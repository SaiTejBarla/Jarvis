"""
config.py — Central configuration for JARVIS.

All tuneable settings live here. Values can be overridden via environment
variables or the .env file (loaded automatically by python-dotenv in main.py).
"""

import os
from pathlib import Path

# ─── Project root ────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).parent

# ─── Identity ─────────────────────────────────────────────────────────────────
JARVIS_NAME = "JARVIS"
USER_NAME = os.getenv("USER_NAME", "Sir")

# ─── Local LLM (Ollama) ───────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# phi3 is the default — optimised for 8 GB RAM machines.
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
# How long (seconds) to wait for a response before giving up.
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

# ─── Gemini Fallback ──────────────────────────────────────────────────────────
# Set GEMINI_API_KEY in your .env file to enable the cloud fallback.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# JARVIS switches to Gemini when a local response is unavailable OR when the
# user explicitly asks for "more power".
GEMINI_FALLBACK_ENABLED = bool(GEMINI_API_KEY)

# ─── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    f"You are {JARVIS_NAME}, a highly intelligent personal AI assistant inspired by "
    "Iron Man's J.A.R.V.I.S. You are precise, helpful, and slightly formal but not robotic. "
    f"Address the user as '{USER_NAME}'. "
    "When you are unsure about something, say so clearly. "
    "Always reply in 1-2 short sentences. Never use bullet points, lists, or markdown. "
    "Be direct and to the point."
)

# ─── Memory ───────────────────────────────────────────────────────────────────
DATA_DIR = ROOT_DIR / "data"
MEMORY_DB_PATH = DATA_DIR / "memory.db"
CHROMA_DIR = DATA_DIR / "chroma"

# ─── Logging ──────────────────────────────────────────────────────────────────
LOG_DIR = DATA_DIR / "logs"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# ─── Conversation ─────────────────────────────────────────────────────────────
# How many previous turns to keep in the rolling context window (CLI).
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "20"))
# Shorter window for voice mode — keeps Ollama fast on long sessions.
VOICE_MAX_HISTORY_TURNS = int(os.getenv("VOICE_MAX_HISTORY_TURNS", "5"))

# ─── Phase 2: Voice ───────────────────────────────────────────────────────────
# Wake word model name (openWakeWord built-in).
WAKE_WORD_MODEL = os.getenv("WAKE_WORD_MODEL", "hey_jarvis")
# Confidence threshold (0–1) for wake-word detection.
WAKE_WORD_THRESHOLD = float(os.getenv("WAKE_WORD_THRESHOLD", "0.5"))

# Whisper model size: tiny | base | small | medium | large
# "tiny" is fastest (~2-3s) and accurate enough for short voice commands.
# Set WHISPER_MODEL=base in .env for better accuracy if needed.
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
# ISO 639-1 language code passed to Whisper.
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")

# kokoro-onnx voice name. Options: af_heart | af_bella | bf_emma | am_adam | bm_george
TTS_VOICE = os.getenv("TTS_VOICE", "af_heart")
# Speech speed multiplier (1.0 = normal).
TTS_SPEED = float(os.getenv("TTS_SPEED", "1.0"))

# ─── CLI ──────────────────────────────────────────────────────────────────────
CLI_PROMPT_COLOR = "\033[96m"   # Cyan for user input prompt
CLI_RESPONSE_COLOR = "\033[92m" # Green for JARVIS replies
CLI_RESET_COLOR = "\033[0m"
CLI_BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""
