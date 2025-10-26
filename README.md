# HiggsCeptionist — AI Call Screener & Message Manager

A voice-first AI receptionist that answers your phone line, **talks** to callers in real time, screens spam, **forwards legitimate calls** to your personal phone, and **saves call summaries + recordings** to a cloud database. A lightweight React Native app shows your inbox.

Built with **BosonAI Higgs** audio models over **Twilio Media Streams**, a **FastAPI** backend, **SQLiteCloud**, and **Google Calendar**.

---

## Features

- **Natural voice conversations** — no IVR menus, just talk.
- **Real-time AI screening** — understands intent during the call.
- **Smart spam detection** — auto-flags/ends obvious scams.
- **Call forwarding** — legit callers are connected to your phone.
- **Google Calendar aware** — routes based on availability; can book meetings.
- **AI summaries & transcripts** — saved with the call record.
- **Full recordings** — WAV saved, referenced from the DB.
- **Multi-API-key failover** — rotate up to 5 BosonAI keys.
- **Voice Activity Detection (VAD)** — smooth turn-taking.

---

## Architecture

```
Caller (PSTN)
    |
    v
Twilio Phone Number
    |
    +-- POST /twiml ---------------------> FastAPI (8080)
    |                                      |
    +-- WebSocket /media-stream ---------->+-- WebRTC VAD (turn-taking)
       (bidirectional audio)               |
                                           +-- Google Calendar (availability / booking)
                                           |
                                           +-- BosonAI:
                                           |     • higgs-audio-understanding-Hackathon
                                           |     • higgs-audio-generation-Hackathon
                                           |
                                           +-- Call Actions via Twilio REST
                                           |
                                           +-- Save metadata -> SQLiteCloud
                                                  |
                                                  v
                                           React Native (Expo) App
                                           (voicemail inbox & playback)
```

---

## Tech Stack

**Backend**

- Python **FastAPI** (WebSocket server for Media Streams)
- **BosonAI Higgs** (audio understanding & TTS via OpenAI client)
- **WebRTC VAD** for endpointing
- **Twilio Programmable Voice** + REST API
- **SQLiteCloud** for call records
- **Google Calendar API** for availability & booking

**Frontend**

- **React Native (Expo)**
- **Axios** for API calls
- **NativeWind/Tailwind** for styling

**Audio**

- μ-law ↔ PCM conversion (8 kHz Twilio ↔ 16/24 kHz models)
- WAV file generation and sample-rate conversion

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Twilio account & phone number
- BosonAI API key(s)
- SQLiteCloud account
- Google Cloud project (Calendar API)
- **ngrok** (for local dev tunneling)

### Backend Setup

1. **Install dependencies**

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configure environment (`backend/.env`)**

```bash
# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE=+1XXXXXXXXXX
PERSONAL_PHONE=+1XXXXXXXXXX

# BosonAI (supports up to 5 keys for failover)
BOSONAI_API_KEY1=bai-xxxxxxxxxxxxxxxx
BOSONAI_API_KEY2=
BOSONAI_API_KEY3=
BOSONAI_API_KEY4=
BOSONAI_API_KEY5=
BOSONAI_BASE_URL=https://hackathon.boson.ai/v1

# Database
SQLITECLOUD_URL=sqlitecloud://USER:PASSWORD@HOST:8860/higgsceptionist?apikey=XXXX

# Public base URL used by Twilio (ngrok host)
PUBLIC_BASE_URL=your-subdomain.ngrok-free.dev
```

3. **Google Calendar (first-time auth)**

- Enable **Google Calendar API** in Google Cloud.
- Create **OAuth 2.0 Desktop** credentials, download JSON to `backend/google-calendar-credentials.json`.
- Run first-time flow:

```bash
cd backend
python gcal.py
```

4. **Run the server(s)**

```bash
# Terminal 1: main FastAPI app (port 8080)
python main.py

# Terminal 2 (optional if you split DB API): start DB API if applicable
# cd database && python main.py

# Terminal 3: expose FastAPI to the internet for Twilio
ngrok http 8080
```

5. **Configure Twilio webhook**

- Twilio Console → **Phone Numbers** → your number → **Voice & Fax**
- **A CALL COMES IN** → **Webhook** → `https://<PUBLIC_BASE_URL>/twiml` (POST)

### Frontend Setup (Optional Inbox App)

```bash
cd frontend
npm install
# In api.js set baseURL to your machine or DB API, e.g.
# export const api = axios.create({ baseURL: "http://YOUR_LAN_IP:8000" });
npx expo start
```

---

## How It Works

1. Caller dials your Twilio number; Twilio connects a media stream to FastAPI.
2. Server greets the caller and transcribes/understands live audio with Higgs.
3. Calendar check: if you’re in a meeting, the bot offers to book the next slot.
4. Decision:

   - **Legit + available** → `FORWARD_CALL` to your phone.
   - **Legit + busy** → auto-books via Google Calendar.
   - **Spam** → polite **END_CALL**.

5. The call record (number, detected name, AI summary, spam flag, WAV filename) is saved to **SQLiteCloud**.
6. The RN app lists voicemails and can play recordings.

---

## REST Endpoints (Backend)

- `GET /` — health, endpoints, database status
- `POST /twiml` — TwiML for Twilio “A CALL COMES IN” webhook
- `GET /voicemails` — list saved call records
- `GET /voicemail/{id}/recording` — returns WAV bytes

---

## Common Issues

- **Frontend “Network error”**
  Ensure `api.js` points to a reachable base URL (LAN IP or ngrok URL).

- **No bot audio / one-way audio**
  Confirm ngrok is running and Twilio webhook points to `https://<PUBLIC_BASE_URL>/twiml`.

- **DB errors**
  Double-check `SQLITECLOUD_URL` URI and that the schema init ran.

- **Model timeouts**
  Add/rotate more `BOSONAI_API_KEY*` entries (up to 5 supported).

- **Calendar errors**
  Re-run `python gcal.py` to refresh OAuth if `token.json` expired.

---

## Roadmap

- [x] Calendar availability checks
- [x] Auto-scheduling meetings
- [ ] Push notifications for new messages
- [ ] Call-back from the app
- [ ] Contact whitelist/blacklist
- [ ] Multi-language support
- [ ] Full transcript view in app

---

## Authors

**Kevin Peng** — [@pengkev](https://github.com/pengkev)

**Ethan Fong** — [@EthanFong30](https://github.com/EthanFong30)

**Jordan Cui** — [@Jordan-Cui](https://github.com/Jordan-Cui)
_Built for the BosonAI Higgs Hackathon 2025_


