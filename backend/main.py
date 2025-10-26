from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import json
import base64
import uvicorn
from datetime import datetime, timezone
import os
import audioop
import wave
import webrtcvad
import openai
from dotenv import load_dotenv

# Import database functions
from database.db_actions import init_db, add_row, Voicemail

load_dotenv()

# Initialize database
SQLITE_URL = os.getenv("SQLITECLOUD_URL")
if SQLITE_URL:
    try:
        init_db(SQLITE_URL)
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")
        SQLITE_URL = None
else:
    print("⚠️ SQLITECLOUD_URL not set - database features disabled")

HTTP_SERVER_PORT = 8080
RECORDINGS_DIR = "recordings"
KEVIN_PHONE_NUMBER = os.getenv("PERSONAL_PHONE")  # Set in .env file

# VAD configuration
VAD_MODE = 2           # 0-3, 3=most aggressive
FRAME_MS = 20          # must be 10/20/30 ms
END_SIL_MS = 2000      # silence threshold to end utterance (increased to 2 seconds for natural pauses)
MAX_UTT_MS = 15000     # max utterance length (increased to 15 seconds)
MIN_SPEECH_MS = 800    # minimum speech duration to count as valid utterance (increased from 500ms)

# Create recordings directory if it doesn't exist
os.makedirs(RECORDINGS_DIR, exist_ok=True)

app = FastAPI()

# Add CORS middleware to allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def log(msg, *args):
    print(f"Media WS: {msg}", *args)

# Initialize BosonAI clients with multiple API keys for cycling
boson_clients = []
boson_api_keys = []

# Load all available API keys (BOSONAI_API_KEY1, BOSONAI_API_KEY2, BOSONAI_API_KEY3)
for i in range(1, 6):
    api_key = os.getenv(f"BOSONAI_API_KEY{i}")
    if api_key:
        boson_api_keys.append(api_key)
        boson_clients.append(openai.Client(
            api_key=api_key,
            base_url="https://hackathon.boson.ai/v1"
        ))
        log(f"Loaded BosonAI API key #{i}")

# Fallback to single BOSONAI_API_KEY if numbered keys not found
if not boson_clients and os.getenv("BOSONAI_API_KEY"):
    boson_api_keys.append(os.getenv("BOSONAI_API_KEY"))
    boson_clients.append(openai.Client(
        api_key=os.getenv("BOSONAI_API_KEY"),
        base_url="https://hackathon.boson.ai/v1"
    ))
    log("Loaded BosonAI API key (legacy)")

# Keep single client reference for backward compatibility
boson_client = boson_clients[0] if boson_clients else None

# API key cycling state
current_key_index = 0
API_REQUEST_TIMEOUT = 10.0  # seconds - timeout for BosonAI requests

# Lock to ensure sequential API calls within same conversation turn
import asyncio
api_call_lock = asyncio.Lock()


async def call_bosonai_with_retry(func_name: str, use_lock: bool = True, **kwargs):
    """
    Call a BosonAI function with automatic key cycling on timeout.
    Tries each available API key in sequence until one succeeds or all fail.
    
    Args:
        func_name: Name of the function to call (e.g., 'chat.completions.create', 'audio.speech.create')
        use_lock: Whether to use the lock to ensure sequential calls (default: True)
        **kwargs: Arguments to pass to the BosonAI function
    
    Returns:
        The response from BosonAI, or None if all keys fail
    """
    global current_key_index
    
    if not boson_clients:
        log("[BosonAI not configured - set BOSONAI_API_KEY1/2/3 env vars]")
        return None
    
    import asyncio
    
    # Use lock to ensure sequential calls within same conversation turn use same API key
    async def _make_call():
        global current_key_index
        
        # Try each API key in sequence
        num_keys = len(boson_clients)
        for attempt in range(num_keys):
            key_idx = (current_key_index + attempt) % num_keys
            client = boson_clients[key_idx]
            
            try:
                log(f"Attempting BosonAI call with API key #{key_idx + 1} (timeout: {API_REQUEST_TIMEOUT}s)...")
                
                # Parse the function path (e.g., "chat.completions.create" -> client.chat.completions.create)
                func = client
                for part in func_name.split('.'):
                    func = getattr(func, part)
                
                # Call the function with timeout
                response = await asyncio.wait_for(
                    asyncio.to_thread(func, **kwargs),
                    timeout=API_REQUEST_TIMEOUT
                )
                
                # Success! Update current key index for next call
                if key_idx != current_key_index:
                    log(f"✅ Switched to API key #{key_idx + 1} successfully")
                    current_key_index = key_idx
                
                return response
                
            except asyncio.TimeoutError:
                log(f"⏱️ API key #{key_idx + 1} timed out after {API_REQUEST_TIMEOUT}s")
                if attempt < num_keys - 1:
                    log(f"🔄 Trying next API key...")
                continue
                
            except Exception as e:
                log(f"❌ API key #{key_idx + 1} failed: {e}")
                if attempt < num_keys - 1:
                    log(f"🔄 Trying next API key...")
                continue
        
        # All keys failed
        log(f"❌ All {num_keys} API keys failed")
        return None
    
    # Execute with or without lock
    if use_lock:
        async with api_call_lock:
            return await _make_call()
    else:
        return await _make_call()


