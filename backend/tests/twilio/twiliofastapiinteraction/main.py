from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import Response
import json
import base64
import uvicorn
from datetime import datetime
import os
import audioop
import wave

HTTP_SERVER_PORT = 8080
RECORDINGS_DIR = "recordings"

# Create recordings directory if it doesn't exist
os.makedirs(RECORDINGS_DIR, exist_ok=True)

app = FastAPI()

def log(msg, *args):
    print(f"Media WS: {msg}", *args)


@app.post('/twiml')
async def return_twiml(request: Request):
    """Return TwiML to connect the call to our WebSocket"""
    print("POST TwiML")
    
    # Get the host from the request to build the WebSocket URL
    host = request.headers.get('host', f'localhost:{HTTP_SERVER_PORT}')
    protocol = 'wss' if request.url.scheme == 'https' else 'ws'
    
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Start>
        <Stream url="{protocol}://{host}/media-stream" />
    </Start>
    <Say>This call is being streamed and recorded.</Say>
    <Pause length="30"/>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """Handle Twilio media stream WebSocket connection"""
    await websocket.accept()
    log("Connection accepted")
    
    count = 0
    has_seen_media = False
    wav_file = None
    call_sid = None
    stream_sid = None
    
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
                
                # Create WAV file for this call
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{RECORDINGS_DIR}/call_{call_sid}_{timestamp}.wav"
                
                # Open WAV file with proper settings for mulaw -> PCM conversion
                wav_file = wave.open(filename, 'wb')
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 2 bytes (16-bit PCM)
                wav_file.setframerate(8000)  # 8000 Hz
                
                log(f"Recording to WAV: {filename}")
            
            elif data['event'] == "media":
                if not has_seen_media:
                    log("Media message received - streaming audio...")
                    log("Additional media messages are being suppressed from logs...")
                    has_seen_media = True
                
                # Decode, convert to PCM, and save the audio data in real-time
                if wav_file:
                    payload = data['media']['payload']  # base64 encoded mulaw audio
                    mulaw_data = base64.b64decode(payload)
                    
                    # Convert mulaw to linear PCM (16-bit)
                    pcm_data = audioop.ulaw2lin(mulaw_data, 2)
                    
                    # Write PCM data to WAV file
                    wav_file.writeframes(pcm_data)
            
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
    finally:
        # Close the WAV file
        if wav_file:
            wav_file.close()
            log(f"WAV file saved successfully - ready to play!")
        log(f"Connection closed. Received a total of {count} messages")


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "message": "Twilio Media Stream FastAPI Server",
        "endpoints": {
            "twiml": "/twiml (POST)",
            "websocket": "/media-stream (WebSocket)"
        }
    }


if __name__ == '__main__':
    print(f"Server listening on: http://localhost:{HTTP_SERVER_PORT}")
    print("Starting FastAPI server with WebSocket support...")
    uvicorn.run(app, host="0.0.0.0", port=HTTP_SERVER_PORT)
