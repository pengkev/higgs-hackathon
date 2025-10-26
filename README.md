# HiggsReceptionist — AI Call Screener & Message Manager# HiggsReceptionist — AI Call Screener & Message Manager

A voice-first AI receptionist that answers your phone line, **talks** to callers in real-time, screens spam calls, **forwards legitimate calls** to your personal phone, and **saves complete call transcripts** with AI-generated summaries to a cloud database. View all messages in a React Native mobile app.A voice-first AI receptionist that answers your phone line, **talks** to callers in real-time, screens spam calls, **forwards legitimate calls** to your personal phone, and **saves complete call transcripts** with AI-generated summaries to a cloud database. View all messages in a React Native mobile app.

Built with **BosonAI Higgs models** for audio understanding and generation, deployed via Twilio Media Streams.Built with **BosonAI Higgs models** for audio understanding and generation, deployed via Twilio Media Streams.

---

## Features## Features

- **Natural voice conversations** - No key presses, just talk- **Natural voice conversations** - No key presses, just talk

- **Real-time AI screening** - BosonAI understands caller intent during the call- **Real-time AI screening** - BosonAI understands caller intent during the call

- **Smart spam detection** - Automatically identifies and categorizes spam calls- **Smart spam detection** - Automatically identifies and categorizes spam calls

- **Call forwarding** - Legitimate callers get connected to your personal phone- **Call forwarding** - Legitimate callers get connected to your personal phone

- **Full conversation transcripts** - All calls saved to SQLiteCloud with recordings- **Full conversation transcripts** - All calls saved to SQLiteCloud with recordings

- **AI-generated summaries** - Bot asks callers for messages and summarizes conversations- **AI-generated summaries** - Bot asks callers for messages and summarizes conversations

- **Mobile app** - React Native (Expo) app to view call history and play recordings- **Mobile app** - React Native (Expo) app to view call history and play recordings

- **Multi-API key support** - Automatic failover across 5 BosonAI API keys- **Multi-API key support** - Automatic failover across 5 BosonAI API keys

- **Voice Activity Detection** - Intelligent conversation turn-taking with VAD- **Voice Activity Detection** - Intelligent conversation turn-taking with VAD

---

## Architecture## Architecture

```

Caller (PSTN)Caller (PSTN)

  |  |

  v  v

Twilio Phone NumberTwilio Phone Number

  |  |

  +-- POST /twiml -----------------> FastAPI Server (Port 8080)  +-- POST /twiml -----------------> FastAPI Server (Port 8080)

  |                                  |  |                                  |

  +-- WebSocket /media-stream -----> +-- Voice Activity Detection (WebRTC VAD)  +-- WebSocket /media-stream -----> +-- Voice Activity Detection (WebRTC VAD)

      (bidirectional audio)          |      (bidirectional audio)          |

                                     +-- BosonAI Higgs Audio Understanding                                     +-- BosonAI Higgs Audio Understanding

                                     |   (higgs-audio-understanding-Hackathon)                                     |   (higgs-audio-understanding-Hackathon)

                                     |                                     |

                                     +-- BosonAI Higgs Audio Generation                                     +-- BosonAI Higgs Audio Generation

                                     |   (higgs-audio-generation-Hackathon)                                     |   (higgs-audio-generation-Hackathon)

                                     |                                     |

                                     +-- Call Actions (Forward/End via Twilio API)                                     +-- Call Actions (Forward/End via Twilio API)

                                     |                                     |

                                     +-- Save to SQLiteCloud                                     +-- Save to SQLiteCloud

                                          |                                          |

                                          v                                          v

                                     Database API Server (Port 8000)                                     Database API Server (Port 8000)

                                          |                                          |

                                          v                                          v

                                     React Native App (Expo)                                     React Native App (Expo)

                                     (Message inbox)                                     (Message inbox)

```

---

## Tech Stack## Tech Stack

### Backend### Backend

- **Python FastAPI** - WebSocket server for Twilio Media Streams- **Python FastAPI** - WebSocket server for Twilio Media Streams

- **BosonAI Higgs Models** - Audio understanding and generation (via OpenAI client)- **BosonAI Higgs Models** - Audio understanding and generation (via OpenAI client)

- **WebRTC VAD** - Voice Activity Detection for conversation segmentation- **WebRTC VAD** - Voice Activity Detection for conversation segmentation

- **Twilio Programmable Voice** - Bidirectional Media Streams- **Twilio Programmable Voice** - Bidirectional Media Streams

- **SQLiteCloud** - Cloud-hosted database for message storage- **SQLiteCloud** - Cloud-hosted database for message storage

- **Twilio REST API** - Call forwarding and termination- **Twilio REST API** - Call forwarding and termination

### Frontend### Frontend

- **React Native (Expo)** - Cross-platform mobile app- **React Native (Expo)** - Cross-platform mobile app

- **Axios** - API communication- **Axios** - API communication

- **NativeWind/Tailwind** - Styling- **NativeWind/Tailwind** - Styling

### Audio Processing### Audio Processing

- **u-law to PCM conversion** - Twilio (8kHz) to BosonAI (16kHz/24kHz)- **u-law to PCM conversion** - Twilio (8kHz) to BosonAI (16kHz/24kHz)

- **WAV file generation** - Full call recordings saved to disk- **WAV file generation** - Full call recordings saved to disk

- **Sample rate conversion** - Automatic audio format adaptation- **Sample rate conversion** - Automatic audio format adaptation

---

## Getting Started## Getting Started

### Prerequisites### Prerequisites

- Python 3.11+- Python 3.11+

- Node.js 18+- Node.js 18+

- Twilio account with a phone number- Twilio account with a phone number

- BosonAI API key(s)- BosonAI API key(s)

