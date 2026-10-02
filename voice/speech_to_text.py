"""
voice/speech_to_text.py — Local speech-to-text for JARVIS using OpenAI Whisper.

Captures audio from the microphone until silence is detected, then
transcribes it with the locally-running Whisper model.  No data is
ever sent to the cloud.

Requires:
    pip install openai-whisper pyaudio

Model size guide (loaded once, cached on disk):
    "tiny"   — ~39 MB,  fastest,  lowest accuracy
    "base"   — ~74 MB,  fast,     decent accuracy   ← default
    "small"  — ~244 MB, moderate, good accuracy
    "medium" — ~769 MB, slower,   great accuracy
    "large"  — ~1.5 GB, slowest,  best accuracy
"""

import io
import logging
import wave
from typing import Optional

logger = logging.getLogger(__name__)

# Audio capture constants
_SAMPLE_RATE = 16_000           # Hz — Whisper expects 16 kHz
_CHANNELS = 1
_SAMPLE_WIDTH = 2               # bytes (16-bit PCM)
_CHUNK_SIZE = 1_024             # frames per read call

_SILENCE_THRESHOLD = 100        # RMS amplitude below which audio is "silent"
_SILENCE_CHUNKS = 15            # consecutive silent chunks → end of speech (~1 s)
_MAX_RECORD_CHUNKS = 250        # safety limit (~4 s at 16 kHz / 1024 chunk)


def _rms(data: bytes) -> float:
    """Return the root-mean-square amplitude of a 16-bit PCM chunk."""
    import array
    samples = array.array("h", data)
    if not samples:
        return 0.0
    return (sum(s * s for s in samples) / len(samples)) ** 0.5


class SpeechToText:
    """
    Wraps a Whisper model and a microphone capture loop.

    The model is loaded lazily on the first call to :meth:`listen`.

    Usage::

        stt = SpeechToText(model_size="base")
        text = stt.listen()   # blocks until speech is captured and transcribed
    """

    def __init__(self, model_size: str = "base", language: str = "en") -> None:
        self.model_size = model_size
        self.language = language
        self._model = None  # loaded on first use

    # ── Public interface ──────────────────────────────────────────────────────

    def listen(self) -> Optional[str]:
        """
        Record from the microphone until silence, then transcribe.

        Returns the transcribed text, or None if nothing was captured or
        an error occurred.
        """
        self._ensure_model()
        audio_bytes = self._record_until_silence()
        if not audio_bytes:
            logger.debug("No speech detected; skipping transcription.")
            return None
        return self._transcribe(audio_bytes)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        try:
            import whisper  # type: ignore
        except ImportError:
            raise RuntimeError(
                "openai-whisper is not installed. "
                "Run: pip install openai-whisper"
            )
        logger.info("Loading Whisper model '%s' (first run may download it)…",
                    self.model_size)
        self._model = whisper.load_model(self.model_size)
        logger.info("Whisper model '%s' ready.", self.model_size)

    def _record_until_silence(self) -> Optional[bytes]:
        """
        Open the microphone, capture audio until a silence boundary is hit,
        and return raw PCM bytes.  Returns None if nothing usable was recorded.
        """
        try:
            import pyaudio  # type: ignore
        except ImportError:
            raise RuntimeError(
                "pyaudio is not installed. "
                "Run: pip install pyaudio"
            )

        pa = pyaudio.PyAudio()
        stream = pa.open(
            rate=_SAMPLE_RATE,
            channels=_CHANNELS,
            format=pa.get_format_from_width(_SAMPLE_WIDTH),
            input=True,
            frames_per_buffer=_CHUNK_SIZE,
        )

        logger.debug("Recording — speak now…")
        frames: list[bytes] = []
        silent_chunks = 0
        speech_started = False

        try:
            for _ in range(_MAX_RECORD_CHUNKS):
                chunk = stream.read(_CHUNK_SIZE, exception_on_overflow=False)
                frames.append(chunk)
                amplitude = _rms(chunk)
                logger.debug("RMS=%.1f speech_started=%s silent_chunks=%d",
                             amplitude, speech_started, silent_chunks)

                if amplitude > _SILENCE_THRESHOLD:
                    speech_started = True
                    silent_chunks = 0
                elif speech_started:
                    silent_chunks += 1
                    if silent_chunks >= _SILENCE_CHUNKS:
                        logger.debug("Silence limit reached — stopping recording.")
                        break
        finally:
            stream.stop_stream()
            stream.close()
            pa.terminate()

        if not speech_started:
            logger.warning("No speech detected (all RMS below threshold=%d).", _SILENCE_THRESHOLD)
            return None

        raw_pcm = b"".join(frames)
        logger.debug("Recorded %d bytes of audio.", len(raw_pcm))
        return raw_pcm

    def _transcribe(self, pcm_bytes: bytes) -> Optional[str]:
        """Convert raw PCM bytes to a WAV buffer and run Whisper on it."""
        import numpy as np  # type: ignore

        # Wrap PCM in an in-memory WAV container so Whisper can decode it.
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(_CHANNELS)
            wf.setsampwidth(_SAMPLE_WIDTH)
            wf.setframerate(_SAMPLE_RATE)
            wf.writeframes(pcm_bytes)
        wav_buffer.seek(0)

        # Whisper expects a float32 numpy array normalised to [-1, 1].
        audio_np = (
            np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            / 32768.0
        )

        logger.debug("Transcribing %d audio samples…", len(audio_np))
        result = self._model.transcribe(audio_np, language=self.language, fp16=False)
        text = result.get("text", "").strip()
        logger.info("STT transcription: %r", text)
        return text if text else None
