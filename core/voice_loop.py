"""
core/voice_loop.py — The JARVIS voice conversation loop.

State machine:
    IDLE ──(wake word)──► LISTENING ──(transcribed)──► THINKING
     ▲                                                      │
     └──────────────────────(spoke reply)──── SPEAKING ◄───┘

The loop runs until the user says a stop phrase ("stop", "goodbye", etc.)
or JARVIS is interrupted via :meth:`VoiceLoop.stop`.

Requires Phase-2 voice dependencies (see requirements.txt).
"""

import logging
import re
import threading
import time

from core.engine import JarvisEngine
from voice.wake_word import WakeWordDetector
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
import config

logger = logging.getLogger(__name__)

# Phrases that end the voice session (case-insensitive, substring match).
_STOP_PHRASES = {
    "stop", "goodbye", "shut down", "that's all",
    "exit", "quit", "power off", "go to sleep",
    "bye", "see you", "stand by", "standby", "go offline",
    "turn off", "sleep", "close", "end session",
}

# Short acknowledgement spoken while the LLM is generating a reply.
_THINKING_ACK = "On it, Sir."

# Spoken when wake word is heard but nothing was transcribed.
_NO_SPEECH_REPLY = "I didn't catch that, Sir. Could you repeat?"

# Spoken at session start / wake.
_GREETING = f"I'm listening, {config.USER_NAME}."


def _is_stop_command(text: str) -> bool:
    """
    Return True if *text* is a stop command.
    Strips punctuation and checks both substring and word-boundary matches
    to handle Whisper transcription variations like "Stop." / "Stopped." / "Please stop".
    """
    import re as _re
    lowered = _re.sub(r"[^\w\s]", "", text.lower()).strip()
    return any(phrase in lowered for phrase in _STOP_PHRASES)


def _first_two_sentences(text: str) -> str:
    """Return the first 2 sentences of *text* for faster TTS response."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sentences[:2])


class VoiceLoop:
    """
    Orchestrates the full wake-word → STT → LLM → TTS → idle cycle.

    Instantiate once and call :meth:`run` (blocking) or :meth:`start`
    (background thread).

    Example::

        loop = VoiceLoop()
        loop.run()          # blocks until "goodbye" / loop.stop()
    """

    def __init__(
        self,
        engine: JarvisEngine,
        wake_word_model: str = "hey_jarvis",
        stt_model: str = "base",
        stt_language: str = "en",
        tts_voice: str = "af_heart",
        tts_speed: float = 1.0,
        wake_threshold: float = 0.5,
    ) -> None:
        self._engine = engine
        self._stt = SpeechToText(model_size=stt_model, language=stt_language)
        self._tts = TextToSpeech(voice=tts_voice, speed=tts_speed)
        self._detector = WakeWordDetector(
            on_detected=self._on_wake,
            model_name=wake_word_model,
            threshold=wake_threshold,
        )

        self._wake_event = threading.Event()
        self._stop_event = threading.Event()
        self._active = False  # True while inside a voice turn

        # Pre-load Whisper and TTS engine now so the first voice turn has no delay.
        logger.info("Pre-loading STT and TTS engines…")
        self._stt._ensure_model()
        self._tts._ensure_engine()
        logger.info("STT and TTS ready.")

        # Wire TTS into the reminder tool so reminders are spoken aloud.
        engine.set_reminder_callback(self._tts.speak)

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self) -> None:
        """
        Run the voice loop **synchronously** in the calling thread.
        Returns when :meth:`stop` is called or the user says a stop command.
        """
        logger.info("Voice loop starting.")
        self._stop_event.clear()
        self._detector.start()
        print(
            f"\n\033[96m[VOICE MODE]\033[0m  Say \033[92m\"Hey Jarvis\"\033[0m to activate.\n"
            f"             Say \033[91m\"Goodbye\" / \"Stop\"\033[0m to exit voice mode.\n"
        )

        try:
            while not self._stop_event.is_set():
                # Wait for wake word (1-second poll so stop_event is checked).
                triggered = self._wake_event.wait(timeout=1.0)
                if not triggered:
                    continue
                self._wake_event.clear()

                if self._stop_event.is_set():
                    break

                self._run_voice_turn()

        finally:
            self._detector.stop()
            logger.info("Voice loop stopped.")

    def start(self) -> threading.Thread:
        """
        Start the voice loop on a **daemon thread** and return the thread.
        Useful when the caller also wants to keep a CLI running.
        """
        t = threading.Thread(target=self.run, daemon=True, name="voice-loop")
        t.start()
        return t

    def stop(self) -> None:
        """Signal the voice loop to exit cleanly."""
        self._stop_event.set()
        self._wake_event.set()  # unblock any wait()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_wake(self) -> None:
        """Called by WakeWordDetector on the detector thread."""
        if not self._active:
            self._wake_event.set()

    def _run_voice_turn(self) -> None:
        """Execute a single wake→listen→think→speak cycle."""
        self._active = True
        try:
            # 1. Acknowledge wake — pause detector so mic is free for STT.
            print("\033[92m[JARVIS]\033[0m  Wake word heard — listening…")
            self._detector.pause()

            # 2. Capture and transcribe speech.
            text = self._stt.listen()
            if not text:
                self._tts.speak(_NO_SPEECH_REPLY)
                return

            print(f"\033[96m[YOU]\033[0m  {text}")

            # 3. Check for stop command before hitting the LLM.
            if _is_stop_command(text):
                farewell = "Understood. Going to standby, Sir."
                print(f"\033[92m[JARVIS]\033[0m  {farewell}")
                self._tts.speak(farewell)
                self.stop()
                return  # finally block still runs → resume() + _active=False

            # 4. Get reply from the engine.
            reply = self._engine.process(text)
            if not reply:
                reply = "I'm not sure how to respond to that, Sir."

            # Trim history to voice window so long sessions stay fast.
            max_msgs = config.VOICE_MAX_HISTORY_TURNS * 2
            h = self._engine.orchestrator.history
            if len(h) > max_msgs:
                self._engine.orchestrator.history = h[-max_msgs:]

            print(f"\033[92m[JARVIS]\033[0m  {reply}")

            # 5. Speak the full reply.
            self._tts.speak(reply)

        except Exception as exc:
            logger.exception("Error in voice turn: %s", exc)
            try:
                self._tts.speak("I encountered an error, Sir. Please try again.")
            except Exception:
                pass  # TTS itself might have failed
        finally:
            # Always resume wake detection and clear active flag.
            self._active = False
            self._detector.resume()
            logger.debug("Voice turn complete — back to idle.")