def mulaw8k_to_pcm16_16k(mulaw_bytes: bytes) -> bytes:
    """Decode μ-law 8 kHz → PCM16 8 kHz, then upsample → PCM16 16 kHz."""
    pcm16_8k = audioop.ulaw2lin(mulaw_bytes, 2)                      # 2 bytes/sample
    pcm16_16k, _ = audioop.ratecv(pcm16_8k, 2, 1, 8000, 16000, None) # inwidth=2, nchannels=1
    return pcm16_16k


def pcm16_16k_to_mulaw8k(pcm16_16k: bytes) -> bytes:
    """Downsample PCM16 16 kHz → 8 kHz, then encode to μ-law for Twilio."""
    pcm16_8k, _ = audioop.ratecv(pcm16_16k, 2, 1, 16000, 8000, None)
    return audioop.lin2ulaw(pcm16_8k, 2)


async def process_utterance_and_respond(pcm16_16k: bytes, websocket: WebSocket, stream_sid: str, conversation_history: list, call_sid: str, wav_file=None):
    """Send PCM16 16kHz audio to BosonAI and stream response back to Twilio."""
    if not boson_clients:
        log("[BosonAI not configured - set BOSONAI_API_KEY1/2/3 env vars]")
        return None, None, None
    
    try:
        # Save audio chunk to temporary WAV file (following example1.py pattern)
        import io
        
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(16000)
            wav.writeframes(pcm16_16k)
        
        wav_data = wav_buffer.getvalue()
        audio_base64 = base64.b64encode(wav_data).decode("utf-8")
        
        log("Sending audio to BosonAI...")
        
        # Build messages with conversation history
        messages = [
            {
                "role": "system",
                "content": f"""You are a professional receptionist for Kevin Peng's office. Your job is to:
1. Screen calls politely and professionally
2. Identify if callers are legitimate or spam/scam
3. For legitimate callers: collect their name, reason for calling, and offer to forward them to Kevin
4. For suspicious calls (robocalls, scammers, telemarketers): politely end the call
5. Keep responses brief and natural - this is a phone conversation

CALL ROUTING RULES:
- If caller mentions: car warranty, IRS, Microsoft support, computer virus, student loans, credit card debt, free vacation, prize winner, "this is your final notice" → These are SPAM
- If caller is rude, aggressive, or won't identify themselves → SPAM
- If caller asks for Kevin by name, seems friendly, mentions a hackathon or school related project, has legitimate business, or seems genuine → LEGITIMATE

RESPONSE FORMAT:
After your spoken response, add ONE of these commands on a new line:
- For legitimate callers who want Kevin (like for a hackathon): add "FORWARD_CALL"
- For spam/scam callers: add "END_CALL"

Example spam response:
"I'm sorry, but that sounds like a spam call. Thank you, but I need to end this call now. Goodbye.
END_CALL"

Example legitimate response:
"Thank you Jordan. Let me connect you to Kevin right away.
FORWARD_CALL"
"""
            }
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add current audio input
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_base64,
                        "format": "wav",
                    },
                },
            ],
        })
        
        # Call BosonAI with automatic key cycling on timeout
        response = await call_bosonai_with_retry(
            "chat.completions.create",
            model="higgs-audio-understanding-Hackathon",
            messages=messages,
            temperature=0.2,
        )
        
        if not response:
            log("Failed to get response from BosonAI (all API keys failed or timed out)")
            return None, None, None
        
        model_response = response.choices[0].message.content
        
        if not model_response:
            log("No response from BosonAI")
            return None, None, None
        
        # Try to extract what the caller said (BosonAI sometimes includes transcription)
        caller_said = None
        if ":" in model_response or "said" in model_response.lower():
            # BosonAI might format like "Caller: text" or mention what was said
            # For now, just log the full response
            pass
            
        log(f"BosonAI understood caller and responded: {model_response}")
        
        # Check for special commands (look for keywords that indicate spam/forward intent)
        action = None
        response_text = model_response
        
        # Check for explicit commands
        if "FORWARD_CALL" in model_response:
            action = "FORWARD"
            response_text = model_response.replace("FORWARD_CALL", "").strip()
            log("⚡ ACTION: Forwarding call to Kevin's phone")
        elif "END_CALL" in model_response:
            action = "END"
            response_text = model_response.replace("END_CALL", "").strip()
            log("⚡ ACTION: Ending call (spam detected)")
        else:
            # Fallback: detect spam indicators in the response
            spam_indicators = [
                "spam call", "spam", "scam", "end this call", "end the call",
                "cannot assist", "can't assist", "not legitimate", "suspicious",
                "telemarkeeter", "robocall", "goodbye"
            ]
            forward_indicators = [
                "connect you", "forward", "transfer you", "put you through",
                "let me get kevin", "patch you through"
            ]
            
            response_lower = response_text.lower()
            
            if any(indicator in response_lower for indicator in spam_indicators):
                action = "END"
                log("⚡ ACTION: Ending call (spam keywords detected in response)")
            elif any(indicator in response_lower for indicator in forward_indicators):
                action = "FORWARD"
                log("⚡ ACTION: Forwarding call (forward keywords detected in response)")
        
        # Add to conversation history (transcription + response)
        # Note: We're adding the assistant's response to maintain context
        conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Generate speech from text response with automatic key cycling
        log("Generating speech response...")
        speech_response = await call_bosonai_with_retry(
            "audio.speech.create",
            model="higgs-audio-generation-Hackathon",
            voice="belinda",
            input=response_text,
            response_format="pcm"
        )
        
        if not speech_response:
            log("Failed to generate speech from BosonAI (all API keys failed or timed out)")
            return None, None, None
        
        # Audio specs from example1.py
        # num_channels = 1
        # sample_width = 2
        # sample_rate = 24000
        
        pcm_data = speech_response.content
        
        log(f"Received {len(pcm_data)} bytes of PCM audio from BosonAI")
        
        # Convert PCM16 24kHz -> PCM16 8kHz for recording and Twilio
        pcm16_8k_full, _ = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)
        
        # Write bot response to WAV file
        if wav_file:
            wav_file.writeframes(pcm16_8k_full)
        
        # Convert to μ-law and send to Twilio in chunks
        # Process in chunks to avoid memory issues
        chunk_size = 1600  # 100ms at 8kHz (1 channel, 2 bytes/sample)
        for i in range(0, len(pcm16_8k_full), chunk_size):
            chunk = pcm16_8k_full[i:i + chunk_size]
            if len(chunk) < 4:  # Need at least 2 samples
                continue
            
            # Convert to μ-law
            mulaw_8k = audioop.lin2ulaw(chunk, 2)
            
            # Send to Twilio
            await websocket.send_text(json.dumps({
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": base64.b64encode(mulaw_8k).decode("utf-8")
                }
            }))
        
        log("Finished streaming response to caller - waiting for next utterance")
        
        # Add delay to let audio clear from the phone line (prevent echo detection)
        import asyncio
        
        # Calculate actual audio duration and add buffer time
        audio_duration_seconds = len(pcm16_8k_full) / (8000 * 2)  # samples / (sample_rate * bytes_per_sample)
        # Add extra 2 seconds for network latency, phone processing, and safety margin
        wait_time = audio_duration_seconds + 2.0
        
        log(f"Waiting {wait_time:.1f}s for bot audio to finish playing ({audio_duration_seconds:.1f}s audio + 2s buffer)...")
        await asyncio.sleep(wait_time)
        
        # Execute action if needed
        if action == "FORWARD":
            log(f"📞 Forwarding call {call_sid} to {KEVIN_PHONE_NUMBER}")
            await forward_call(call_sid)
        elif action == "END":
            log(f"🚫 Ending call {call_sid} (spam)")
            await end_call(call_sid)
        
        return model_response, pcm16_8k_full, action
        
    except Exception as e:
        log(f"BosonAI error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


async def forward_call(call_sid: str):
    """Forward the call to Kevin's personal phone number using Twilio API."""
    try:
        import httpx
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            log("⚠️ TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env to forward calls")
            return
        
        # Update the call to dial Kevin's number
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"
        
        # TwiML to dial Kevin's number with extended timeout
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Please hold while I connect you to Kevin.</Say>
    <Dial timeout="30" callerId="{KEVIN_PHONE_NUMBER}">
        <Number>{KEVIN_PHONE_NUMBER}</Number>
    </Dial>
    <Say>I'm sorry, Kevin is not available right now. Please try again later. Goodbye.</Say>
</Response>"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(account_sid, auth_token),
                data={"Twiml": twiml}
            )
            
            if response.status_code == 200:
                log(f"✅ Call forwarded successfully to {KEVIN_PHONE_NUMBER}")
            else:
                log(f"❌ Failed to forward call: {response.status_code} - {response.text}")
                
    except Exception as e:
        log(f"Error forwarding call: {e}")


