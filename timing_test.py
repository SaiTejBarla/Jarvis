import time, logging, sys
logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

import config
from core.engine import JarvisEngine

print("=== Timing each stage ===\n")

# Stage 1: STT
t = time.time()
from voice.speech_to_text import SpeechToText
stt = SpeechToText(model_size=config.WHISPER_MODEL, language=config.WHISPER_LANGUAGE)
stt._ensure_model()
print(f"[1] Whisper model load:  {time.time()-t:.2f}s  (model={config.WHISPER_MODEL})")

t = time.time()
print("\n[2] Speak a sentence now — timing STT listen+transcribe...")
text = stt.listen()
print(f"[2] STT listen+transcribe: {time.time()-t:.2f}s  → {text!r}")

# Stage 2: LLM
t = time.time()
engine = JarvisEngine()
print(f"\n[3] Engine init: {time.time()-t:.2f}s")

if text:
    t = time.time()
    reply = engine.process(text)
    print(f"[4] LLM reply:  {time.time()-t:.2f}s  → {reply[:80] if reply else '(none)'}…")

# Stage 3: TTS
t = time.time()
from voice.text_to_speech import TextToSpeech
tts = TextToSpeech()
tts._ensure_engine()
print(f"\n[5] TTS engine init: {time.time()-t:.2f}s")

if reply:
    t = time.time()
    tts.speak(reply[:100])
    print(f"[6] TTS speak: {time.time()-t:.2f}s")
