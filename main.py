"""
main.py — JARVIS entry point.

Boots Phase-1 (brain) and optionally Phase-2 (voice) systems.

Usage:
    python main.py                # text-only CLI mode
    python main.py --voice        # full voice mode (wake word + STT + TTS)
    python main.py --voice --cli  # voice + simultaneous CLI input
"""

import argparse
import logging
import os
import sys
from pathlib import Path

# ── Load .env before importing config ─────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env", override=False)
except ImportError:
    pass  # python-dotenv not installed; rely on real environment variables

import config
from core.engine import JarvisEngine

# ── Logging setup ─────────────────────────────────────────────────────────────
config.LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_DIR / "jarvis.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Silence overly verbose third-party loggers.
for _noisy in ("httpx", "httpcore", "urllib3", "requests"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)


# ── CLI helpers ───────────────────────────────────────────────────────────────

def _print_banner() -> None:
    print(config.CLI_BANNER)
    print(f"  Welcome, {config.USER_NAME}. JARVIS is online.")
    print(f"  Model  : {config.OLLAMA_MODEL} (local Ollama)")
    if config.GEMINI_FALLBACK_ENABLED:
        print(f"  Fallback: {config.GEMINI_MODEL} (Gemini)")
    else:
        print("  Fallback: disabled  (set GEMINI_API_KEY in .env to enable)")
    print()
    print("  Commands: 'exit' | 'quit'   — end session")
    print("            'reset'           — clear conversation history")
    print("            'model <name>'    — switch Ollama model on the fly")
    print("  Voice:    'python main.py --voice' to enable voice mode")
    print()


def _print_jarvis(text: str) -> None:
    c = config.CLI_RESPONSE_COLOR
    r = config.CLI_RESET_COLOR
    print(f"\n{c}JARVIS:{r} {text}\n")


def _prompt_user() -> str:
    c = config.CLI_PROMPT_COLOR
    r = config.CLI_RESET_COLOR
    try:
        return input(f"{c}{config.USER_NAME}:{r} ").strip()
    except (EOFError, KeyboardInterrupt):
        return "exit"


# ── CLI chat loop ─────────────────────────────────────────────────────────────

def run_cli(engine: JarvisEngine) -> None:
    _print_banner()

    while True:
        user_input = _prompt_user()

        if not user_input:
            continue

        # Built-in commands
        if user_input.lower() in {"exit", "quit"}:
            print("\nGoodbye, Sir. JARVIS shutting down.\n")
            break

        if user_input.lower() == "reset":
            engine.reset_memory()
            print("  Conversation history cleared.\n")
            continue

        if user_input.lower().startswith("model "):
            new_model = user_input[6:].strip()
            if new_model:
                config.OLLAMA_MODEL = new_model
                engine.reset_memory()
                print(f"  Switched to model: {new_model}\n")
            else:
                print("  Usage: model <model-name>\n")
            continue

        # Normal chat turn
        reply = engine.process(user_input)
        if reply:
            _print_jarvis(reply)


# ── Voice mode ────────────────────────────────────────────────────────────────

def run_voice(engine: JarvisEngine, also_cli: bool = False) -> None:
    """Start the voice conversation loop."""
    from core.voice_loop import VoiceLoop

    loop = VoiceLoop(
        engine=engine,
        wake_word_model=config.WAKE_WORD_MODEL,
        stt_model=config.WHISPER_MODEL,
        stt_language=config.WHISPER_LANGUAGE,
        tts_voice=config.TTS_VOICE,
        tts_speed=config.TTS_SPEED,
        wake_threshold=config.WAKE_WORD_THRESHOLD,
    )

    if also_cli:
        # Run voice on a background thread; keep CLI in the foreground.
        voice_thread = loop.start()
        logger.info("Voice loop running in background. CLI also active.")
        run_cli(engine)
        loop.stop()
        voice_thread.join(timeout=5)
    else:
        _print_banner()
        loop.run()


# ── HUD mode ──────────────────────────────────────────────────────────────────

def run_hud(engine: JarvisEngine) -> None:
    """Launch the desktop HUD overlay."""
    try:
        from ui.hud import run_hud as _run_hud
        logger.info("Starting JARVIS HUD overlay.")
        _run_hud(engine=engine)
    except ImportError:
        print("PyQt6 not installed. Run: pip install PyQt6")


# ── Tray mode ─────────────────────────────────────────────────────────────────

def run_tray(engine: JarvisEngine) -> None:
    """Launch the system tray icon."""
    try:
        from ui.tray import run_tray as _run_tray
        logger.info("Starting JARVIS system tray.")
        _run_tray(engine=engine)
    except ImportError:
        print("PyQt6 not installed. Run: pip install PyQt6")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS AI assistant")
    parser.add_argument("--voice", action="store_true",
                        help="Enable voice mode (wake word + STT + TTS).")
    parser.add_argument("--cli", action="store_true",
                        help="Keep the text CLI active alongside voice mode.")
    parser.add_argument("--hud", action="store_true",
                        help="Launch the desktop HUD overlay (requires PyQt6).")
    parser.add_argument("--tray", action="store_true",
                        help="Launch as a system tray icon (requires PyQt6).")
    args = parser.parse_args()

    engine = JarvisEngine()

    if args.tray:
        logger.info("Starting JARVIS — system tray mode.")
        run_tray(engine)
    elif args.hud:
        logger.info("Starting JARVIS — HUD mode.")
        run_hud(engine)
    elif args.voice:
        logger.info("Starting JARVIS Phase 2 — voice mode.")
        run_voice(engine, also_cli=args.cli)
    else:
        logger.info("Starting JARVIS Phase 1 — brain / CLI mode.")
        run_cli(engine)

    logger.info("JARVIS session ended.")


if __name__ == "__main__":
    main()
