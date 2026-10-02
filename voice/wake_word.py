"""
voice/wake_word.py — Wake-word detection for JARVIS.

Uses openWakeWord to listen continuously for the phrase "Hey Jarvis".
The detector runs in a tight loop on a background thread and fires a
callback the moment the trigger is heard.

Requires:
    pip install openwakeword pyaudio

openWakeWord ships with a built-in "hey_jarvis" model that is used by
default.  If the model file is not bundled yet, openWakeWord will download
it on first run.
"""

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Minimum activation score (0–1) for a positive detection.
_DEFAULT_THRESHOLD = 0.5
# How long (seconds) to block after a detection before listening again.
# Prevents the same utterance from firing the callback twice.
_REFRACTORY_PERIOD = 2.0


class WakeWordDetector:
    """
    Continuously listens on the default microphone and calls *on_detected*
    each time the configured wake phrase is recognised.

    Usage::

        detector = WakeWordDetector(on_detected=my_callback)
        detector.start()
        ...
        detector.stop()
    """

    def __init__(
        self,
        on_detected: Callable[[], None],
        model_name: str = "hey_jarvis",
        threshold: float = _DEFAULT_THRESHOLD,
        chunk_size: int = 1280,
    ) -> None:
        self.on_detected = on_detected
        self.model_name = model_name
        self.threshold = threshold
        self.chunk_size = chunk_size

        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None

    # ── Public interface ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background listener thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Wake-word detector started (model=%s, threshold=%.2f).",
                    self.model_name, self.threshold)

    def pause(self) -> None:
        """Pause audio capture — closes the mic stream so STT can open it."""
        self._paused = True
        # Give the listen loop one cycle to close the stream.
        time.sleep(0.15)

    def resume(self) -> None:
        """Resume audio capture — loop will reopen the mic stream."""
        self._paused = False

    def stop(self) -> None:
        """Signal the listener to stop and wait for it to exit."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Wake-word detector stopped.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _listen_loop(self) -> None:
        try:
            import pyaudio  # type: ignore
            from openwakeword.model import Model  # type: ignore
        except ImportError as exc:
            logger.error(
                "Wake-word dependencies not installed: %s. "
                "Run: pip install openwakeword pyaudio",
                exc,
            )
            self._running = False
            return

        import numpy as np  # type: ignore

        oww_model = Model(wakeword_models=[self.model_name], inference_framework="onnx")

        last_detected_at = 0.0
        pa = pyaudio.PyAudio()
        stream = None

        def _open_stream():
            return pa.open(
                rate=16000,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                frames_per_buffer=self.chunk_size,
            )

        def _close_stream(s):
            try:
                s.stop_stream()
                s.close()
            except Exception:
                pass

        try:
            stream = _open_stream()
            logger.debug("Microphone stream opened — listening for wake word.")

            while self._running:
                if self._paused:
                    # Close mic so STT can open it.
                    if stream is not None:
                        _close_stream(stream)
                        stream = None
                        logger.debug("Mic released for STT.")
                    time.sleep(0.05)
                    continue
                # Reopen mic after a pause — small delay lets Windows release the device.
                if stream is None:
                    time.sleep(0.3)
                    stream = _open_stream()
                    logger.debug("Mic reclaimed by wake detector.")
                audio_bytes = stream.read(self.chunk_size, exception_on_overflow=False)
                # openWakeWord expects a flat int16 NumPy array, not raw bytes.
                audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
                oww_model.predict(audio_chunk)

                scores = oww_model.prediction_buffer.get(self.model_name, [])
                latest_score = scores[-1] if scores else 0.0

                if latest_score >= self.threshold:
                    now = time.monotonic()
                    if now - last_detected_at >= _REFRACTORY_PERIOD:
                        last_detected_at = now
                        logger.info(
                            "Wake word detected! (score=%.3f)", latest_score
                        )
                        self.on_detected()
        finally:
            if stream is not None:
                _close_stream(stream)
            pa.terminate()
            logger.debug("Microphone stream closed.")
