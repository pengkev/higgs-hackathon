# HiggsReceptionist — AI Call Screener & Message Manager# HiggsReceptionist — AI Call Screener & Message Manager# HiggsReceptionist — AI Call Screener & Message Manager

A voice-first AI receptionist that answers your phone line, **talks** to callers in real-time, screens spam calls, **forwards legitimate calls** to your personal phone, and **saves complete call transcripts** with AI-generated summaries to a cloud database. View all messages in a React Native mobile app.A voice-first AI receptionist that answers your phone line, **talks** to callers in real-time, screens spam calls, **forwards legitimate calls** to your personal phone, and **saves complete call transcripts** with AI-generated summaries to a cloud database. View all messages in a React Native mobile app.A voice-first AI receptionist that answers your phone line, **talks** to callers in real-time, screens spam calls, **forwards legitimate calls** to your personal phone, and **saves complete call transcripts** with AI-generated summaries to a cloud database. View all messages in a React Native mobile app.

Built with **BosonAI Higgs models** for audio understanding and generation, deployed via Twilio Media Streams.Built with **BosonAI Higgs models** for audio understanding and generation, deployed via Twilio Media Streams.Built with **BosonAI Higgs models** for audio understanding and generation, deployed via Twilio Media Streams.

---

## Features## Features## Features

- **Natural voice conversations** - No key presses, just talk- **Natural voice conversations** - No key presses, just talk- **Natural voice conversations** - No key presses, just talk

- **Real-time AI screening** - BosonAI understands caller intent during the call

- **Smart spam detection** - Automatically identifies and categorizes spam calls- **Real-time AI screening** - BosonAI understands caller intent during the call- **Real-time AI screening** - BosonAI understands caller intent during the call

- **Call forwarding** - Legitimate callers get connected to your personal phone

- **Google Calendar integration** - Context-aware routing based on meeting status- **Smart spam detection** - Automatically identifies and categorizes spam calls- **Smart spam detection** - Automatically identifies and categorizes spam calls

- **Auto-scheduling** - Books meetings at next available slot when you're busy

- **Full conversation transcripts** - All calls saved to SQLiteCloud with recordings- **Call forwarding** - Legitimate callers get connected to your personal phone- **Call forwarding** - Legitimate callers get connected to your personal phone

- **AI-generated summaries** - Bot asks callers for messages and summarizes conversations

- **Mobile app** - React Native (Expo) app to view call history and play recordings- **Full conversation transcripts** - All calls saved to SQLiteCloud with recordings- **Full conversation transcripts** - All calls saved to SQLiteCloud with recordings

- **Multi-API key support** - Automatic failover across 5 BosonAI API keys

- **Voice Activity Detection** - Intelligent conversation turn-taking with VAD- **AI-generated summaries** - Bot asks callers for messages and summarizes conversations- **AI-generated summaries** - Bot asks callers for messages and summarizes conversations

---- **Mobile app** - React Native (Expo) app to view call history and play recordings- **Mobile app** - React Native (Expo) app to view call history and play recordings

## Architecture- **Multi-API key support** - Automatic failover across 5 BosonAI API keys- **Multi-API key support** - Automatic failover across 5 BosonAI API keys

````- **Voice Activity Detection** - Intelligent conversation turn-taking with VAD- **Voice Activity Detection** - Intelligent conversation turn-taking with VAD

Caller (PSTN)

  |---

  v

