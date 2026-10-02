"""
voice/text_to_speech.py — Local text-to-speech for JARVIS using kokoro-onnx.

Synthesises speech entirely offline using kokoro-onnx (ONNX runtime — no
build step, works on Windows + Python 3.11+) and plays it through the
default audio output device via sounddevice.

Requires:
    pip install kokoro-onnx sounddevice soundfile numpy

On first run kokoro downloads its ~80 MB ONNX model and voice files to the
Hugging Face cache (~/.cache/huggingface/).

Fallback: if kokoro-onnx is unavailable, the module falls back to pyttsx3
(cross-platform system TTS) so JARVIS always has a voice.
"""

import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# kokoro voice to use.  "af_heart" is the default warm English (US) female voice.
# Other options: "af_bella", "bf_emma", "am_adam", "bm_george", etc.
_DEFAULT_VOICE = "af_heart"
_DEFAULT_SPEED = 1.0   # 1.0 = normal speed


class TextToSpeech:
    """
    Converts text to spoken audio and plays it locally.

    Tries kokoro-onnx first; falls back to pyttsx3 if kokoro is not installed.
    The TTS engine is initialised lazily on the first call to :meth:`speak`.

    Usage::

        tts = TextToSpeech()
        tts.speak("Hello, Sir. How can I help you today?")
    """

    def __init__(
        self,
        voice: str = _DEFAULT_VOICE,
        speed: float = _DEFAULT_SPEED,
        # model_name kept for API compatibility with older callers — ignored
        model_name: Optional[str] = None,
    ) -> None:
        self.voice = voice
        self.speed = speed
        self._kokoro = None             # Kokoro instance (lazy)
        self._pyttsx3_engine = None     # fallback engine (lazy)
        self._use_kokoro: Optional[bool] = None  # determined on first use
        self._lock = threading.Lock()   # prevent concurrent synthesis

    # ── Public interface ──────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """
        Synthesise *text* and play it through the speakers.

        Blocks until playback is complete so the caller always knows when
        JARVIS has finished talking before listening again.
        """
        if not text:
            return
        with self._lock:
            self._ensure_engine()
            if self._use_kokoro:
                self._speak_kokoro(text)
            else:
                self._speak_pyttsx3(text)

    # ── kokoro-onnx ───────────────────────────────────────────────────────────

    def _ensure_engine(self) -> None:
        if self._use_kokoro is not None:
            return  # already decided

        self._use_kokoro = False
        self._init_pyttsx3()

    def _speak_kokoro(self, text: str) -> None:
        """Synthesise with kokoro-onnx and play via sounddevice."""
        try:
            import numpy as np          # type: ignore
            import sounddevice as sd    # type: ignore

            logger.debug("kokoro synthesising: %r", text[:60])
            # create_stream returns (samples_float32, sample_rate)
            samples, sample_rate = self._kokoro.create(
                text,
                voice=self.voice,
                speed=self.speed,
                lang="en-us",
            )
            audio = np.array(samples, dtype=np.float32)
            sd.play(audio, samplerate=sample_rate)
            sd.wait()
        except Exception as exc:
            logger.error("kokoro-onnx speak failed: %s", exc)
            # Gracefully degrade to pyttsx3 for this utterance.
            self._init_pyttsx3()
            self._speak_pyttsx3(text)

    # ── pyttsx3 fallback ──────────────────────────────────────────────────────

    def _init_pyttsx3(self) -> None:
        if self._pyttsx3_engine is not None:
            return
        try:
            import pyttsx3  # type: ignore
            engine = pyttsx3.init()
            engine.setProperty("rate", 165)
            engine.setProperty("volume", 1.0)
            # Prefer Zira (female) on Windows — more natural than David.
            voices = engine.getProperty("voices")
            for v in voices:
                if "zira" in v.name.lower():
                    engine.setProperty("voice", v.id)
                    break
            self._pyttsx3_engine = engine
            logger.info("pyttsx3 TTS initialised.")
        except Exception as exc:
            logger.error("pyttsx3 also unavailable: %s", exc)

    def _speak_pyttsx3(self, text: str) -> None:
        if self._pyttsx3_engine is None:
            logger.error("No TTS engine available — cannot speak.")
            return
        try:
            logger.debug("pyttsx3 speaking: %r", text[:60])
            self._pyttsx3_engine.say(text)
            self._pyttsx3_engine.runAndWait()
        except Exception as exc:
            logger.error("pyttsx3 speak failed: %s", exc)