async def end_call(call_sid: str):
    """End the call immediately using Twilio API."""
    try:
        import httpx
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            log("⚠️ TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env to end calls")
            return
        
        # Update the call status to "completed" to end it
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(account_sid, auth_token),
                data={"Status": "completed"}
            )
            
            if response.status_code == 200:
                log(f"✅ Call ended successfully")
            else:
                log(f"❌ Failed to end call: {response.status_code} - {response.text}")
                
    except Exception as e:
        log(f"Error ending call: {e}")


async def save_call_to_database(
    call_sid: str,
    from_number: str,
    conversation_log: list,
    transcripts: list,
    recording_filename: str,
    is_spam: bool
):
    """
    Save call information to the SQLiteCloud database.
    
    Args:
        call_sid: Twilio call SID
        from_number: Caller's phone number
        conversation_log: List of conversation exchanges
        transcripts: List of bot responses
        recording_filename: Path to the WAV recording file
        is_spam: Whether the call was identified as spam
    """
    log(f"[SAVE] Starting database save for call {call_sid}")
    log(f"[SAVE] Recording filename: {recording_filename}")
    log(f"[SAVE] From number: {from_number}")
    log(f"[SAVE] Is spam: {is_spam}")
    
    if not SQLITE_URL:
        log("⚠️ Database not configured - skipping save")
        return
    
    try:
        # Extract caller name and call description from conversation
        caller_name = "Unknown Caller"
        description = "No conversation"
        
        # Try to extract name from bot responses
        for entry in conversation_log:
            if entry.get('speaker') == 'Bot':
                text = entry.get('text', '')
                # Look for patterns like "Thank you [Name]" or "Hi [Name]"
                if 'thank you' in text.lower() or 'thanks' in text.lower() or 'hi ' in text.lower():
                    words = text.split()
                    for i, word in enumerate(words):
                        if word.lower() in ['thank', 'thanks', 'hi', 'hello'] and i + 1 < len(words):
                            potential_name = words[i + 1].strip('.,!?')
                            if potential_name and potential_name[0].isupper() and len(potential_name) > 1:
                                caller_name = potential_name
                                log(f"[SAVE] Extracted caller name: {caller_name}")
                                break
        
        # Create a concise, high-level description
        if is_spam:
            # For spam calls, create a short description
            spam_types = {
                'warranty': 'Car warranty scam',
                'irs': 'IRS scam call',
                'microsoft': 'Tech support scam',
                'computer': 'Tech support scam',
                'student loan': 'Student loan scam',
                'credit card': 'Credit card offer',
                'vacation': 'Vacation scam',
                'prize': 'Prize scam',
                'social security': 'Social Security scam'
            }
            
            # Check transcripts for spam keywords
            description = "Spam call"
            if transcripts:
                transcript_text = ' '.join(transcripts).lower()
                for keyword, desc in spam_types.items():
                    if keyword in transcript_text:
                        description = desc
                        break
        else:
            # For legitimate calls, extract the main topic
            if transcripts and len(transcripts) > 0:
                # Get the caller's stated purpose from the conversation
                first_response = transcripts[0].replace("FORWARD_CALL", "").replace("END_CALL", "").strip()
                
                # Extract key phrases
                if 'hackathon' in first_response.lower():
                    description = "Hackathon related inquiry"
                elif 'project' in first_response.lower():
                    description = "Project discussion"
                elif 'meeting' in first_response.lower():
                    description = "Meeting request"
                elif 'interview' in first_response.lower():
                    description = "Interview scheduled"
                else:
                    # Take first sentence as description (limit to 60 chars)
                    sentences = first_response.split('.')
                    if sentences:
                        description = sentences[0].strip()
                        if len(description) > 60:
                            description = description[:60] + "..."
        
        log(f"[SAVE] Caller: {caller_name}")
        log(f"[SAVE] Description: {description}")
        
        # Create Voicemail object
        voicemail = Voicemail(
            id=0,  # Will be auto-generated by database
            number=from_number if from_number and from_number != 'unknown' and from_number != 'Unknown' else 'Unknown Number',
            name=caller_name,
            description=description,
            spam=is_spam,
            date=datetime.now(timezone.utc),
            unread=True,
            recording=recording_filename
        )
        
        log(f"[SAVE] Calling add_row() to save to database...")
        # Save to database
        add_row(SQLITE_URL, voicemail)
        log(f"✅ Call saved to database: {caller_name} ({from_number}) - Spam: {is_spam}")
        
    except Exception as e:
        log(f"❌ Failed to save call to database: {e}")
        import traceback
        traceback.print_exc()