Twilio Phone Number## Architecture## Architecture

  |

  +-- POST /twiml -----------------> FastAPI Server (Port 8080)```

  |                                  |

  +-- WebSocket /media-stream -----> +-- Voice Activity Detection (WebRTC VAD)Caller (PSTN)Caller (PSTN)

      (bidirectional audio)          |

                                     +-- Google Calendar Integration  |  |

                                     |   (Check availability, book meetings)

                                     |  v  v

                                     +-- BosonAI Higgs Audio Understanding

                                     |   (higgs-audio-understanding-Hackathon)Twilio Phone NumberTwilio Phone Number

                                     |

                                     +-- BosonAI Higgs Audio Generation  |  |

                                     |   (higgs-audio-generation-Hackathon)

                                     |  +-- POST /twiml -----------------> FastAPI Server (Port 8080)  +-- POST /twiml -----------------> FastAPI Server (Port 8080)

                                     +-- Call Actions (Forward/End/Book via Twilio API)

                                     |  |                                  |  |                                  |

                                     +-- Save to SQLiteCloud

                                          |  +-- WebSocket /media-stream -----> +-- Voice Activity Detection (WebRTC VAD)  +-- WebSocket /media-stream -----> +-- Voice Activity Detection (WebRTC VAD)

                                          v

                                     Database API Server (Port 8000)      (bidirectional audio)          |      (bidirectional audio)          |

                                          |

                                          v                                     +-- BosonAI Higgs Audio Understanding                                     +-- BosonAI Higgs Audio Understanding

                                     React Native App (Expo)

                                     (Message inbox)                                     |   (higgs-audio-understanding-Hackathon)                                     |   (higgs-audio-understanding-Hackathon)

````

                                     |                                     |

---

                                     +-- BosonAI Higgs Audio Generation                                     +-- BosonAI Higgs Audio Generation

## Tech Stack

                                     |   (higgs-audio-generation-Hackathon)                                     |   (higgs-audio-generation-Hackathon)

### Backend

- **Python FastAPI** - WebSocket server for Twilio Media Streams | |

- **BosonAI Higgs Models** - Audio understanding and generation (via OpenAI client)

- **WebRTC VAD** - Voice Activity Detection for conversation segmentation +-- Call Actions (Forward/End via Twilio API) +-- Call Actions (Forward/End via Twilio API)

- **Twilio Programmable Voice** - Bidirectional Media Streams

- **SQLiteCloud** - Cloud-hosted database for message storage | |

- **Google Calendar API** - Meeting scheduling and availability checks

- **Twilio REST API** - Call forwarding and termination +-- Save to SQLiteCloud +-- Save to SQLiteCloud

### Frontend | |

- **React Native (Expo)** - Cross-platform mobile app

- **Axios** - API communication v v

- **NativeWind/Tailwind** - Styling

                                     Database API Server (Port 8000)                                     Database API Server (Port 8000)

### Audio Processing

- **u-law to PCM conversion** - Twilio (8kHz) to BosonAI (16kHz/24kHz) | |

- **WAV file generation** - Full call recordings saved to disk

- **Sample rate conversion** - Automatic audio format adaptation v v

--- React Native App (Expo) React Native App (Expo)

## Getting Started (Message inbox) (Message inbox)

### Prerequisites```

- Python 3.11+

- Node.js 18+---

- Twilio account with a phone number

- BosonAI API key(s)## Tech Stack## Tech Stack

- SQLiteCloud account

- Google Cloud account (for Calendar API)### Backend### Backend

- ngrok (for local development)

- **Python FastAPI** - WebSocket server for Twilio Media Streams- **Python FastAPI** - WebSocket server for Twilio Media Streams

### Backend Setup

- **BosonAI Higgs Models** - Audio understanding and generation (via OpenAI client)- **BosonAI Higgs Models** - Audio understanding and generation (via OpenAI client)

1. **Install Python dependencies:**

   ```bash- **WebRTC VAD** - Voice Activity Detection for conversation segmentation- **WebRTC VAD** - Voice Activity Detection for conversation segmentation

   cd backend

   python -m venv venv- **Twilio Programmable Voice** - Bidirectional Media Streams- **Twilio Programmable Voice** - Bidirectional Media Streams

   venv\Scripts\activate  # Windows

   pip install -r requirements.txt- **SQLiteCloud** - Cloud-hosted database for message storage- **SQLiteCloud** - Cloud-hosted database for message storage

   ```

- **Twilio REST API** - Call forwarding and termination- **Twilio REST API** - Call forwarding and termination

