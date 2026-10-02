"""
voice/__init__.py — Public API for the JARVIS voice layer.

Exposes the three Phase-2 components so callers can do:

    from voice import WakeWordDetector, SpeechToText, TextToSpeech
"""

from voice.wake_word import WakeWordDetector
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech

__all__ = ["WakeWordDetector", "SpeechToText", "TextToSpeech"]