class VadProcessor:
    """Handles VAD-based speech segmentation for endpointing."""
    
    def __init__(self, on_utterance_callback):
        self.vad = webrtcvad.Vad(VAD_MODE)
        self.on_utterance = on_utterance_callback
        self.buf_pcm16_8k = bytearray()
        self.sil_ms = 0
        self.speech_ms = 0
        self.utt_ms = 0
        self.in_speech = False
    
    def feed_mulaw_frame(self, mulaw_frame: bytes):
        """
        Feed a 20ms μ-law frame (160 bytes) and check for utterance endpoint.
        mulaw_frame must be 20 ms at 8 kHz -> 160 samples -> 160 bytes of μ-law.
        """
        if len(mulaw_frame) != 160:
            return  # Skip invalid frames
        
        # μ-law → PCM16 8 kHz
        pcm16_8k = audioop.ulaw2lin(mulaw_frame, 2)
        
        # VAD expects linear PCM at the same sample rate
        is_speech = self.vad.is_speech(pcm16_8k, sample_rate=8000)
        self.utt_ms += FRAME_MS
        
        if is_speech:
            self.in_speech = True
            self.speech_ms += FRAME_MS
            self.sil_ms = 0
            self.buf_pcm16_8k.extend(pcm16_8k)
        else:
            if self.in_speech:
                self.sil_ms += FRAME_MS
                self.buf_pcm16_8k.extend(pcm16_8k)  # Include trailing silence
        
        # Endpoint conditions
        if self.in_speech and (self.sil_ms >= END_SIL_MS or self.utt_ms >= MAX_UTT_MS):
            # Finalize utterance - upsample to 16 kHz for ASR
            pcm16_16k, _ = audioop.ratecv(bytes(self.buf_pcm16_8k), 2, 1, 8000, 16000, None)
            log(f"Utterance detected: {self.speech_ms}ms speech, {self.sil_ms}ms silence")
            self.on_utterance(pcm16_16k)
            # Reset
            self.buf_pcm16_8k.clear()
            self.sil_ms = self.speech_ms = self.utt_ms = 0
            self.in_speech = False


