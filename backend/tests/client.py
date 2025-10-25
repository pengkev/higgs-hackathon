"""
Minimal asyncio websocket client that:
- reads a local WAV file ('input.wav')
- sends the WAV bytes as binary frames
- sends {"type":"end_utterance"} JSON to signal end
- waits for transcript JSON and streamed TTS bytes, writes them to out_tts.wav and plays it.

Run:
  python client.py

Requires:
  pip install websockets soundfile sounddevice
"""
import asyncio
import json
import websockets
import soundfile as sf
import sounddevice as sd

WS_URL = "ws://localhost:9000/ws/audio"
INPUT_WAV = "input.wav"
OUT_WAV = "out_tts.wav"

async def run_client():
    async with websockets.connect(WS_URL, max_size=2**25) as ws:
        # send the WAV file bytes
        with open(INPUT_WAV, "rb") as f:
            wav_bytes = f.read()
            await ws.send(wav_bytes)
        # signal end of utterance
        await ws.send(json.dumps({"type": "end_utterance"}))

        tts_buffer = bytearray()
        transcript_text = None

        while True:
            msg = await ws.recv()
            # websockets library returns str for text frames, bytes for binary ones
            if isinstance(msg, bytes):
                # TTS chunk
                tts_buffer.extend(msg)
            else:
                # JSON/control message
                try:
                    obj = json.loads(msg)
                except Exception:
                    print("Received non-json text:", msg)
                    continue

                if obj.get("type") == "transcript":
                    transcript_text = obj.get("text", "")
                    print("Transcript:", transcript_text)
                elif obj.get("type") == "tts_done":
                    # Save TTS bytes to file (raw PCM or mp3 depending on your server settings).
                    # Here we assume response_format == "pcm" and the server used WAV/PCM encoding.
                    with open(OUT_WAV, "wb") as f:
                        f.write(tts_buffer)
                    print("Saved TTS to", OUT_WAV)
                    # Try to play — this will work only if the bytes are a proper WAV or PCM file.
                    try:
                        data, sr = sf.read(OUT_WAV, dtype='float32')
                        print("Playing TTS...")
                        sd.play(data, sr)
                        sd.wait()
                    except Exception as e:
                        print("Could not play audio:", e)
                    break
                elif obj.get("type") == "error":
                    print("Server error:", obj.get("message"))
                else:
                    print("Unknown control message:", obj)

if __name__ == "__main__":
    asyncio.run(run_client())