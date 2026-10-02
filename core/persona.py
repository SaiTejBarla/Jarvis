"""
core/persona.py — Multi-persona mode system for JARVIS.

Defines distinct personality presets that change the system prompt.
Personas can be switched at runtime via voice or CLI.

Available personas:
    jarvis    — Default JARVIS assistant (formal, precise)
    assistant — Friendly casual helper
    tutor     — Patient teacher / explainer
    coder     — Expert software engineer
    brief     — Ultra-concise, one-line answers only
"""

import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)

_PERSONAS: dict[str, dict] = {
    "jarvis": {
        "name": "JARVIS",
        "prompt": (
            f"You are {config.JARVIS_NAME}, a highly intelligent personal AI assistant "
            "inspired by Iron Man's J.A.R.V.I.S. You are precise, helpful, and slightly "
            f"formal but not robotic. Address the user as '{config.USER_NAME}'. "
            "Always reply in 1-2 short sentences. Never use bullet points, lists, or markdown. "
            "Be direct and to the point."
        ),
    },
    "assistant": {
        "name": "Friendly Assistant",
        "prompt": (
            f"You are a warm, friendly AI assistant. Address the user as '{config.USER_NAME}'. "
            "Be conversational, encouraging, and helpful. Keep answers brief and clear. "
            "Never use markdown formatting."
        ),
    },
    "tutor": {
        "name": "Tutor",
        "prompt": (
            f"You are a patient, expert tutor. Address the user as '{config.USER_NAME}'. "
            "Explain concepts clearly with simple analogies. Break down complex topics "
            "step by step. Encourage learning. Keep each explanation to 2-3 sentences "
            "unless the user asks for more detail."
        ),
    },
    "coder": {
        "name": "Code Expert",
        "prompt": (
            f"You are an expert software engineer. Address the user as '{config.USER_NAME}'. "
            "Give precise, correct, idiomatic code answers. Prefer brevity over verbosity. "
            "Always specify the language. If asked for code, provide only the code and "
            "a one-line explanation."
        ),
    },
    "brief": {
        "name": "Brief Mode",
        "prompt": (
            f"You are a concise AI. Address the user as '{config.USER_NAME}'. "
            "Answer every question in exactly ONE sentence. No exceptions. No markdown."
        ),
    },
}

# Active persona — default to jarvis
_active_persona: str = "jarvis"


def get_active_persona() -> str:
    return _active_persona


def get_system_prompt() -> str:
    """Return the system prompt for the current active persona."""
    return _PERSONAS.get(_active_persona, _PERSONAS["jarvis"])["prompt"]


def set_persona(name: str) -> Optional[str]:
    """
    Switch to a named persona. Returns a confirmation string or None if not found.
    """
    global _active_persona
    name = name.lower().strip()
    if name in _PERSONAS:
        _active_persona = name
        persona = _PERSONAS[name]
        logger.info("Persona switched to: %s", name)
        return f"Switched to {persona['name']} mode, Sir."
    # Fuzzy match
    for key in _PERSONAS:
        if key.startswith(name) or name in key:
            _active_persona = key
            persona = _PERSONAS[key]
            logger.info("Persona switched to: %s", key)
            return f"Switched to {persona['name']} mode, Sir."
    available = ", ".join(_PERSONAS.keys())
    return f"Unknown persona '{name}'. Available: {available}."


def list_personas() -> str:
    lines = ["Available personas, Sir:"]
    for key, p in _PERSONAS.items():
        active = " ← active" if key == _active_persona else ""
        lines.append(f"  {key}: {p['name']}{active}")
    return "\n".join(lines)
