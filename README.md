# Voice AI Doctor Appointment Assistant

A browser-based voice agent that checks doctor availability, books and cancels appointments. The caller is identified only by the phone number they speak. A dashboard shows the live transcript, doctors, free slots and appointments.

## Stack
- Voice pipeline: Pipecat 1.17, SmallWebRTC, Silero VAD
- STT and TTS: ElevenLabs
- LLM: `openai/gpt-oss-120b` on Groq (free tier), through Pipecat's OpenAI-compatible service. Any OpenAI-compatible provider works by changing `LLM_BASE_URL` and `LLM_MODEL`.
- Data: SQLite, read through a small FastAPI service
- Frontend: React + Vite

## Pipeline
Browser mic -> WebRTC -> Silero VAD -> ElevenLabs STT -> LLM with tool calls -> ElevenLabs TTS -> browser speaker.
Tools (`backend/tools.py`): `check_doctor_availability`, `book_appointment`, `cancel_appointment`.

## Run
Requires Python 3.11+ and Node 18+. You need an ElevenLabs API key and a Groq API key (both have free tiers).

```
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

Fill in `backend/.env`:

```
ELEVENLABS_API_KEY=<your key>
ELEVENLABS_VOICE_ID=hpp4J3VqNfWAUOO0d1Us
LLM_API_KEY=<your Groq key>
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

Open three terminals (activate `.venv` in the first two):

```
cd backend && python bot.py                  # voice bot, port 7860
cd backend && uvicorn api:app --port 8000    # data API, port 8000
cd frontend && npm install && npm run dev    # dashboard, port 5173
```

Open http://localhost:5173 and click Try Call. Use headphones to avoid echo.

## Features
Required: voice pipeline with three tools, spoken-number identification with read-back, dashboard with live transcript, doctors, slots and appointments.
Bonus: Silero VAD, phone-style call screen (ringing, connected, ended, timer, mute, end), waveform, booking confirmation card, highlighted rows, ring and end sounds, mobile layout.

Code: `backend/bot.py` (pipeline and prompt), `backend/tools.py` (tools), `backend/db.py` (schema and seed data), `backend/api.py` (dashboard data), `frontend/src` (dashboard and call screen).

## Notes and limits
- One active appointment per phone number.
- Identification is by spoken number only, as the assignment specifies, so anyone who knows a number could cancel that person's appointment. A real system would add OTP verification.
- Slots are seeded for the three days after the database is first created. Delete `backend/clinic.db` to reseed.
- English only. Free-tier LLM and ElevenLabs limits apply.
- Gemini was tried first and dropped after repeated 404 and 503 errors.
