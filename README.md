<div align="center">

# ⚡ J.A.R.V.I.S
### Just A Rather Very Intelligent System

**A real, offline, desktop-grade AI assistant — inspired by Iron Man**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black?style=flat&logo=ollama&logoColor=white)](https://ollama.com)
[![Whisper](https://img.shields.io/badge/Whisper-STT-00A67E?style=flat&logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In_Development-orange?style=flat)]()

</div>

---

```
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝

       "In the right hands, the right tools do wonders."
```

---

## 🧠 The Vision

JARVIS is not a chatbot. It is a **fully offline, voice-driven, desktop AI operating system** — the kind Tony Stark uses — built entirely with free and open-source tools.

It lives on your machine, listens for your voice, remembers everything about you, takes real actions on your behalf, and asks for your permission before doing anything critical. It runs on **any device** on your local network — PC, phone, tablet — all connecting to the same brain on your machine.

> No subscriptions. No cloud. No data leaving your machine. Just you and your AI.

---

## ✨ What JARVIS Can Do

| Capability | Description |
|---|---|
| 🎤 **Always Listening** | Wake word "Hey Jarvis" activates it from anywhere |
| 🗣️ **Talks Back** | Responds in a natural voice using local TTS |
| 🧠 **Remembers You** | Long-term memory — knows your preferences, history, habits |
| 🌐 **Browses the Web** | Searches the internet and summarizes results for you |
| 💻 **Writes & Runs Code** | Generates and executes code on your command |
| 📁 **Manages Files** | Create, read, move, organize files and folders |
| 🖥️ **Controls Your PC** | Opens apps, types text, takes screenshots, clicks buttons |
| 📧 **Email & Calendar** | Reads, drafts, and manages your schedule |
| 🏠 **Smart Home** | Controls lights, temperature, and connected devices |
| 🔐 **Auth Gate** | Asks your permission before any critical or destructive action |
| 🚨 **Proactive Alerts** | Warns you about things before you ask |
| 📱 **Any Device** | Access from phone or tablet over your local network |

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                               │
│   🎤 Microphone (Wake Word → Whisper STT)  /  ⌨️ Text Input      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     JARVIS CORE ENGINE                           │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  ORCHESTRATOR                           │   │
│   │  • Understands intent (local LLM via Ollama)            │   │
│   │  • Pulls context from Memory                            │   │
│   │  • Checks: is this a critical action? → Auth Gate       │   │
│   │  • Routes to the right skill/agent                      │   │
│   └──────┬──────────┬──────────┬──────────┬─────────────────┘   │
│          │          │          │          │                      │
│          ▼          ▼          ▼          ▼                      │
│   ┌──────────┐ ┌────────┐ ┌────────┐ ┌────────┐                 │
│   │ Research │ │ Planner│ │ System │ │  Code  │                 │
│   │  Agent   │ │ Agent  │ │ Agent  │ │ Agent  │                 │
│   │          │ │        │ │        │ │        │                 │
│   │ Web      │ │ Tasks  │ │ Files  │ │ Write  │                 │
│   │ Search   │ │ Notes  │ │ Apps   │ │ Run    │                 │
│   │ Summary  │ │ Remind │ │ PC ctrl│ │ Debug  │                 │
│   └──────────┘ └────────┘ └────────┘ └────────┘                 │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                  MEMORY SYSTEM                          │   │
│   │  ChromaDB (vector search)  +  SQLite (structured facts) │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │               MONITOR AGENT (background)                │   │
│   │  • Watches system state, calendar, alerts               │   │
│   │  • Interrupts Jarvis proactively when needed            │   │
│   └─────────────────────────────────────────────────────────┘   │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                       AUTH GATE                                  │
│   🔐 PIN / Voice Passphrase required for critical actions        │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                      OUTPUT LAYER                                │
│   🗣️ Voice (Coqui TTS)  +  🖥️ Desktop HUD  +  📱 Web UI (PWA)   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 Planned Project Structure

```
jarvis/
│
├── main.py                        # Entry point — boots all systems
├── config.py                      # All settings in one place
├── .env                           # API keys (never committed)
│
├── core/
│   ├── engine.py                  # Main JARVIS brain loop
│   ├── orchestrator.py            # Intent routing logic
│   └── auth.py                    # PIN + voice passphrase auth gate
│
├── voice/
│   ├── wake_word.py               # "Hey Jarvis" detection (openWakeWord)
│   ├── speech_to_text.py          # Whisper local STT
│   └── text_to_speech.py          # Coqui TTS local voice output
│
├── agents/
│   ├── research_agent.py          # Web search, summarization
│   ├── planning_agent.py          # Tasks, reminders, calendar
│   ├── system_agent.py            # File ops, PC control, app launcher
│   ├── code_agent.py              # Write, run, and debug code
│   └── monitor_agent.py           # Background proactive watchdog
│
├── memory/
│   ├── vector_memory.py           # ChromaDB semantic/vector memory
│   ├── structured_memory.py       # SQLite key-value facts about user
│   └── memory_manager.py          # Unified interface to both stores
│
├── tools/
│   ├── web_search.py              # DuckDuckGo / SearXNG search
│   ├── browser.py                 # Playwright browser automation
│   ├── file_ops.py                # File and folder operations
│   ├── pc_control.py              # pyautogui — mouse, keyboard, apps
│   ├── code_runner.py             # Sandboxed Python execution
│   └── home_automation.py         # Home Assistant API integration
│
├── ui/
│   ├── hud.py                     # Desktop HUD overlay (PyQt6)
│   ├── tray.py                    # System tray icon + quick access
│   └── web_app.py                 # Streamlit web UI for any device
│
└── data/
    ├── memory.db                  # SQLite structured memory
    ├── chroma/                    # ChromaDB vector store
    └── logs/                      # Action and conversation logs
```

---

## 🛠️ Tech Stack — 100% Free & Open Source

### Core Brain
| Component | Tool | Why |
|---|---|---|
| **Local LLM** | [Ollama](https://ollama.com) + LLaMA 3.1 / Mistral / Phi-3 | Runs 100% offline, no API cost |
| **LLM Fallback** | Google Gemini 2.5 Flash (free tier) | For tasks needing more power |
| **Agent Framework** | Custom Python (async) | Full control, no black boxes |

### Voice
| Component | Tool | Why |
|---|---|---|
| **Wake Word** | [openWakeWord](https://github.com/dscripka/openWakeWord) | Free, trainable, accurate |
| **Speech-to-Text** | [OpenAI Whisper](https://github.com/openai/whisper) (local) | Best-in-class, runs offline |
| **Text-to-Speech** | [Coqui TTS](https://github.com/coqui-ai/TTS) | Natural voice, local, free |

### Memory
| Component | Tool | Why |
|---|---|---|
| **Vector Memory** | [ChromaDB](https://www.trychroma.com) | Semantic search over conversations |
| **Structured Memory** | SQLite (built-in Python) | Fast key-value facts |

### Actions & Tools
| Component | Tool | Why |
|---|---|---|
| **Web Search** | DuckDuckGo API / SearXNG | Free, no API key needed |
| **Browser Automation** | [Playwright](https://playwright.dev/python) | Full browser control |
| **PC Control** | [pyautogui](https://pyautogui.readthedocs.io) | Mouse, keyboard, screenshots |
| **Code Execution** | Sandboxed subprocess | Safe local code runner |

### UI & Access
| Component | Tool | Why |
|---|---|---|
| **Desktop HUD** | [PyQt6](https://doc.qt.io/qtforpython) | Always-on-top overlay like Iron Man |
| **Web UI** | [Streamlit](https://streamlit.io) | Any device on local network |
| **Mobile Access** | PWA via Streamlit | Phone/tablet access, no app install |
| **System Tray** | PyQt6 QSystemTrayIcon | Lives in taskbar, always ready |

---

## 🔐 The Auth Gate — User Authorization for Critical Tasks

JARVIS **never acts silently on critical tasks**. Any destructive, sensitive, or irreversible action is blocked until you authorize it.

```
┌─────────────────────────────────────────────────────┐
│              CRITICAL ACTION DETECTED               │
│                                                     │
│  Action   : Delete project files                   │
│  Risk      : Irreversible                          │
│                                                     │
│  Authorize with:                                   │
│   [1] PIN code                                     │
│   [2] Voice passphrase — "Jarvis, confirmed"       │
└─────────────────────────────────────────────────────┘
```

**Actions that always require authorization:**

| Action | Risk Level |
|---|---|
| Delete files or folders | 🔴 Critical |
| Send emails | 🔴 Critical |
| Execute system commands | 🔴 Critical |
| Access passwords / secrets | 🔴 Critical |
| Make purchases | 🔴 Critical |
| Modify system settings | 🟡 High |
| Shutdown / restart PC | 🔴 Critical |

---

## 🚀 Getting Started (When Built)

### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed and running
- A microphone (for voice mode)
- 8GB+ RAM recommended (16GB for larger models)

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/jarvis.git
cd jarvis
```

### 2. Set up Python environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Pull your local LLM
```bash
ollama pull phi3            # Recommended — lightest, works on 8 GB RAM
ollama pull mistral         # Good middle ground (~4 GB)
ollama pull llama3.1        # Best overall, needs 16 GB RAM
```

### 4. Configure JARVIS
```bash
cp .env.example .env
# Edit .env with your preferences
```

### 5. Launch JARVIS
```bash
python main.py
```

> Say **"Hey Jarvis"** and start talking.

---

## 💬 How It Works — Example Interactions

```
You  : "Hey Jarvis, what's the weather in New York today?"
JARVIS: "Currently 72°F and partly cloudy in New York.
         High of 78 expected this afternoon."

You  : "Jarvis, summarize the last email from John"
JARVIS: "John's email from Tuesday is about the Q3 budget review.
         He's asking for your input by Friday."

You  : "Jarvis, delete all files in my Downloads folder"
JARVIS: "⚠️ That's a critical action. I'll need your authorization.
         Please say your passphrase or enter your PIN."
You  : "Jarvis, confirmed"
JARVIS: "Authorized. Deleting Downloads folder contents now."

You  : "Jarvis, write a Python script to rename all my photos"
JARVIS: "Here's the script. Want me to run it now?"
```

---

## 🗺️ Build Roadmap

### Phase 1 — The Brain ✅
- [x] Project structure and config system
- [x] Ollama integration (local LLM)
- [x] Basic text chat via CLI
- [x] Gemini fallback for complex tasks

### Phase 2 — The Voice ✅
- [x] Wake word detection ("Hey Jarvis")
- [x] Speech-to-text (Whisper local)
- [x] Text-to-speech (Coqui TTS)
- [x] Full voice conversation loop

### Phase 3 — The Memory ✅
- [x] SQLite structured memory (user facts)
- [x] ChromaDB vector memory (conversations)
- [x] Context injection into every prompt
- [x] Memory search ("What did I say about X?")

### Phase 4 — The Actions ✅
- [x] Web search + summarization
- [x] File operations
- [x] PC control (open apps, type, click)
- [x] Code writing and sandboxed execution
- [x] Browser automation (Playwright)

### Phase 5 — The Security ✅
- [x] PIN auth gate
- [x] Voice passphrase authorization
- [x] Critical action detection and blocking
- [x] Full action audit log

### Phase 6 — The Face ✅
- [x] Desktop HUD overlay (PyQt6)
- [x] System tray integration
- [x] Streamlit web UI
- [ ] Mobile PWA (any device on local network)

### Phase 7 — The Intelligence ✅
- [x] Proactive monitor agent
- [x] Smart home integration (Home Assistant)
- [x] Plugin / skill system
- [x] Self-improvement via feedback loop

---

## 🖥️ System Requirements

| Spec | Minimum | Recommended |
|---|---|---|
| **OS** | Windows 10 / macOS 12 / Ubuntu 20.04 | Windows 11 / Ubuntu 22.04 |
| **RAM** | 8 GB | 16 GB+ |
| **Storage** | 10 GB free | 20 GB free |
| **CPU** | 4-core | 8-core+ |
| **GPU** | Not required | NVIDIA GPU (faster LLM inference) |
| **Microphone** | Any USB/built-in | Dedicated mic for better wake word |

---

## 🤝 Contributing

This project is open to contributions. If you want to build a skill, fix a bug, or improve the architecture:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/skill-name`
3. Commit your changes: `git commit -m "Add: skill description"`
4. Push and open a Pull Request

---

## 📄 License

MIT License — free to use, modify, and build upon.

---

<div align="center">

**Built from scratch · Runs offline · Inspired by Tony Stark**

*"Sometimes you gotta run before you can walk."*

⚡ **JARVIS** — The AI that works for you, not the cloud.

</div>