@app.post('/twiml')
async def return_twiml(request: Request):
    """Return TwiML to connect the call to our WebSocket for bidirectional streaming"""
    print("POST TwiML")
    
    # Get the host from the request to build the WebSocket URL
    host = request.headers.get('host', f'localhost:{HTTP_SERVER_PORT}')
    protocol = 'wss' if request.url.scheme == 'https' else 'ws'
    
    # Use <Connect> with BIDIRECTIONAL streaming (both_tracks) to allow bot to speak
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{protocol}://{host}/media-stream" />
    </Connect>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


async def send_greeting(websocket: WebSocket, stream_sid: str, wav_file=None):
    """Send initial greeting when call starts."""
    if not boson_clients:
        return
    
    try:
        greeting_text = "Hi, you've reached the office of Kevin Peng. How can I help you today?"
        log(f"Sending greeting: {greeting_text}")
        
        # Generate speech from greeting with automatic key cycling
        speech_response = await call_bosonai_with_retry(
            "audio.speech.create",
            model="higgs-audio-generation-Hackathon",
            voice="mabel",
            input=greeting_text,
            response_format="pcm"
        )
        
        if not speech_response:
            log("Failed to generate greeting from BosonAI (all API keys failed or timed out)")
            return None
        
        pcm_data = speech_response.content
        log(f"Received {len(pcm_data)} bytes of PCM audio for greeting")
        
        # Convert PCM16 24kHz -> PCM16 8kHz for recording and Twilio
        pcm16_8k_full, _ = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)
        
        # Write bot greeting to WAV file
        if wav_file:
            wav_file.writeframes(pcm16_8k_full)
        
        # Send to Twilio in chunks
        chunk_size = 1600  # 100ms at 8kHz
        for i in range(0, len(pcm16_8k_full), chunk_size):
            chunk = pcm16_8k_full[i:i + chunk_size]
            if len(chunk) < 4:
                continue
            
            mulaw_8k = audioop.lin2ulaw(chunk, 2)
            await websocket.send_text(json.dumps({
                "event": "media",
                "streamSid": stream_sid,
                "media": {
                    "payload": base64.b64encode(mulaw_8k).decode("utf-8")
                }
            }))
        
        log("Greeting sent - waiting for caller response...")
        
        # Add delay to let greeting audio clear from the line
        import asyncio
        
        # Calculate actual audio duration and add buffer time
        audio_duration_seconds = len(pcm16_8k_full) / (8000 * 2)  # samples / (sample_rate * bytes_per_sample)
        # Add extra 2 seconds for network latency, phone processing, and safety margin
        wait_time = audio_duration_seconds + 2.0
        
        log(f"Waiting {wait_time:.1f}s for greeting to finish playing ({audio_duration_seconds:.1f}s audio + 2s buffer)...")
        await asyncio.sleep(wait_time)
        
        return greeting_text
        
    except Exception as e:
        log(f"Error sending greeting: {e}")
        return None


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Handle Twilio media stream WebSocket connection with VAD-based endpointing and BosonAI streaming"""
    await websocket.accept()
    log("Connection accepted")
    
    count = 0
    has_seen_media = False
    wav_file = None
    call_sid = None
    stream_sid = None
    mulaw_buffer = bytearray()
    transcripts = []
    conversation_log = []  # Detailed conversation with caller and bot
    conversation_history = []  # Track full conversation
    greeting_sent = False
    from_number = "unknown"  # Initialize to default value
    recording_filename = None  # Track recording filename
    
    # Track bot speaking state to prevent VAD during bot responses
    bot_is_speaking = False
    bot_finished_time = None  # Track when bot finished speaking for debounce
    DEBOUNCE_SECONDS = 0.5  # Ignore audio for this long after bot finishes (prevent echo pickup)
    
    # Callback for when VAD detects a complete utterance
    async def on_utterance(pcm16_16k: bytes, speech_duration_ms: int):
        nonlocal bot_is_speaking, buf_pcm16_8k, sil_ms, speech_ms, utt_ms, in_speech, bot_finished_time
        
        # Ignore very short utterances (breath, noise, feedback)
        if speech_duration_ms < MIN_SPEECH_MS:
            log(f"Ignoring short utterance ({speech_duration_ms}ms < {MIN_SPEECH_MS}ms minimum)")
            return
        
        log(f"Processing valid utterance ({len(pcm16_16k)} bytes at 16kHz, {speech_duration_ms}ms speech)...")
        
        # Set flag to disable VAD during bot response
        bot_is_speaking = True
        bot_finished_time = None  # Clear debounce timer during processing
        
        # Clear VAD buffer immediately to prevent echo detection
        buf_pcm16_8k.clear()
        sil_ms = speech_ms = utt_ms = 0
        in_speech = False
        
        # Process with BosonAI and stream response back
        if stream_sid and call_sid:  # Make sure we have both stream_sid and call_sid
            response, bot_audio, action = await process_utterance_and_respond(pcm16_16k, websocket, stream_sid, conversation_history, call_sid, wav_file)
            if response:
                transcripts.append(response)
                # Log the exchange
                conversation_log.append({
                    "speaker": "Caller",
                    "duration_ms": speech_duration_ms,
                    "audio_size": len(pcm16_16k)
                })
                conversation_log.append({
                    "speaker": "Bot",
                    "text": response
                })
        else:
            log("Warning: stream_sid or call_sid not set yet, skipping utterance")
        
        # Re-enable VAD after bot finishes speaking (with delay built into process_utterance_and_respond)
        bot_is_speaking = False
        
        # Set debounce time to ignore immediate audio feedback/echo
        import time
        bot_finished_time = time.time()
        
        # Clear buffers again after bot response to ensure clean slate
        buf_pcm16_8k.clear()
        sil_ms = speech_ms = utt_ms = 0
        in_speech = False
        
        log(f"Bot finished speaking - debouncing for {DEBOUNCE_SECONDS}s, then listening for caller...")
    
    # Simple utterance detector (we'll handle VAD manually for async callback)
    vad = webrtcvad.Vad(VAD_MODE)
    buf_pcm16_8k = bytearray()
    sil_ms = 0
    speech_ms = 0
    utt_ms = 0
    in_speech = False
    
    try:
        while True:
            message = await websocket.receive_text()
            
            if message is None:
                log("No message received...")
                continue

            data = json.loads(message)
            
            if data['event'] == "connected":
                log("Connected Message received:", message)
            
            elif data['event'] == "start":
                log("Start Message received:", message)
                # Extract call metadata
                stream_sid = data.get('streamSid')
                call_sid = data['start'].get('callSid')
                
                # Extract caller phone number - Twilio sends this in the start event
                # Try multiple possible fields where the number might be
                from_number = (
                    data['start'].get('customParameters', {}).get('From') or
                    data['start'].get('customParameters', {}).get('from') or
                    data.get('from') or
                    'Unknown'
                )
                log(f"Call from: {from_number}")
                
                # Create WAV file for this call (8 kHz native PSTN rate)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{RECORDINGS_DIR}/call_{call_sid}_{timestamp}.wav"
                recording_filename = f"call_{call_sid}_{timestamp}.wav"  # Store just the filename
                
                # Open WAV file with proper settings for mulaw -> PCM conversion
                wav_file = wave.open(filename, 'wb')
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes (16-bit PCM)
                wav_file.setframerate(8000)  # 8000 Hz (native PSTN)
                
                log(f"Recording to WAV (8kHz): {filename}")
                log(f"VAD enabled: endpointing at {END_SIL_MS}ms silence, min speech {MIN_SPEECH_MS}ms")
                log(f"BosonAI bot ready")
            
            elif data['event'] == "media":
                # Always write to WAV for complete recording
                payload = data['media']['payload']
                mulaw_data = base64.b64decode(payload)
                if wav_file:
                    pcm_data = audioop.ulaw2lin(mulaw_data, 2)
                    wav_file.writeframes(pcm_data)
                
                # Skip VAD processing if bot is speaking (but keep recording above)
                if bot_is_speaking:
                    continue
                
                # Check debounce period - skip VAD immediately after bot finishes speaking
                if bot_finished_time is not None:
                    import time
                    time_since_bot_finished = time.time() - bot_finished_time
                    if time_since_bot_finished < DEBOUNCE_SECONDS:
                        # Still in debounce period - skip VAD processing
                        continue
                    else:
                        # Debounce period over - clear the timer and resume normal processing
                        if bot_finished_time is not None:  # Only log once
                            log("Debounce period over - resuming VAD")
                            bot_finished_time = None
                
                if not has_seen_media:
                    log("Media message received - streaming audio with VAD...")
                    log("Additional media messages are being suppressed from logs...")
                    has_seen_media = True
                    
                    # Send greeting after first media packet (ensures stream is ready)
                    if not greeting_sent and stream_sid:
                        bot_is_speaking = True  # Prevent VAD during greeting
                        greeting = await send_greeting(websocket, stream_sid, wav_file)
                        if greeting:
                            conversation_history.append({
                                "role": "assistant",
                                "content": greeting
                            })
                            conversation_log.append({
                                "speaker": "Bot",
                                "text": greeting
                            })
                        # Clear any accumulated audio during greeting
                        mulaw_buffer.clear()
                        buf_pcm16_8k.clear()
                        sil_ms = speech_ms = utt_ms = 0
                        in_speech = False
                        bot_is_speaking = False
                        
                        # Set debounce time after greeting
                        import time
                        bot_finished_time = time.time()
                        
                        greeting_sent = True
                        log(f"Greeting complete - VAD buffers cleared, debouncing for {DEBOUNCE_SECONDS}s, then ready for caller")
                        continue  # Skip processing this packet
                
                # Add to buffer and process in 20ms frames (160 bytes μ-law)
                # (mulaw_data already extracted at top of media event handler)
                mulaw_buffer.extend(mulaw_data)
                
                # Process complete 20ms frames for VAD
                while len(mulaw_buffer) >= 160:
                    frame = bytes(mulaw_buffer[:160])
                    mulaw_buffer = mulaw_buffer[160:]
                    
                    # Manual VAD processing for async callback support
                    pcm16_8k = audioop.ulaw2lin(frame, 2)
                    is_speech = vad.is_speech(pcm16_8k, sample_rate=8000)
                    utt_ms += FRAME_MS
                    
                    if is_speech:
                        in_speech = True
                        speech_ms += FRAME_MS
                        sil_ms = 0
                        buf_pcm16_8k.extend(pcm16_8k)
                    else:
                        if in_speech:
                            sil_ms += FRAME_MS
                            buf_pcm16_8k.extend(pcm16_8k)
                    
                    # Check for utterance endpoint
                    if in_speech and (sil_ms >= END_SIL_MS or utt_ms >= MAX_UTT_MS):
                        # Finalize utterance - upsample to 16 kHz for ASR
                        pcm16_16k, _ = audioop.ratecv(bytes(buf_pcm16_8k), 2, 1, 8000, 16000, None)
                        log(f"Utterance detected: {speech_ms}ms speech, {sil_ms}ms silence")
                        
                        # Process with BosonAI (async) - this will set bot_is_speaking=True
                        # Pass speech duration to filter out short noise
                        await on_utterance(pcm16_16k, speech_ms)
                        
                        # Reset VAD state
                        buf_pcm16_8k.clear()
                        sil_ms = speech_ms = utt_ms = 0
                        in_speech = False
            
            elif data['event'] == "stop":
                log("Stop Message received:", message)
                break
            
            elif data['event'] == "closed":
                log("Closed Message received:", message)
                break
            
            count += 1
    
    except WebSocketDisconnect:
        log("WebSocket disconnected")
    except Exception as e:
        log(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close the WAV file
        if wav_file:
            wav_file.close()
            log(f"WAV file saved successfully - ready to play!")
        
        # Determine if call was spam based on conversation
        is_spam = False
        for entry in conversation_log:
            if entry.get('speaker') == 'Bot':
                text = entry.get('text', '').lower()
                if 'spam' in text or 'end_call' in text or 'scam' in text:
                    is_spam = True
                    break
        
        # Save call to database
        if call_sid and recording_filename:
            await save_call_to_database(
                call_sid=call_sid,
                from_number=from_number,
                conversation_log=conversation_log,
                transcripts=transcripts,
                recording_filename=recording_filename,
                is_spam=is_spam
            )
        
        # Log full conversation
        if conversation_log:
            log(f"\n{'='*60}")
            log(f"CALL TRANSCRIPT - {len([x for x in conversation_log if x['speaker'] == 'Caller'])} exchanges")
            log(f"{'='*60}")
            for i, entry in enumerate(conversation_log, 1):
                if entry['speaker'] == 'Caller':
                    duration = entry.get('duration_ms', 0)
                    audio_size = entry.get('audio_size', 0)
                    log(f"[{i}] 📞 Caller spoke: {duration}ms ({audio_size} bytes audio)")
                else:
                    text = entry.get('text', '')
                    log(f"[{i}] 🤖 Bot: {text}")
            log(f"{'='*60}\n")
        
        # Log transcripts (old format for backward compatibility)
        if transcripts:
            log(f"Call summary - {len(transcripts)} bot response(s):")
            for i, t in enumerate(transcripts, 1):
                log(f"  [{i}] {t}")
        
        log(f"Connection closed. Received a total of {count} messages")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Twilio Media Stream FastAPI Server",
        "endpoints": {
            "twiml": "/twiml (POST)",
            "websocket": "/media-stream (WebSocket)",
            "voicemails": "/voicemails (GET)",
            "voicemail_recording": "/voicemail/{id}/recording (GET)"
        },
        "database": "enabled" if SQLITE_URL else "disabled"
    }


@app.get("/voicemails")
async def get_voicemails():
    """Retrieve all voicemails from the database"""
    log("[API] GET /voicemails - Fetching voicemails from database")
    
    if not SQLITE_URL:
        log("[API] ERROR: Database not configured")
        return {"error": "Database not configured"}
    
    try:
        from database.db_actions import read_table
        voicemails = read_table(SQLITE_URL)
        
        log(f"[API] Retrieved {len(voicemails)} voicemails from database")
        
        # Convert to JSON-serializable format
        result = []
        for vm in voicemails:
            result.append({
                "id": vm.id,
                "number": vm.number,
                "name": vm.name,
                "description": vm.description,
                "spam": vm.spam,
                "date": vm.date.isoformat(),
                "unread": vm.unread,
                "recording": vm.recording
            })
        
        log(f"[API] Returning {len(result)} voicemails to frontend")
        return {"voicemails": result, "count": len(result)}
    except Exception as e:
        log(f"[API] ERROR fetching voicemails: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@app.get("/voicemail/{voicemail_id}/recording")
async def get_voicemail_recording(voicemail_id: int):
    """Get the audio recording for a specific voicemail"""
    if not SQLITE_URL:
        return {"error": "Database not configured"}
    
    try:
        from database.db_actions import get_recording
        recording_bytes = get_recording(SQLITE_URL, voicemail_id)
        
        if recording_bytes:
            from fastapi.responses import Response
            return Response(content=recording_bytes, media_type="audio/wav")
        else:
            return {"error": "Recording not found"}
    except Exception as e:
        return {"error": str(e)}


if __name__ == '__main__':
    print(f"Server listening on: http://localhost:{HTTP_SERVER_PORT}")
    print("Starting FastAPI server with WebSocket support...")
    uvicorn.run(app, host="0.0.0.0", port=HTTP_SERVER_PORT)
