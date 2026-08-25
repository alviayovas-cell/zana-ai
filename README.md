# 🧠 Zana — Personal AI Assistant

Zana is a **web-based personal AI assistant** that combines **text, voice, AI reasoning, music control, memory, and intelligent tool routing** in a single application.

The project is designed with a modular architecture so new AI tools and services can be added without rebuilding the existing system.

## ✨ Features

* 💬 **AI Chat** — Natural-language conversations with Zana
* 🎤 **Voice Assistant** — Speak commands through the browser
* 🧠 **AI Brain** — Intent understanding, context awareness, and tool routing
* ⚡ **Fast Command Router** — Executes simple commands without unnecessary LLM calls
* 🎵 **Music Control** — Search and control music through Spotify
* 🔊 **Text-to-Speech** — Zana can speak responses
* 🧠 **Memory System** — Store useful conversations, preferences, and memories using MongoDB
* 🛠️ **Tool-Based Architecture** — Designed for future tools and integrations

## 🎵 Music Capabilities

Zana is not limited to a single song. It is designed to understand requests such as:

```text
Play Believer
Play songs by Arijit Singh
Play some relaxing music
Pause the music
Resume
Next song
Previous song
Set volume to 50
What's playing?
```

The music system uses the connected music service instead of storing or downloading songs.

## 🧠 AI Architecture

```text
                  ZANA
                    │
          ┌─────────┴─────────┐
          │                   │
        TEXT                 VOICE
          │                   │
          │             Speech-to-Text
          │                   │
          └─────────┬─────────┘
                    ↓
           Fast Command Router
                    │
          ┌─────────┴─────────┐
          │                   │
     Simple Command      Complex Request
          │                   │
          ↓                   ↓
      Direct Tool          AI Brain
                              │
                       ┌──────┴──────┐
                       ↓             ↓
                      LLM          Memory
                       │             │
                       └──────┬──────┘
                              ↓
                         Tool Router
                              │
                   ┌──────────┼──────────┐
                   ↓          ↓          ↓
                Spotify     Memory    Future Tools
                   │
                   ↓
                Response
                   │
                   ↓
             Text-to-Speech
                   │
                   ↓
                  🔊
```

## 🛠️ Tech Stack

### Frontend

* React
* TypeScript
* Vite
* HTML5 / CSS
* Browser Speech APIs

### Backend

* Python
* FastAPI
* Uvicorn
* Pydantic

### AI

* Large Language Model (LLM)
* AI Brain / Tool Routing
* Structured AI commands

### Database

* MongoDB
* MongoDB Atlas
* PyMongo

### Music

* Spotify Web API

### Development

* Antigravity
* Git
* GitHub

## 📂 Project Structure

```text
zana/
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── services/
│       ├── hooks/
│       ├── types/
│       └── utils/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── ai/
│   │   ├── assistant/
│   │   ├── music/
│   │   ├── memory/
│   │   └── core/
│   │
│   └── tests/
│
├── .env.example
├── .gitignore
└── README.md
```

## 🚀 Development Phases

### Phase 1 — Web Foundation

* React + TypeScript + Vite
* FastAPI backend
* Chat interface
* Frontend/backend communication

### Phase 2 — Music

* Spotify integration
* Music search
* Playback controls

### Phase 3 — Voice

* Browser microphone
* Speech-to-text
* Voice commands

### Phase 4 — AI Brain

* LLM integration
* Intent understanding
* Context awareness
* Tool routing
* Task planning

### Phase 5 — Intelligence Enhancement

* Fast Command Router
* MongoDB Memory
* Conversation context
* User preferences
* Text-to-Speech

## 🔐 Security

Sensitive credentials must remain on the backend.

Never commit:

```text
.env
API keys
Spotify client secrets
MongoDB credentials
OAuth tokens
```

Use `.env.example` for required environment variables.

Example:

```env
OPENAI_API_KEY=
MONGODB_URI=
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

## 💻 Local Development

### Prerequisites

* Python 3.11+
* Node.js
* npm
* Git
* MongoDB Atlas account
* Spotify Developer credentials
* LLM API credentials

### Backend

```bash
cd backend

python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure `.env`, then run:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## 📌 Current Status

**Status: Active Development**

Implemented / developing:

* ✅ Web-based Zana interface
* ✅ Chat
* ✅ Spotify integration
* ✅ Music controls
* ✅ Voice Assistant
* ✅ AI Brain
* ✅ LLM integration
* 🔄 Fast Command Router
* 🔄 MongoDB Memory
* 🔄 Text-to-Speech

## 🛣️ Future Plans

* 🌐 Web search
* 📅 Calendar integration
* ⏰ Reminders
* 📝 Notes
* 🐙 GitHub tools
* 📁 File/document search
* 🧠 Advanced memory
* 🔌 Plugin/tool architecture
* 🔊 Improved voice interaction

## 🎯 Project Goal

The goal of Zana is to build a **modular personal AI assistant** that can understand natural language, remember useful context, select the right tools, and interact with external services through a single interface.

> **Voice + AI Brain + Memory + Tools = Zana**

