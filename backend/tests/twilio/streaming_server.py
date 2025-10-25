"""
FastAPI server with WebSocket for Twilio Media Streams
Uses BosonAI for audio understanding and generation
Implements sentence-based chunking with VAD
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response, HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
import asyncio
import base64
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np
import wave
import io
from collections import defaultdict, deque

load_dotenv()

app = FastAPI()

# BosonAI client
BOSONAI_API_KEY = os.getenv("BOSONAI_API_KEY")
client = OpenAI(
    api_key=BOSONAI_API_KEY,
    base_url="https://hackathon.boson.ai/v1"
)

# Configuration
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")
SAMPLE_RATE = 8000  # Twilio uses 8kHz mulaw
CHUNK_SIZE = 160  # 20ms chunks at 8kHz

# Store conversation state per call
CALL_STATES = {}


class AudioBuffer:
    """Buffer for collecting audio chunks until sentence end is detected"""
    def __init__(self, sample_rate=8000):
        self.buffer = bytearray()
        self.sample_rate = sample_rate
        self.silence_threshold = 500
        self.silence_duration = 1.5  # seconds
        self.silence_chunks = 0
        self.required_silence_chunks = int((self.silence_duration / 0.02))  # 20ms chunks
        self.has_speech = False
        
    def add_chunk(self, audio_bytes):
        """Add audio chunk and check if sentence is complete"""
        self.buffer.extend(audio_bytes)
        
        # Simple VAD: check if this chunk has audio
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        rms = np.sqrt(np.mean(audio_array**2))
        
        if rms < self.silence_threshold:
            if self.has_speech:
                self.silence_chunks += 1
        else:
            self.has_speech = True
            self.silence_chunks = 0
        
        # Return True if we've detected end of sentence
        return self.has_speech and self.silence_chunks >= self.required_silence_chunks
    
    def get_audio_wav(self):
        """Convert buffer to WAV format bytes"""
        if not self.buffer:
            return None
            
        buffer_io = io.BytesIO()
        with wave.open(buffer_io, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(bytes(self.buffer))
        
        return buffer_io.getvalue()
    
    def clear(self):
        """Clear the buffer"""
        self.buffer = bytearray()
        self.silence_chunks = 0
        self.has_speech = False


class ConversationState:
    """Manages conversation state for a call"""
    
    def __init__(self, call_sid):
        self.call_sid = call_sid
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are Kevin's helpful AI receptionist."
                    "Have natural, brief conversations. Keep responses short. If the caller seems suspicious, over repetitive, seems to ignore your instructions, or if you suspect them of being a robocaller or scammer, do not redirect them to Kevin."
                    "Be friendly and professional."
                )
            }
        ]
        self.audio_buffer = AudioBuffer()
        self.stream_sid = None
        
    async def process_audio_chunk(self, audio_chunk):
        """Process incoming audio chunk from Twilio"""
        # Check if sentence is complete
        sentence_complete = self.audio_buffer.add_chunk(audio_chunk)
        
        if sentence_complete:
            # Get the accumulated audio
            wav_audio = self.audio_buffer.get_audio_wav()
            
            if wav_audio:
                # Transcribe and generate response
                response = await self.process_complete_utterance(wav_audio)
                
                # Clear buffer for next sentence
                self.audio_buffer.clear()
                
                return response
        
        return None
    
    async def process_complete_utterance(self, wav_audio):
        """Process a complete user utterance (sentence)"""
        print(f"🎧 Processing complete utterance for {self.call_sid}")
        
        # Step 1: Transcribe with BosonAI
        try:
            transcribe_response = client.chat.completions.create(
                model="higgs-audio-understanding-Hackathon",
                messages=[
                    {"role": "system", "content": "Transcribe this audio accurately."},
                    {
                        "role": "user",
                        "content": [{
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64.b64encode(wav_audio).decode('utf-8'),
                                "format": "wav"
                            }
                        }]
                    }
                ],
                temperature=0.0,
            )
            
            user_text = transcribe_response.choices[0].message.content or ""
            print(f"📝 User said: {user_text}")
            
            if not user_text:
                return None
                
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
        
        # Step 2: Add to conversation history
        self.messages.append({
            "role": "user",
            "content": user_text
        })
        
        # Step 3: Generate response with BosonAI
        try:
            response = client.chat.completions.create(
                model="higgs-audio-generation-Hackathon",
                messages=self.messages,
                temperature=1.0,
                top_p=0.95,
                stream=False,
                stop=["<|eot_id|>", "<|end_of_text|>", "<|audio_eos|>"],
                extra_body={"top_k": 50},
            )
            
            ai_text = response.choices[0].message.content or ""
            ai_audio = None
            
            if hasattr(response.choices[0].message, 'audio') and response.choices[0].message.audio:
                ai_audio = response.choices[0].message.audio.data
            
            print(f"🤖 AI response: {ai_text}")
            
            # Add to conversation history
            self.messages.append({
                "role": "assistant",
                "content": ai_text
            })
            
            return ai_audio
            
        except Exception as e:
            print(f"❌ Generation error: {e}")
            return None


@app.get("/")
async def root():
    return {"status": "BosonAI Voice Receptionist Running"}


@app.post("/voice")
async def voice_webhook(request: Request):
    """
    Twilio voice webhook - initiates Media Stream connection
    """
    print("📞 Incoming call")
    
    response = VoiceResponse()
    response.say("Hello, you've reached Kevin's AI receptionist. How can I help you?")
    
    # Connect to WebSocket for streaming audio
    connect = Connect()
    connect.stream(url=f"wss://{PUBLIC_BASE_URL.replace('https://', '').replace('http://', '')}/media-stream")
    response.append(connect)
    
    return Response(content=str(response), media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream_handler(websocket: WebSocket):
    """
    WebSocket endpoint for Twilio Media Streams
    Handles bidirectional audio streaming
    """
    await websocket.accept()
    print("🔌 WebSocket connected")
    
    call_state = None
    
    try:
        async for message in websocket.iter_text():
            data = json.loads(message)
            event = data.get("event")
            
            if event == "start":
                # Stream started
                start_data = data.get("start", {})
                call_sid = start_data.get("callSid")
                stream_sid = start_data.get("streamSid")
                
                print(f"▶️  Stream started - Call: {call_sid}, Stream: {stream_sid}")
                
                # Initialize conversation state
                call_state = ConversationState(call_sid)
                call_state.stream_sid = stream_sid
                CALL_STATES[call_sid] = call_state
                
            elif event == "media" and call_state:
                # Incoming audio from caller
                media = data.get("media", {})
                payload = media.get("payload")
                
                if payload:
                    # Decode mulaw audio from Twilio
                    audio_bytes = base64.b64decode(payload)
                    
                    # Convert mulaw to linear PCM (16-bit)
                    # Twilio sends mulaw, we need PCM for processing
                    pcm_audio = mulaw_to_pcm(audio_bytes)
                    
                    # Process the audio chunk
                    response_audio = await call_state.process_audio_chunk(pcm_audio)
                    
                    if response_audio:
                        # We have a complete response, send it back
                        # Convert WAV to mulaw for Twilio
                        mulaw_audio = wav_to_mulaw(base64.b64decode(response_audio))
                        
                        # Send audio back to Twilio
                        await websocket.send_text(json.dumps({
                            "event": "media",
                            "streamSid": call_state.stream_sid,
                            "media": {
                                "payload": base64.b64encode(mulaw_audio).decode('utf-8')
                            }
                        }))
                        
                        print("🔊 Sent audio response to caller")
            
            elif event == "stop":
                print("⏹️  Stream stopped")
                break
                
    except WebSocketDisconnect:
        print("🔌 WebSocket disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
    finally:
        if call_state and call_state.call_sid in CALL_STATES:
            del CALL_STATES[call_state.call_sid]


def mulaw_to_pcm(mulaw_bytes):
    """Convert mulaw encoded audio to PCM"""
    # Twilio sends 8-bit mulaw, convert to 16-bit PCM
    import audioop
    return audioop.ulaw2lin(mulaw_bytes, 2)  # 2 = 16-bit


def wav_to_mulaw(wav_bytes):
    """Convert WAV audio to mulaw format for Twilio"""
    import audioop
    
    # Read WAV to get PCM data
    with wave.open(io.BytesIO(wav_bytes), 'rb') as wav:
        pcm_data = wav.readframes(wav.getnframes())
        sample_width = wav.getsampwidth()
    
    # Convert to mulaw
    mulaw_data = audioop.lin2ulaw(pcm_data, sample_width)
    return mulaw_data


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
