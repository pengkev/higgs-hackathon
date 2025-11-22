from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import json
import base64
import uvicorn
from datetime import datetime, timezone
import os
import re
import audioop
import wave
import webrtcvad
import openai
from dotenv import load_dotenv
from gcal import get_current_event, book_next_available

# Import database functions
# from database.db_actions import init_db, add_row, Voicemail

load_dotenv()

# Load prompts from JSON file
with open('prompts.json', 'r', encoding='utf-8') as f:
    PROMPTS = json.load(f)

# Initialize database
# SQLITE_URL = os.getenv("SQLITECLOUD_URL")
# if SQLITE_URL:
#     try:
#         init_db(SQLITE_URL)
#         print("✅ Database initialized successfully")
#     except Exception as e:
#         print(f"⚠️ Database initialization failed: {e}")
#         SQLITE_URL = None
# else:
#     print("⚠️ SQLITECLOUD_URL not set - database features disabled")
SQLITE_URL = None  # Temporarily disabled

HTTP_SERVER_PORT = 8080
RECORDINGS_DIR = "recordings"
TRANSCRIPTS_DIR = "transcripts"
BOSONAI_PHONE_NUMBER = os.getenv("BOSONAI_PHONE_NUMBER") or os.getenv("PERSONAL_PHONE")  # Set in .env file

# VAD configuration
VAD_MODE = 2           # 0-3, 3=most aggressive
FRAME_MS = 20          # must be 10/20/30 ms
END_SIL_MS = 1000      # silence threshold to end utterance (1.5 seconds - wait for caller to finish)
MAX_UTT_MS = 20000     # max utterance length
MIN_SPEECH_MS = 500    # minimum speech duration to count as valid utterance (ignore breath/noise)
MIN_EXCHANGES_BEFORE_ACTION = 0
VOICE = "belinda"

# Echo/Delay configuration (tune these to adjust timing)
POST_AUDIO_DELAY_SECONDS = 0.5   # Fixed delay after bot audio finishes playing before accepting user input