- SQLiteCloud account- SQLiteCloud account

- ngrok (for local development)- ngrok (for local development)

### Backend Setup### Backend Setup

1. **Install Python dependencies:**1. **Install Python dependencies:**

   ````bash \\ash

   cd backend   cd backend

   python -m venv venv   python -m venv venv

   venv\Scripts\activate  # Windows   venv\Scripts\activate # Windows

   pip install -r requirements.txt   pip install -r requirements.txt

   ```   \\\

   ````

2. **Configure environment variables in `backend/.env`:**2. **Configure environment variables in \ackend/.env\:**

   ````bash \\ash

   TWILIO_ACCOUNT_SID=ACxxxxxxxxxx   TWILIO_ACCOUNT_SID=ACxxxxxxxxxx

   TWILIO_AUTH_TOKEN=xxxxx   TWILIO_AUTH_TOKEN=xxxxx

   TWILIO_PHONE=+1XXXXXXXXXX   TWILIO_PHONE=+1XXXXXXXXXX

   PERSONAL_PHONE=+1XXXXXXXXXX   PERSONAL_PHONE=+1XXXXXXXXXX

   BOSONAI_API_KEY1=bai-xxxxx   BOSONAI_API_KEY1=bai-xxxxx

   BOSONAI_BASE_URL=https://hackathon.boson.ai/v1   BOSONAI_BASE_URL=https://hackathon.boson.ai/v1

   SQLITECLOUD_URL=sqlitecloud://xxxxx   SQLITECLOUD_URL=sqlitecloud://xxxxx

   PUBLIC_BASE_URL=your-ngrok-domain.ngrok-free.dev   PUBLIC_BASE_URL=your-ngrok-domain.ngrok-free.dev

   ```   \\\

   ````

3. **Start servers:**3. **Start servers:**

   ```bash \\ash

   # Terminal 1: Main server (port 8080)

   python main.py   # Terminal 1: Main server (port 8080)



   # Terminal 2: Database API server (port 8000)   python main.py

   cd database

   python main.py   # Terminal 2: Database API server (port 8000)



   # Terminal 3: Expose via ngrok   cd database

   ngrok http 8080   python main.py

   ```

   # Terminal 3: Expose via ngrok

4. **Configure Twilio webhook:**

   - Go to Twilio Console > Phone Numbers > Your Number ngrok http 8080

   - Set **Voice & Fax** > **A CALL COMES IN** > **Webhook** \\\

   - URL: `https://your-ngrok-url.ngrok-free.dev/twiml` (POST)

5. **Configure Twilio webhook:**

### Frontend Setup - Go to Twilio Console Phone Numbers Your Number

- Set **Voice & Fax** **A CALL COMES IN** **Webhook**

1. **Install and configure:** - URL: \https://your-ngrok-url.ngrok-free.dev/twiml\ (POST)

   ````bash

   cd frontend### Frontend Setup

   npm install

   # Edit api.js - set baseURL to your computer's IP: http://YOUR_IP:80001. **Install and configure:**

   npx expo start   \\\ash

   ```   cd frontend

   npm install
   ````

--- # Edit api.js - set baseURL to your computer's IP: http://YOUR_IP:8000

npx expo start

## How It Works \\\

1. **Caller dials your Twilio number**---

2. **AI receptionist answers** and has a natural conversation

3. **Bot asks for messages** - "Is there anything you'd like me to pass along to Kevin?"## How It Works

4. **Smart decision making:**

   - **Legitimate caller** > Forwards to your personal phone1. **Caller dials your Twilio number**

   - **Spam detected** > Politely ends call2. **AI receptionist answers** and has a natural conversation

5. **Call saved to database** with:3. **Smart decision making:**

   - Caller info (number, extracted name) - **Legitimate caller** Forwards to your personal phone

   - AI-generated summary from full conversation transcript - **Spam detected** Politely ends call

   - Spam classification4. **Call saved to database** with:

   - Complete WAV recording - Caller info (number, extracted name)

6. **View in mobile app** - All calls with summaries available in React Native inbox - AI-generated description/summary

   - Spam classification

--- - Full WAV recording

5. **View in mobile app** - All calls available in React Native inbox

## Common Issues

---

- **"Network error" in frontend:** Check that `api.js` has your computer's IP address

- **No audio from bot:** Check ngrok tunnel is running and Twilio webhook is configured## Common Issues

- **Database errors:** Verify `SQLITECLOUD_URL` is correct

- **API key timeouts:** Add more `BOSONAI_API_KEY` entries (supports 1-5)- **"Network error" in frontend:** Check that \pi.js\ has your computer's IP address

- **No audio from bot:** Check ngrok tunnel is running and Twilio webhook is configured

---- **Database errors:** Verify \SQLITECLOUD_URL\ is correct

- **API key timeouts:** Add more \BOSONAI_API_KEY\ entries (supports 1-5)

## Roadmap

---

- [ ] Push notifications for new messages

- [ ] Callback functionality from app## Roadmap

- [ ] Calendar integration (don't disturb during meetings)

- [ ] Contact whitelist/blacklist- [ ] Push notifications for new voicemails

- [ ] Multi-language support- [ ] Callback functionality from app

- [ ] Full transcript display in app alongside summaries- [ ] Calendar integration (don't disturb during meetings)

- [ ] Contact whitelist/blacklist

---- [ ] Multi-language support

- [ ] Voicemail transcription display in app

## Author

---

**Kevin Peng** - [GitHub](https://github.com/pengkev)

## Author

_Built for the BosonAI Higgs Hackathon 2025_

**Kevin Peng** - [GitHub](https://github.com/pengkev)

_Built for the BosonAI Higgs Hackathon 2025_
