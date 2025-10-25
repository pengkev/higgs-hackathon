# BosonAI Bidirectional Streaming Setup

Your FastAPI server now supports **real-time bidirectional audio streaming** with BosonAI! When you call your Twilio number, you can have a live conversation with the AI bot.

## 🎯 How It Works

1. **You call** your Twilio number
2. **Twilio connects** to your FastAPI server via ngrok
3. **VAD detects** when you stop speaking (800ms silence)
4. **Your audio** is sent to BosonAI for understanding
5. **BosonAI responds** with streaming audio back to you in real-time
6. **Conversation continues** - you can keep talking back and forth

## 🚀 Setup

### 1. Environment Variables

Make sure your `.env` file has:

```bash
BOSONAI_API_KEY=your_boson_api_key_here
```

### 2. Start the Server

```powershell
cd C:\Users\kevp9\Documents\GitHub\higgshackathon\backend
python main.py
```

### 3. Start ngrok

In another terminal:

```powershell
cd C:\Users\kevp9\Documents\GitHub\higgshackathon\backend
ngrok http 8080
```

### 4. Configure Twilio

1. Copy your ngrok URL (e.g., `https://abc123.ngrok.io`)
2. Go to your Twilio phone number configuration
3. Set "A Call Comes In" webhook to: `https://abc123.ngrok.io/twiml`
4. Method: **HTTP POST**

## 📞 Making a Call

1. Call your Twilio number
2. Wait for the connection (you'll hear nothing at first - this is normal)
3. **Start speaking** - say something like "Hello, is anyone there?"
4. **Stop speaking** and wait ~800ms for VAD to detect end of speech
5. **BosonAI will respond** - you'll hear the AI assistant speaking back to you
6. **Continue the conversation** - keep talking back and forth

## 🔧 Technical Details

### Audio Pipeline

**Incoming (Caller → BosonAI)**:

```
Caller (PSTN 8kHz μ-law)
→ Twilio WebSocket
→ Decode to PCM16 8kHz
→ Upsample to PCM16 16kHz
→ Send to BosonAI
```

**Outgoing (BosonAI → Caller)**:

```
BosonAI (PCM16 24kHz streaming)
→ Downsample to PCM16 8kHz
→ Encode to μ-law 8kHz
→ Twilio WebSocket
→ Caller hears response
```

### VAD Configuration

Located in `main.py`:

```python
VAD_MODE = 2           # 0-3 (3=most aggressive)
FRAME_MS = 20          # Frame duration
END_SIL_MS = 800       # Silence threshold to end utterance
MAX_UTT_MS = 10000     # Max utterance length (10 seconds)
```

### System Prompt

The AI is configured as a receptionist:

```python
"You are a helpful receptionist assistant. Respond to the caller
professionally and determine if this is a legitimate call or spam.
Keep responses brief and natural."
```

You can customize this in the `process_utterance_and_respond()` function.

## 📝 What Gets Logged

When a call comes in, you'll see:

```
POST TwiML
Media WS:  Connection accepted
Media WS:  Start Message received: ...
Media WS:  Call from: +1234567890
Media WS:  Recording to WAV (8kHz): recordings/call_CAxxxx_20251025_xxxxxx.wav
Media WS:  VAD enabled: endpointing at 800ms silence
Media WS:  BosonAI bot ready - caller can now speak
Media WS:  Media message received - streaming audio with VAD...
Media WS:  Utterance detected: 2400ms speech, 800ms silence
Media WS:  Sending audio to BosonAI for understanding and response...
Media WS:  Streaming BosonAI response back to caller...
Media WS:  BosonAI response: Hello! Thank you for calling. How can I help you today?
```

## 🎙️ Recordings

All calls are automatically recorded to:

```
backend/recordings/call_{CallSID}_{timestamp}.wav
```

These are saved at native 8kHz PSTN quality for archival purposes.

## 🐛 Troubleshooting

### "No audio from bot"

- Check that `BOSONAI_API_KEY` is set correctly
- Look for BosonAI errors in the terminal logs

### "Bot cuts me off"

- Increase `END_SIL_MS` if the bot responds too quickly
- Current setting: 800ms of silence triggers response

### "Delay/latency"

- Normal: ~1-2 seconds for BosonAI processing + streaming
- Check your internet connection
- ngrok adds some latency (consider using production ngrok or direct hosting)

### "Bot doesn't hear me"

- VAD might be too aggressive - lower `VAD_MODE` from 2 to 1
- Check that Twilio is sending audio (look for "Media message received" log)

## 🔐 Security Note

Remember to:

- Keep your `.env` file secure (it's in `.gitignore`)
- Use ngrok auth token for better security
- Consider rate limiting for production use

## 🎉 Next Steps

1. **Customize the system prompt** to match your use case
2. **Adjust VAD settings** for your preferred conversation style
3. **Add database logging** to track calls and responses
4. **Build a frontend** to view call transcripts and recordings

Have fun talking to your AI receptionist! 🤖📞