# Create recordings directory if it doesn't exist
os.makedirs(RECORDINGS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

app = FastAPI()

def log(msg, *args):
    print(f"Media WS: {msg}", *args)


# Initialize BosonAI clients with multiple API keys for cycling
boson_clients = []
boson_api_keys = []

# Load all available API keys (BOSONAI_API_KEY1, BOSONAI_API_KEY2, BOSONAI_API_KEY3)
for i in range(1, 2):
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
# Add CORS middleware to allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def extract_caller_name(conversation_history: list, latest_transcription: str) -> str:
    """
    Extract caller's name from conversation history.
    Looks for patterns like "This is [name]", "My name is [name]", "[name] calling", etc.
    """
    # Combine all caller messages
    all_caller_text = ""
    for msg in conversation_history:
        if msg.get("role") == "user":
            all_caller_text += msg.get("content", "") + " "
    
    all_caller_text += latest_transcription
    
    # Simple name extraction patterns
    patterns = [
        r"(?:this is|it's|i'm|my name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:calling|here)",
        r"(?:^|\s)([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s|$)",  # Two capitalized words
    ]
    
    for pattern in patterns:
        match = re.search(pattern, all_caller_text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Filter out common false positives
            false_positives = ["BosonAI", "Good Morning", "Good Afternoon", "Thank You"]
            if name not in false_positives and len(name) > 2:
                return name
    
    # Default if no name found
    return "Unknown Caller"


def clean_text_for_transcript(text: str) -> str:
    """
    Clean text for transcript logging by removing:
    - <think>...</think> tags (AI reasoning)
    - Content in brackets: [text], (text), {text}
    """
    import re
    # Remove <think> tags and their content
    cleaned = re.sub(r'<think>.*?</think>\s*', '', text, flags=re.DOTALL)
    # Remove bracketed content
    cleaned = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', cleaned)
    # Clean up extra whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def save_transcript(call_sid: str, from_number: str, conversation_log: list, call_start_time: datetime, call_end_time: datetime, final_action: str = None, call_in_progress: bool = False):
    """Save call transcript to JSON file. Can be called multiple times to update the same file."""
    try:
        timestamp = call_start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{TRANSCRIPTS_DIR}/transcript_{call_sid}_{timestamp}.json"
        
        # Calculate call duration
        duration_seconds = (call_end_time - call_start_time).total_seconds()
        
        # Build transcript data
        transcript_data = {
            "call_sid": call_sid,
            "from_number": from_number,
            "start_time": call_start_time.isoformat(),
            "end_time": call_end_time.isoformat(),
            "duration_seconds": round(duration_seconds, 2),
            "call_in_progress": call_in_progress,  # True if call is still active
            "final_action": final_action,  # "FORWARD", "END", or None
            "conversation": []
        }
        
        # Process conversation log
        for entry in conversation_log:
            if entry['speaker'] == 'Caller':
                caller_text = entry.get('text', None)
                transcript_data['conversation'].append({
                    "speaker": "Caller",
                    "duration_ms": entry.get('duration_ms', 0),
                    "audio_size_bytes": entry.get('audio_size', 0),
                    "text": caller_text if caller_text else "[Transcription not available]"
                })
            else:  # Bot
                transcript_data['conversation'].append({
                    "speaker": "AI Receptionist",
                    "text": entry.get('text', ''),
                    "timestamp": entry.get('timestamp', '')
                })
        
        # Save to JSON file
        import json as json_module
        with open(filename, 'w', encoding='utf-8') as f:
            json_module.dump(transcript_data, f, indent=2, ensure_ascii=False)
        
        log(f"💾 Transcript saved: {filename}")
        
        # Also save a human-readable text version
        txt_filename = f"{TRANSCRIPTS_DIR}/transcript_{call_sid}_{timestamp}.txt"
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(f"CALL TRANSCRIPT\n")
            f.write(f"{'='*60}\n")
            f.write(f"Call ID: {call_sid}\n")
            f.write(f"From: {from_number}\n")
            f.write(f"Start: {call_start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"End: {call_end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {duration_seconds:.1f} seconds\n")
            if call_in_progress:
                f.write(f"Status: CALL IN PROGRESS (transcript updating in real-time)\n")
            if final_action:
                action_text = "Forwarded to BosonAI" if final_action == "FORWARD" else "Ended (Spam Detected)"
                f.write(f"Result: {action_text}\n")
            f.write(f"{'='*60}\n\n")
            
            for i, entry in enumerate(conversation_log, 1):
                if entry['speaker'] == 'Caller':
                    caller_text = entry.get('text', None)
                    duration = entry.get('duration_ms', 0)
                    if caller_text:
                        f.write(f"[{i}] CALLER: {caller_text}\n\n")
                    else:
                        f.write(f"[{i}] CALLER: [Spoke for {duration}ms - transcription unavailable]\n\n")
                else:
                    text = entry.get('text', '')
                    f.write(f"[{i}] AI RECEPTIONIST: {text}\n\n")
        
        log(f"📄 Human-readable transcript saved: {txt_filename}")
        
    except Exception as e:
        log(f"Error saving transcript: {e}")
        import traceback
        traceback.print_exc()




def mulaw8k_to_pcm16_16k(mulaw_bytes: bytes) -> bytes:
    """Decode μ-law 8 kHz → PCM16 8 kHz, then upsample → PCM16 16 kHz."""
    pcm16_8k = audioop.ulaw2lin(mulaw_bytes, 2)                      # 2 bytes/sample
    pcm16_16k, _ = audioop.ratecv(pcm16_8k, 2, 1, 8000, 16000, None) # inwidth=2, nchannels=1
    return pcm16_16k


def pcm16_16k_to_mulaw8k(pcm16_16k: bytes) -> bytes:
    """Downsample PCM16 16 kHz → 8 kHz, then encode to μ-law for Twilio."""
    pcm16_8k, _ = audioop.ratecv(pcm16_16k, 2, 1, 16000, 8000, None)
    return audioop.lin2ulaw(pcm16_8k, 2)


async def get_call_info(call_sid: str) -> dict:
    """
    Retrieve detailed information about a call including AI-generated summary.
    
    Returns a dictionary with:
        id: str - Call SID
        number: str - Caller phone number
        name: str - Extracted caller name
        description: str - AI-generated summary of the call
        spam: bool - Whether call was marked as spam
        date: datetime - Call start time
        unread: bool - Whether call has been reviewed (always False for now)
        recording: str - Path to WAV recording file
        transcript: str - Path to transcript JSON file
    """
    import glob
    import json as json_module
    from pathlib import Path
    
    try:
        # Find transcript file for this call_sid
        transcript_pattern = f"{TRANSCRIPTS_DIR}/transcript_{call_sid}_*.json"
        transcript_files = glob.glob(transcript_pattern)
        
        if not transcript_files:
            log(f"No transcript found for call {call_sid}")
            return None
        
        # Use the most recent transcript if multiple exist
        transcript_path = sorted(transcript_files)[-1]
        
        # Load transcript data
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_data = json_module.load(f)
        
        # Extract basic info
        call_id = transcript_data.get('call_sid', call_sid)
        from_number = transcript_data.get('from_number', 'Unknown')
        start_time_str = transcript_data.get('start_time')
        start_time = datetime.fromisoformat(start_time_str) if start_time_str else datetime.now()
        final_action = transcript_data.get('final_action')
        is_spam = final_action == "END"
        
        # Extract caller name from conversation
        caller_name = "Unknown Caller"
        conversation = transcript_data.get('conversation', [])
        for entry in conversation:
            if entry.get('speaker') == 'Caller' and entry.get('text'):
                # Try to extract name from first caller message
                import re
                text = entry.get('text', '')
                patterns = [
                    r"(?:this is|it's|i'm|my name is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
                    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:calling|here)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        name = match.group(1).strip()
                        if len(name) > 2:
                            caller_name = name
                            break
                if caller_name != "Unknown Caller":
                    break
        
        # Find corresponding recording file
        recording_pattern = f"{RECORDINGS_DIR}/call_{call_sid}_*.wav"
        recording_files = glob.glob(recording_pattern)
        recording_path = sorted(recording_files)[-1] if recording_files else None
        
        # Generate AI summary of the conversation
        description = await generate_call_summary(conversation)
        
        # Build result dictionary
        result = {
            "id": call_id,
            "number": from_number,
            "name": caller_name,
            "description": description,
            "spam": is_spam,
            "date": start_time,
            "unread": False,  # Could be implemented with a separate tracking system
            "recording": recording_path,
            "transcript": transcript_path
        }
        
        return result
        
    except Exception as e:
        log(f"Error getting call info: {e}")
        import traceback
        traceback.print_exc()
        return None


async def generate_call_summary(conversation: list) -> str:
    """
    Generate a concise summary of the call conversation using AI.
    
    Args:
        conversation: List of conversation entries from transcript
        
    Returns:
        A brief summary string describing the call
    """
    if not boson_client or not conversation:
        return "No conversation data available"
    
    try:
        # Build a readable conversation text
        conversation_text = ""
        for entry in conversation:
            speaker = entry.get('speaker', 'Unknown')
            text = entry.get('text', '[No text]')
            conversation_text += f"{speaker}: {text}\n"
        
        # Prompt the AI to summarize
        summary_prompt = PROMPTS["call_summary_user_template"].format(conversation_text=conversation_text)
        
        response = await call_bosonai_with_retry(
            "chat.completions.create",
            model="Qwen3-32B-non-thinking-Hackathon",
            messages=[
                {
                    "role": "system",
                    "content": PROMPTS["call_summary"]
                },
                {
                    "role": "user",
                    "content": summary_prompt
                }
            ],
            temperature=0.3,  # Lower temperature for consistent summaries
        )
        
        if response and response.choices[0].message.content:
            summary = response.choices[0].message.content.strip()
            # Remove any thinking tags
            import re
            summary = re.sub(r'<think>.*?</think>\s*', '', summary, flags=re.DOTALL).strip()
            return summary
        else:
            return "Unable to generate summary"
            
    except Exception as e:
        log(f"Error generating summary: {e}")
        return "Error generating summary"


async def process_utterance_and_respond(pcm16_16k: bytes, websocket: WebSocket, stream_sid: str, conversation_history: list, call_sid: str, exchange_count: int = 0):
    """Process user utterance and generate/send response."""
    if not boson_clients:
        return None, None, None, None, 0.0
    
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
        
        log("Step 1: Transcribing caller audio...")
        
        # STEP 1: Transcribe the audio first
        transcription_messages = [
            {
                "role": "system",
                "content": PROMPTS["transcription"]
            },
            {
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
            }
        ]
        
        transcription_response = await call_bosonai_with_retry(
            "chat.completions.create",
            model="higgs-audio-understanding-Hackathon",
            messages=transcription_messages,
            temperature=0.3,  # Lower temperature for accurate transcription
        )
        
        if not transcription_response:
            log("Failed to get transcription from BosonAI (all API keys failed or timed out)")
            return None, None, None, None, 0.0
        
        caller_transcription = transcription_response.choices[0].message.content
        
        if not caller_transcription:
            log("No transcription received")
            return None, None, None, None, 0.0
        
        log(f"📝 Caller said: \"{caller_transcription}\"")
        
        # STEP 2: Use transcription to generate response
        log("Step 2: Generating AI response from transcription...")
        
        # Get current calendar event status
        current_event_info = get_current_event()
        log(f"📅 Calendar status: {current_event_info}")
        
        # Build messages with conversation history
        calendar_context = ""
        if current_event_info and current_event_info != "No current events":
            calendar_context = f"\n\nCALENDAR STATUS:\nBosonAI is currently in: {current_event_info}\n\nFor legitimate callers, if BosonAI is busy, offer to book them at the next available time instead of forwarding. Use the command BOOK_MEETING on a new line after your response."
        else:
            calendar_context = f"\n\nCALENDAR STATUS:\nBosonAI is available right now (no current meetings).\n\nFor legitimate callers, you can forward them directly."
        
        messages = [
            {
                "role": "system",
                "content": f"{PROMPTS['receptionist']}{calendar_context}"
            }
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add transcribed caller text as user message
        messages.append({
            "role": "user",
            "content": caller_transcription
        })
        
        # Call BosonAI text completion model to generate response
        response = await call_bosonai_with_retry(
            "chat.completions.create",
            model="Qwen3-32B-non-thinking-Hackathon",  # Use text model instead of audio understanding
            messages=messages,
            temperature=0.2,
        )
        
        if not response:
            log("Failed to get response from BosonAI (all API keys failed or timed out)")
            return None, None, None, None, 0.0
        
        model_response = response.choices[0].message.content
        
        if not model_response:
            log("No response from BosonAI")
            return None, None, None, None, 0.0
            
        log(f"🤖 AI response: {model_response}")
        
        # Strip out <think> tags if present (model's internal reasoning)
        # This prevents the thinking process from triggering spam detection
        import re
        thinking_pattern = r'<think>.*?</think>\s*'
        model_response_clean = re.sub(thinking_pattern, '', model_response, flags=re.DOTALL).strip()
        
        if model_response_clean != model_response:
            log(f"🧠 Stripped thinking tags, clean response: {model_response_clean}")
        
        # Check for special commands (look for keywords that indicate spam/forward intent)
        action = None
        response_text = model_response_clean
        caller_name = None
        
        # IMPORTANT: Ignore FORWARD_CALL and END_CALL until at least 3 exchanges have occurred
        # This ensures the AI gathers enough information before routing the call
        
        # Check for explicit commands
        if "FORWARD_CALL" in model_response_clean:
            action = "FORWARD"
            response_text = model_response_clean.replace("FORWARD_CALL", "").strip()
            if exchange_count < MIN_EXCHANGES_BEFORE_ACTION:
                log(f"⏸️ FORWARD action detected but ignoring (exchange {exchange_count + 1}/{MIN_EXCHANGES_BEFORE_ACTION})")
                action = None  # Suppress action until minimum exchanges reached
            else:
                log("⚡ ACTION: Forwarding call to BosonAI's phone")
        elif "BOOK_MEETING" in model_response_clean:
            action = "BOOK"
            response_text = model_response_clean.replace("BOOK_MEETING", "").strip()
            log("⚡ ACTION: Booking meeting at next available time")
            
            # Extract caller name from conversation history
            caller_name = extract_caller_name(conversation_history, caller_transcription)
            log(f"📝 Extracted caller name: {caller_name}")
        elif "END_CALL" in model_response_clean:
            action = "END"
            response_text = model_response_clean.replace("END_CALL", "").strip()
            if exchange_count < MIN_EXCHANGES_BEFORE_ACTION:
                log(f"⏸️ END action detected but ignoring (exchange {exchange_count + 1}/{MIN_EXCHANGES_BEFORE_ACTION})")
                action = None  # Suppress action until minimum exchanges reached
            else:
                log("⚡ ACTION: Ending call (spam detected)")
        else:
            # Fallback: detect spam indicators in the response
            # Only check for spam when it's clearly the bot dismissing the call
            spam_indicators = [
                "end this call", "end the call", "ending this call",
                "cannot assist", "can't assist", "not legitimate", 
                "telemarkeeter", "robocall", "have a good day. goodbye",
                "need to end this", "dismiss this call"
            ]
            forward_indicators = [
                "connect you", "forward", "transfer you", "put you through",
                "let me get bosonai", "patch you through"
            ]
            
            response_lower = response_text.lower()
            
            if any(indicator in response_lower for indicator in spam_indicators):
                action = "END"
                if exchange_count < MIN_EXCHANGES_BEFORE_ACTION:
                    log(f"⏸️ END action detected (keywords) but ignoring (exchange {exchange_count + 1}/{MIN_EXCHANGES_BEFORE_ACTION})")
                    action = None  # Suppress action until minimum exchanges reached
                else:
                    log("⚡ ACTION: Ending call (spam keywords detected in response)")
            elif any(indicator in response_lower for indicator in forward_indicators):
                action = "FORWARD"
                if exchange_count < MIN_EXCHANGES_BEFORE_ACTION:
                    log(f"⏸️ FORWARD action detected (keywords) but ignoring (exchange {exchange_count + 1}/{MIN_EXCHANGES_BEFORE_ACTION})")
                    action = None  # Suppress action until minimum exchanges reached
                else:
                    log("⚡ ACTION: Forwarding call (forward keywords detected in response)")

        
        # Add to conversation history (caller's transcribed text + assistant's response)
        conversation_history.append({
            "role": "user",
            "content": caller_transcription
        })
        conversation_history.append({
            "role": "assistant",
            "content": response_text
        })
        
        # Generate speech from text response (following example1.py pattern)
        log("Step 3: Generating speech from response...")
        
        # Remove content in brackets before TTS (stage directions, actions, etc.)
        # Remove [text], (text), and {text} patterns
        import re
        tts_text = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', response_text).strip()
        log(f"TTS input (brackets removed): {tts_text}")
        
        speech_response = await call_bosonai_with_retry(
            "audio.speech.create",
            model="higgs-audio-generation-Hackathon",
            voice=VOICE,
            input=tts_text,
            response_format="pcm"
        )
        
        if not speech_response:
            log("Failed to generate speech from BosonAI (all API keys failed or timed out)")
            return None, None, None, None, 0.0
        
        # Audio specs from example1.py
        # num_channels = 1
        # sample_width = 2
        # sample_rate = 24000
        
        pcm_data = speech_response.content
        
        log(f"Received {len(pcm_data)} bytes of PCM audio from BosonAI")
        
        # Convert PCM16 24kHz -> PCM16 8kHz for recording and Twilio
        pcm16_8k_full, _ = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)
        
        # Calculate audio duration for proper delay (PCM16 8kHz, mono, 2 bytes/sample)
        audio_duration_seconds = len(pcm16_8k_full) / (8000 * 2)
        log(f"Bot audio duration: {audio_duration_seconds:.2f} seconds")
        
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
        
        log("Finished streaming response to caller - will ignore audio during playback...")
        
        # Calculate exact audio duration: PCM16 8kHz, mono, 2 bytes per sample
        # Duration = total_bytes / (sample_rate * bytes_per_sample)
        audio_duration_seconds = len(pcm16_8k_full) / (8000 * 2)
        log(f"Bot audio duration: {audio_duration_seconds:.2f} seconds")
        
        # Total delay = exact audio playback time + fixed post-audio buffer
        total_delay_seconds = audio_duration_seconds + POST_AUDIO_DELAY_SECONDS
        log(f"Will block user input for {total_delay_seconds:.2f}s ({audio_duration_seconds:.2f}s audio + {POST_AUDIO_DELAY_SECONDS:.2f}s buffer)")
        
        # Execute action if needed
        if action == "FORWARD":
            log(f"📞 Forwarding call {call_sid} to {BOSONAI_PHONE_NUMBER}")
            await forward_call(call_sid)
        elif action == "BOOK":
            log(f"📅 Booking meeting for {caller_name}")
            booking_result = book_next_available(caller_name, caller_phone="", caller_email="")
            log(f"✅ Booking result: {booking_result}")
            
            # Send confirmation message to caller
            confirmation_text = f"Perfect! I've scheduled you for a 15-minute call with BosonAI. {booking_result}. You'll receive a confirmation. Thank you for calling!"
            
            # Remove content in brackets before TTS
            import re
            confirmation_tts = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', confirmation_text).strip()
            
            # Generate speech for confirmation
            speech_response = await call_bosonai_with_retry(
                "audio.speech.create",
                model="higgs-audio-generation-Hackathon",
                voice=VOICE,
                input=confirmation_tts,
                response_format="pcm"
            )
            
            if not speech_response:
                log("Failed to generate confirmation speech from BosonAI (all API keys failed or timed out)")
                # Still try to end the call even if speech failed
            else:
                pcm_data = speech_response.content
                pcm16_8k_confirmation, _ = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)
                
                # Calculate confirmation audio duration
                confirmation_duration_seconds = len(pcm16_8k_confirmation) / (8000 * 2)
                log(f"Confirmation audio duration: {confirmation_duration_seconds:.2f} seconds")
                
                # Send confirmation to caller
                chunk_size = 1600
                for i in range(0, len(pcm16_8k_confirmation), chunk_size):
                    chunk = pcm16_8k_confirmation[i:i + chunk_size]
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
                
                # Wait for confirmation to play completely
                confirmation_duration_seconds = len(pcm16_8k_confirmation) / (8000 * 2)
                log(f"Confirmation will play for {confirmation_duration_seconds:.2f} seconds...")
                
                # Actually wait for the audio to finish playing
                import asyncio
                wait_time = confirmation_duration_seconds + 0.5  # Audio duration + small buffer
                log(f"⏳ Waiting {wait_time:.2f}s for confirmation to finish before ending call...")
                await asyncio.sleep(wait_time)
            
            # End the call after booking (and after confirmation finishes playing)
            await end_call(call_sid)
        elif action == "END":
            log(f"🚫 Ending call {call_sid} (spam)")
            # Wait for the goodbye message to finish playing before hanging up
            # Audio was already sent above, now wait for it to complete
            import asyncio
            wait_time = audio_duration_seconds + 0.5  # Audio duration + small buffer
            log(f"⏳ Waiting {wait_time:.2f}s for goodbye message to finish before ending call...")
            await asyncio.sleep(wait_time)
            await end_call(call_sid)
        
        # Return total delay duration for blocking user input
        return model_response, pcm16_8k_full, action, caller_transcription, total_delay_seconds
        
    except Exception as e:
        log(f"BosonAI error: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None, None, 0.0


async def forward_call(call_sid: str):
    """Forward the call to BosonAI's personal phone number using Twilio API."""
    try:
        import httpx
        
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        
        if not account_sid or not auth_token:
            log("⚠️ TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in .env to forward calls")
            return
        
        # Update the call to dial BosonAI's number
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Calls/{call_sid}.json"
        
        # TwiML to dial BosonAI's number with extended timeout
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Please hold while I connect you to BosonAI.</Say>
    <Dial timeout="30" callerId="{BOSONAI_PHONE_NUMBER}">
        <Number>{BOSONAI_PHONE_NUMBER}</Number>
    </Dial>
    <Say>I'm sorry, BosonAI is not available right now. Please try again later. Goodbye.</Say>
</Response>"""
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                auth=(account_sid, auth_token),
                data={"Twiml": twiml}
            )
            
            if response.status_code == 200:
                log(f"✅ Call forwarded successfully to {BOSONAI_PHONE_NUMBER}")
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


# async def save_call_to_database(
#     call_sid: str,
#     from_number: str,
#     conversation_log: list,
#     transcripts: list,
#     recording_filename: str,
#     is_spam: bool
# ):
#     """
#     Save call information to the SQLiteCloud database.
#     
#     Args:
#         call_sid: Twilio call SID
#         from_number: Caller's phone number
#         conversation_log: List of conversation exchanges
#         transcripts: List of bot responses
#         recording_filename: Path to the WAV recording file
#         is_spam: Whether the call was identified as spam
#     """
#     log(f"[SAVE] Starting database save for call {call_sid}")
#     log(f"[SAVE] Recording filename: {recording_filename}")
#     log(f"[SAVE] From number: {from_number}")
#     log(f"[SAVE] Is spam: {is_spam}")
#     
#     if not SQLITE_URL:
#         log("⚠️ Database not configured - skipping save")
#         return
#     
#     try:
#         # Extract caller name and call description from conversation
#         caller_name = "Unknown Caller"
#         description = "No conversation"
#         
#         # Try to extract name from bot responses
#         for entry in conversation_log:
#             if entry.get('speaker') == 'Bot':
#                 text = entry.get('text', '')
#                 # Look for patterns like "Thank you [Name]" or "Hi [Name]"
#                 if 'thank you' in text.lower() or 'thanks' in text.lower() or 'hi ' in text.lower():
#                     words = text.split()
#                     for i, word in enumerate(words):
#                         if word.lower() in ['thank', 'thanks', 'hi', 'hello'] and i + 1 < len(words):
#                             potential_name = words[i + 1].strip('.,!?')
#                             if potential_name and potential_name[0].isupper() and len(potential_name) > 1:
#                                 caller_name = potential_name
#                                 log(f"[SAVE] Extracted caller name: {caller_name}")
#                                 break
#         
#         # Create a concise, high-level description
#         if is_spam:
#             # For spam calls, create a short description
#             spam_types = {
#                 'warranty': 'Car warranty scam',
#                 'irs': 'IRS scam call',
#                 'microsoft': 'Tech support scam',
#                 'computer': 'Tech support scam',
#                 'student loan': 'Student loan scam',
#                 'credit card': 'Credit card offer',
#                 'vacation': 'Vacation scam',
#                 'prize': 'Prize scam',
#                 'social security': 'Social Security scam'
#             }
#             
#             # Check transcripts for spam keywords
#             description = "Spam call"
#             if transcripts:
#                 transcript_text = ' '.join(transcripts).lower()
#                 for keyword, desc in spam_types.items():
#                     if keyword in transcript_text:
#                         description = desc
#                         break
#         else:
#             # For legitimate calls, extract the main topic
#             if transcripts and len(transcripts) > 0:
#                 # Get the caller's stated purpose from the conversation
#                 first_response = transcripts[0].replace("FORWARD_CALL", "").replace("END_CALL", "").strip()
#                 
#                 # Extract key phrases
#                 if 'hackathon' in first_response.lower():
#                     description = "Hackathon related inquiry"
#                 elif 'project' in first_response.lower():
#                     description = "Project discussion"
#                 elif 'meeting' in first_response.lower():
#                     description = "Meeting request"
#                 elif 'interview' in first_response.lower():
#                     description = "Interview scheduled"
#                 else:
#                     # Take first sentence as description (limit to 60 chars)
#                     sentences = first_response.split('.')
#                     if sentences:
#                         description = sentences[0].strip()
#                         if len(description) > 60:
#                             description = description[:60] + "..."
#         
#         log(f"[SAVE] Caller: {caller_name}")
#         log(f"[SAVE] Description: {description}")
#         
#         # Create Voicemail object
#         voicemail = Voicemail(
#             id=0,  # Will be auto-generated by database
#             number=from_number if from_number and from_number != 'unknown' and from_number != 'Unknown' else 'Unknown Number',
#             name=caller_name,
#             description=description,
#             spam=is_spam,
#             date=datetime.now(timezone.utc),
#             unread=True,
#             recording=recording_filename
#         )
#         
#         log(f"[SAVE] Calling add_row() to save to database...")
#         # Save to database
#         add_row(SQLITE_URL, voicemail)
#         log(f"✅ Call saved to database: {caller_name} ({from_number}) - Spam: {is_spam}")
#         
#     except Exception as e:
#         log(f"❌ Failed to save call to database: {e}")
#         import traceback
#         traceback.print_exc()


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


async def send_greeting(websocket: WebSocket, stream_sid: str):
    """Send initial greeting when call starts."""
    if not boson_clients:
        return None, 0.0, None
    
    try:
        greeting_text = "Hi, you've reached the office of BosonAI. How can I help you today?"
        log(f"Sending greeting: {greeting_text}")
        
        # Remove content in brackets before TTS
        import re
        greeting_tts = re.sub(r'\[.*?\]|\(.*?\)|\{.*?\}', '', greeting_text).strip()
        
        # Generate speech from greeting
        speech_response = await call_bosonai_with_retry(
            "audio.speech.create",
            model="higgs-audio-generation-Hackathon",
            voice=VOICE,
            input=greeting_tts,
            response_format="pcm"
        )
        
        if not speech_response:
            log("Failed to generate greeting from BosonAI (all API keys failed or timed out)")
            return None, 0.0, None
        
        pcm_data = speech_response.content
        log(f"Received {len(pcm_data)} bytes of PCM audio for greeting")
        
        # Convert PCM16 24kHz -> PCM16 8kHz for recording and Twilio
        pcm16_8k_full, _ = audioop.ratecv(pcm_data, 2, 1, 24000, 8000, None)
        
        # Calculate greeting audio duration
        greeting_duration_seconds = len(pcm16_8k_full) / (8000 * 2)
        log(f"Greeting audio duration: {greeting_duration_seconds:.2f} seconds")
        
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
        
        log("Greeting sent - will ignore audio during playback...")
        
        # Calculate exact audio duration: PCM16 8kHz, mono, 2 bytes per sample
        # Duration = total_bytes / (sample_rate * bytes_per_sample)
        greeting_duration_seconds = len(pcm16_8k_full) / (8000 * 2)
        log(f"Greeting audio duration: {greeting_duration_seconds:.2f} seconds")
        
        # Total delay = exact audio playback time + fixed post-audio buffer
        total_delay_seconds = greeting_duration_seconds + POST_AUDIO_DELAY_SECONDS
        log(f"Will block user input for {total_delay_seconds:.2f}s ({greeting_duration_seconds:.2f}s audio + {POST_AUDIO_DELAY_SECONDS:.2f}s buffer)")
        
        return greeting_text, total_delay_seconds, pcm16_8k_full
        
    except Exception as e:
        log(f"Error sending greeting: {e}")
        return None, 0.0, None  # Return 0 duration on error


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
    from_number = "unknown"
    call_start_time = datetime.now()
    final_action = None
    mulaw_buffer = bytearray()
    transcripts = []
    conversation_log = []  # Detailed conversation with caller and bot
    conversation_history = []  # Track full conversation
    greeting_sent = False
    exchange_count = 0  # Track number of caller-bot exchanges (greeting doesn't count)
    
    # Stereo recording buffer for bot audio
    bot_audio_buffer = bytearray()
    
    # Track bot speaking state to prevent VAD during bot responses
    bot_is_speaking = False
    bot_speaking_until = None  # Timestamp when bot will finish speaking + buffer delay
    bot_finished_time = None  # Track when bot finished speaking for debounce
    
    # Callback for when VAD detects a complete utterance
    async def on_utterance(pcm16_16k: bytes, speech_duration_ms: int):
        nonlocal bot_is_speaking, buf_pcm16_8k, sil_ms, speech_ms, utt_ms, in_speech, final_action, mulaw_buffer, exchange_count, bot_speaking_until, bot_finished_time, bot_audio_buffer
        
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
        if stream_sid:  # Make sure we have a stream_sid
            from datetime import timedelta
            # Removed wav_file argument
            response, bot_audio, action, caller_text, delay_seconds = await process_utterance_and_respond(pcm16_16k, websocket, stream_sid, conversation_history, call_sid, exchange_count=exchange_count)
            if response:
                transcripts.append(response)
                # Increment exchange counter (caller spoke + bot responded = 1 exchange)
                exchange_count += 1
                log(f"📊 Exchange count: {exchange_count}")
                # Track final action
                if action:
                    final_action = action
                # Log the exchange with caller transcription
                conversation_log.append({
                    "speaker": "Caller",
                    "duration_ms": speech_duration_ms,
                    "audio_size": len(pcm16_16k),
                    "text": caller_text if caller_text else None,
                    "timestamp": datetime.now().isoformat()
                })
                conversation_log.append({
                    "speaker": "Bot",
                    "text": clean_text_for_transcript(response),
                    "timestamp": datetime.now().isoformat()
                })
                
                # Add bot audio to buffer for stereo recording
                if bot_audio:
                    bot_audio_buffer.extend(bot_audio)
                
                # Save transcript after each exchange (overwrite same file)
                save_transcript(call_sid, from_number, conversation_log, call_start_time, datetime.now(), final_action, call_in_progress=True)
                
                # Set timestamp when bot will finish speaking (now + delay_seconds)
                bot_speaking_until = datetime.now() + timedelta(seconds=delay_seconds)
                log(f"🔇 Blocking user input until {bot_speaking_until.strftime('%H:%M:%S.%f')[:-3]} ({delay_seconds:.2f}s from now)")
        else:
            log("Warning: stream_sid or call_sid not set yet, skipping utterance")
        
        # Re-enable VAD immediately (timestamp check handles blocking)
        bot_is_speaking = False
        
        # CRITICAL: Clear mulaw_buffer to discard any audio that came in during bot speaking
        # This prevents echo/noise from being processed as the next utterance
        mulaw_buffer.clear()
        
        # Clear VAD buffers again after bot response to ensure clean slate
        buf_pcm16_8k.clear()
        sil_ms = speech_ms = utt_ms = 0
        in_speech = False
        
        log(f"✅ Bot response sent - user input blocked until {bot_speaking_until.strftime('%H:%M:%S.%f')[:-3] if bot_speaking_until else 'now'}")
    
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
                
                # Extract caller info if available
                from_number = data['start'].get('customParameters', {}).get('from', 'unknown')
                call_start_time = datetime.now()
                log(f"Call from: {from_number}")
                
                # Create WAV file for this call (8 kHz native PSTN rate)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{RECORDINGS_DIR}/call_{call_sid}_{timestamp}.wav"
                recording_filename = f"call_{call_sid}_{timestamp}.wav"  # Store just the filename
                
                # Open WAV file with proper settings for mulaw -> PCM conversion
                wav_file = wave.open(filename, 'wb')
                wav_file.setnchannels(2)  # Stereo (Left=Caller, Right=Bot)
                wav_file.setsampwidth(2)  # 2 bytes (16-bit PCM)
                wav_file.setframerate(8000)  # 8000 Hz (native PSTN)
                
                log(f"Recording to WAV (8kHz Stereo): {filename}")
                log(f"VAD enabled: endpointing at {END_SIL_MS}ms silence, min speech {MIN_SPEECH_MS}ms")
                log(f"BosonAI bot ready")
            
            elif data['event'] == "media":
                # Process media for recording and VAD
                payload = data['media']['payload']
                mulaw_data = base64.b64decode(payload)
                
                # Write to stereo WAV file
                if wav_file:
                    # Caller audio (Left channel)
                    caller_pcm = audioop.ulaw2lin(mulaw_data, 2)
                    
                    # Bot audio (Right channel)
                    # Pop corresponding amount of audio from buffer
                    chunk_len = len(caller_pcm)
                    if len(bot_audio_buffer) >= chunk_len:
                        bot_pcm = bot_audio_buffer[:chunk_len]
                        del bot_audio_buffer[:chunk_len]
                    else:
                        # Not enough bot audio, pad with silence
                        bot_pcm = bot_audio_buffer[:]
                        del bot_audio_buffer[:]
                        padding = bytes(chunk_len - len(bot_pcm))
                        bot_pcm += padding
                    
                    # Create stereo frame: Left=Caller, Right=Bot
                    # audioop.tostereo(fragment, width, lfactor, rfactor)
                    # lfactor=1, rfactor=0 -> Left channel
                    # lfactor=0, rfactor=1 -> Right channel
                    left_stereo = audioop.tostereo(caller_pcm, 2, 1, 0)
                    right_stereo = audioop.tostereo(bot_pcm, 2, 0, 1)
                    
                    # Combine channels
                    stereo_frame = audioop.add(left_stereo, right_stereo, 2)
                    wav_file.writeframes(stereo_frame)
                
                # Skip VAD processing if bot is speaking (but keep recording above)
                if bot_is_speaking:
                    continue
                
                # Check if we're still in the blocking period after bot spoke
                if bot_speaking_until is not None:
                    import time
                    current_time = datetime.now()
                    if current_time < bot_speaking_until:
                        # Still in blocking period - skip VAD processing
                        continue
                    else:
                        # Blocking period over - clear the timer and resume normal processing
                        log(f"✅ Blocking period over - resuming VAD at {current_time.strftime('%H:%M:%S.%f')[:-3]}")
                        bot_speaking_until = None
                
                if not has_seen_media:
                    log("Media message received - streaming audio with VAD...")
                    log("Additional media messages are being suppressed from logs...")
                    has_seen_media = True
                    
                    # Send greeting after first media packet (ensures stream is ready)
                    if not greeting_sent and stream_sid:
                        from datetime import timedelta
                        bot_is_speaking = True  # Prevent VAD during greeting
                        # Removed wav_file argument
                        greeting_result = await send_greeting(websocket, stream_sid)
                        
                        if greeting_result:
                            greeting, delay_seconds, bot_audio = greeting_result
                            if greeting:
                                conversation_history.append({
                                    "role": "assistant",
                                    "content": greeting
                                })
                                conversation_log.append({
                                    "speaker": "Bot",
                                    "text": clean_text_for_transcript(greeting),
                                    "timestamp": datetime.now().isoformat()
                                })
                                
                                # Add greeting audio to buffer
                                if bot_audio:
                                    bot_audio_buffer.extend(bot_audio)
                                
                                # Save transcript after greeting (overwrite same file)
                                save_transcript(call_sid, from_number, conversation_log, call_start_time, datetime.now(), final_action, call_in_progress=True)
                            
                            # Set timestamp when bot will finish speaking (now + delay_seconds)
                            bot_speaking_until = datetime.now() + timedelta(seconds=delay_seconds)
                            log(f"🔇 Blocking user input until {bot_speaking_until.strftime('%H:%M:%S.%f')[:-3]} ({delay_seconds:.2f}s from now)")
                        
                        # Re-enable VAD after greeting is sent (timestamp check handles blocking)
                        bot_is_speaking = False
                        
                        # Clear any accumulated audio during greeting
                        mulaw_buffer.clear()
                        buf_pcm16_8k.clear()
                        sil_ms = speech_ms = utt_ms = 0
                        in_speech = False
                        greeting_sent = True
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
        call_end_time = datetime.now()
        
        # Close the WAV file
        if wav_file:
            wav_file.close()
            log(f"WAV file saved successfully - ready to play!")
        
        # Save final transcript to file (mark as complete)
        if conversation_log and call_sid:
            save_transcript(call_sid, from_number, conversation_log, call_start_time, call_end_time, final_action, call_in_progress=False)
        # Determine if call was spam based on conversation
        # is_spam = False
        # for entry in conversation_log:
        #     if entry.get('speaker') == 'Bot':
        #         text = entry.get('text', '').lower()
        #         if 'spam' in text or 'end_call' in text or 'scam' in text:
        #             is_spam = True
        #             break
        
        # Save call to database
        # if call_sid and recording_filename:
        #     await save_call_to_database(
        #         call_sid=call_sid,
        #         from_number=from_number,
        #         conversation_log=conversation_log,
        #         transcripts=transcripts,
        #         recording_filename=recording_filename,
        #         is_spam=is_spam
        #     )
        
        # Log full conversation
        if conversation_log:
            log(f"\n{'='*60}")
            log(f"CALL TRANSCRIPT - {len([x for x in conversation_log if x['speaker'] == 'Caller'])} exchanges")
            log(f"{'='*60}")
            for i, entry in enumerate(conversation_log, 1):
                if entry['speaker'] == 'Caller':
                    caller_text = entry.get('text', None)
                    duration = entry.get('duration_ms', 0)
                    audio_size = entry.get('audio_size', 0)
                    if caller_text:
                        log(f"[{i}] 📞 Caller: \"{caller_text}\" ({duration}ms, {audio_size} bytes)")
                    else:
                        log(f"[{i}] 📞 Caller: [Audio {duration}ms, {audio_size} bytes - no transcription]")
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


@app.api_route("/", methods=["GET", "POST"])
async def root(request: Request):
    """Health check endpoint - accepts both GET and POST"""
    if request.method == "POST":
        # If Twilio is POSTing to root, return TwiML
        host = request.headers.get('host', f'localhost:{HTTP_SERVER_PORT}')
        protocol = 'wss' if request.url.scheme == 'https' else 'ws'
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{protocol}://{host}/media-stream" />
    </Connect>
</Response>"""
        return Response(content=twiml, media_type="application/xml")
    
    # GET request - return JSON status
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


@app.api_route("/status-callback", methods=["GET", "POST"])
async def status_callback(request: Request):
    """Handle Twilio status callbacks (for call status updates)"""
    return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")


@app.api_route("/call-events", methods=["GET", "POST"])
async def call_events(request: Request):
    """Handle any call event webhooks from Twilio"""
    return Response(content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>', media_type="application/xml")


# @app.get("/voicemails")
# async def get_voicemails():
#     """Retrieve all voicemails from the database"""
#     log("[API] GET /voicemails - Fetching voicemails from database")
#     
#     if not SQLITE_URL:
#         log("[API] ERROR: Database not configured")
#         return {"error": "Database not configured"}
#     
#     try:
#         from database.db_actions import read_table
#         voicemails = read_table(SQLITE_URL)
#         
#         log(f"[API] Retrieved {len(voicemails)} voicemails from database")
#         
#         # Convert to JSON-serializable format
#         result = []
#         for vm in voicemails:
#             result.append({
#                 "id": vm.id,
#                 "number": vm.number,
#                 "name": vm.name,
#                 "description": vm.description,
#                 "spam": vm.spam,
#                 "date": vm.date.isoformat(),
#                 "unread": vm.unread,
#                 "recording": vm.recording
#             })
#         
#         log(f"[API] Returning {len(result)} voicemails to frontend")
#         return {"voicemails": result, "count": len(result)}
#     except Exception as e:
#         log(f"[API] ERROR fetching voicemails: {e}")
#         import traceback
#         traceback.print_exc()
#         return {"error": str(e)}


# @app.get("/voicemail/{voicemail_id}/recording")
# async def get_voicemail_recording(voicemail_id: int):
#     """Get the audio recording for a specific voicemail"""
#     if not SQLITE_URL:
#         return {"error": "Database not configured"}
#     
#     try:
#         from database.db_actions import get_recording
#         recording_bytes = get_recording(SQLITE_URL, voicemail_id)
#         
#         if recording_bytes:
#             from fastapi.responses import Response
#             return Response(content=recording_bytes, media_type="audio/wav")
#         else:
#             return {"error": "Recording not found"}
#     except Exception as e:
#         return {"error": str(e)}


if __name__ == '__main__':
    print(f"Server listening on: http://localhost:{HTTP_SERVER_PORT}")
    print("Starting FastAPI server with WebSocket support...")
    uvicorn.run(app, host="0.0.0.0", port=HTTP_SERVER_PORT)