2. **Configure environment variables in `backend/.env`:**

   ```bash### Frontend### Frontend

   TWILIO_ACCOUNT_SID=ACxxxxxxxxxx

   TWILIO_AUTH_TOKEN=xxxxx- **React Native (Expo)** - Cross-platform mobile app- **React Native (Expo)** - Cross-platform mobile app

   TWILIO_PHONE=+1XXXXXXXXXX

   PERSONAL_PHONE=+1XXXXXXXXXX- **Axios** - API communication- **Axios** - API communication

   BOSONAI_API_KEY1=bai-xxxxx

   BOSONAI_BASE_URL=https://hackathon.boson.ai/v1- **NativeWind/Tailwind** - Styling- **NativeWind/Tailwind** - Styling

   SQLITECLOUD_URL=sqlitecloud://xxxxx

   PUBLIC_BASE_URL=your-ngrok-domain.ngrok-free.dev### Audio Processing### Audio Processing

   ```

- **u-law to PCM conversion** - Twilio (8kHz) to BosonAI (16kHz/24kHz)- **u-law to PCM conversion** - Twilio (8kHz) to BosonAI (16kHz/24kHz)

3. **Set up Google Calendar:**

   - Go to [Google Cloud Console](https://console.cloud.google.com/)- **WAV file generation** - Full call recordings saved to disk- **WAV file generation** - Full call recordings saved to disk

   - Create a new project or select existing

   - Enable Google Calendar API- **Sample rate conversion** - Automatic audio format adaptation- **Sample rate conversion** - Automatic audio format adaptation

   - Create OAuth 2.0 credentials (Desktop app)

   - Download credentials JSON and save as `backend/google-calendar-credentials.json`---

   - Run first-time OAuth flow:

     ```bash## Getting Started## Getting Started

     cd backend

     python gcal.py### Prerequisites### Prerequisites

     ```

   - Follow browser prompts to authorize (creates `token.json`)- Python 3.11+- Python 3.11+

4. **Start servers:**- Node.js 18+- Node.js 18+

   ```bash

   # Terminal 1: Main server (port 8080)- Twilio account with a phone number- Twilio account with a phone number

   python main.py
   ```

- BosonAI API key(s)- BosonAI API key(s)

  # Terminal 2: Database API server (port 8000)

  cd database- SQLiteCloud account- SQLiteCloud account

  python main.py

- ngrok (for local development)- ngrok (for local development)

  # Terminal 3: Expose via ngrok

  ngrok http 8080### Backend Setup### Backend Setup

  ```

  ```

1. **Install Python dependencies:**1. **Install Python dependencies:**

2. **Configure Twilio webhook:**

   - Go to Twilio Console > Phone Numbers > Your Number ````bash \\ash

   - Set **Voice & Fax** > **A CALL COMES IN** > **Webhook**

   - URL: `https://your-ngrok-url.ngrok-free.dev/twiml` (POST) cd backend cd backend

### Frontend Setup python -m venv venv python -m venv venv

1. **Install and configure:** venv\Scripts\activate # Windows venv\Scripts\activate # Windows

   `````bash

   cd frontend   pip install -r requirements.txt   pip install -r requirements.txt

   npm install

   # Edit api.js - set baseURL to your computer's IP: http://YOUR_IP:8000   ```   \\\

   npx expo start

   ```   ````
   `````

---2. **Configure environment variables in `backend/.env`:**2. **Configure environment variables in \ackend/.env\:**

## How It Works ````bash \\ash

### Call Flow with Calendar Integration TWILIO_ACCOUNT_SID=ACxxxxxxxxxx TWILIO_ACCOUNT_SID=ACxxxxxxxxxx

1. **Caller dials your Twilio number** TWILIO_AUTH_TOKEN=xxxxx TWILIO_AUTH_TOKEN=xxxxx

2. **AI receptionist answers** and has a natural conversation

3. **Calendar check** - Bot checks Google Calendar for current meeting status TWILIO_PHONE=+1XXXXXXXXXX TWILIO_PHONE=+1XXXXXXXXXX

4. **Smart decision making:**

   - **Legitimate caller + Available** → Forwards to your personal phone PERSONAL_PHONE=+1XXXXXXXXXX PERSONAL_PHONE=+1XXXXXXXXXX

   - **Legitimate caller + In meeting** → Offers to book at next available slot

   - **Spam detected** → Politely ends call BOSONAI_API_KEY1=bai-xxxxx BOSONAI_API_KEY1=bai-xxxxx

5. **Auto-booking** (if applicable):

   - Extracts caller name from conversation BOSONAI_BASE_URL=https://hackathon.boson.ai/v1 BOSONAI_BASE_URL=https://hackathon.boson.ai/v1

   - Finds next available 15-minute slot during business hours (9 AM - 5 PM)

   - Creates Google Calendar event SQLITECLOUD_URL=sqlitecloud://xxxxx SQLITECLOUD_URL=sqlitecloud://xxxxx

   - Confirms booking details to caller

6. **Call saved to database** with: PUBLIC_BASE_URL=your-ngrok-domain.ngrok-free.dev PUBLIC_BASE_URL=your-ngrok-domain.ngrok-free.dev

   - Caller info (number, extracted name)

   - AI-generated summary from full conversation transcript ``` \\\

   - Spam classification

   - Complete WAV recording ````

7. **View in mobile app** - All calls with summaries available in React Native inbox

8. **Start servers:**3. **Start servers:**

### Calendar Functions

`````bash \ash

The system uses three Google Calendar functions (`backend/gcal.py`):

# Terminal 1: Main server (port 8080)

- **`get_current_event()`** - Returns current meeting details or empty if available

- **`get_next_available_slot()`** - Finds next open time slot during business hours   python main.py   # Terminal 1: Main server (port 8080)

- **`book_next_available(caller_name, caller_phone, caller_email)`** - Automatically schedules a 15-min meeting



### AI Receptionist Behavior

# Terminal 2: Database API server (port 8000)   python main.py

**When you're available:**

- "Thanks for calling! Let me connect you with Kevin right now."   cd database

- Uses `FORWARD_CALL` command

python main.py   # Terminal 2: Database API server (port 8000)

**When you're in a meeting:**

- "Kevin is currently in [Meeting Name] until [Time]. I can schedule you for the next available slot. Would that work?"

- Uses `BOOK_MEETING` command

- Creates calendar event automatically   # Terminal 3: Expose via ngrok   cd database



---   ngrok http 8080   python main.py



## Common Issues   ```



- **"Network error" in frontend:** Check that `api.js` has your computer's IP address (run `ipconfig`)   # Terminal 3: Expose via ngrok

- **No audio from bot:** Check ngrok tunnel is running and Twilio webhook is configured

- **Database errors:** Verify `SQLITECLOUD_URL` is correct4. **Configure Twilio webhook:**

- **API key timeouts:** Add more `BOSONAI_API_KEY` entries (supports 1-5)

- **Calendar errors:** Run `python gcal.py` to re-authenticate if `token.json` expires   - Go to Twilio Console > Phone Numbers > Your Number ngrok http 8080



---   - Set **Voice & Fax** > **A CALL COMES IN** > **Webhook** \\\



## Roadmap   - URL: `https://your-ngrok-url.ngrok-free.dev/twiml` (POST)



- [x] Google Calendar integration (availability checks)5. **Configure Twilio webhook:**

- [x] Auto-scheduling meetings

- [ ] Push notifications for new messages### Frontend Setup - Go to Twilio Console Phone Numbers Your Number

- [ ] Callback functionality from app

- [ ] Contact whitelist/blacklist- Set **Voice & Fax** **A CALL COMES IN** **Webhook**

- [ ] Multi-language support

- [ ] Full transcript display in app alongside summaries1. **Install and configure:** - URL: \https://your-ngrok-url.ngrok-free.dev/twiml\ (POST)



---   ````bash



## Author   cd frontend### Frontend Setup



**Kevin Peng** - [GitHub](https://github.com/pengkev)   npm install



*Built for the BosonAI Higgs Hackathon 2025*   # Edit api.js - set baseURL to your computer's IP: http://YOUR_IP:80001. **Install and configure:**


npx expo start   \\\ash

```   cd frontend

npm install
`````

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
