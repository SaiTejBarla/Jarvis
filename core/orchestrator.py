"""
core/orchestrator.py — The brain router for JARVIS.

Responsibilities (Phase 1):
  • Send a conversation to Ollama (local LLM) and return the reply.
  • Fall back to Google Gemini when Ollama is unavailable or the caller
    explicitly requests it.
  • Maintain a rolling conversation history within the context window.

Later phases will extend this with intent detection and agent dispatch.
"""

import logging
from typing import Optional

import requests

import config

logger = logging.getLogger(__name__)


# ─── History management ───────────────────────────────────────────────────────

def _trim_history(history: list[dict]) -> list[dict]:
    """Keep the last MAX_HISTORY_TURNS * 2 messages (user + assistant pairs)."""
    max_messages = config.MAX_HISTORY_TURNS * 2
    if len(history) > max_messages:
        return history[-max_messages:]
    return history


# ─── Ollama ───────────────────────────────────────────────────────────────────

def _chat_ollama(history: list[dict], memory_context: str = "") -> str:
    """
    Send *history* to the local Ollama instance and return the assistant reply.
    Raises RuntimeError if the request fails.
    """
    url = f"{config.OLLAMA_BASE_URL}/api/chat"
    # Use the active persona's prompt if available
    try:
        from core.persona import get_system_prompt
        system = get_system_prompt()
    except Exception:
        system = config.SYSTEM_PROMPT
    if memory_context:
        system += f"\n\n{memory_context}"
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + history,
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=config.OLLAMA_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot reach Ollama at {config.OLLAMA_BASE_URL}. "
            "Is Ollama running? Try: ollama serve"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"Ollama timed out after {config.OLLAMA_TIMEOUT}s. "
            "Try a smaller model or increase OLLAMA_TIMEOUT in .env."
        )
    except Exception as exc:
        raise RuntimeError(f"Ollama error: {exc}") from exc


# ─── Gemini ───────────────────────────────────────────────────────────────────

def gemini_summarise(text: str, instruction: str = "Summarise this concisely in 2-3 sentences.") -> str:
    """
    One-shot Gemini call for summarisation tasks (search results, scraped pages, news).
    Returns the summary or falls back gracefully if Gemini is unavailable.
    """
    if not config.GEMINI_FALLBACK_ENABLED:
        return text[:500]  # plain truncation if no Gemini key

    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(model_name=config.GEMINI_MODEL)
        response = model.generate_content(f"{instruction}\n\n{text[:4000]}")
        return response.text.strip()
    except Exception as exc:
        logger.warning("Gemini summarise failed: %s", exc)
        return text[:500]


def _chat_gemini(history: list[dict]) -> str:
    """
    Send *history* to Google Gemini and return the assistant reply.
    Requires GEMINI_API_KEY to be set.
    Raises RuntimeError if the request fails or the key is missing.
    """
    if not config.GEMINI_API_KEY:
        raise RuntimeError(
            "Gemini fallback requested but GEMINI_API_KEY is not set in .env."
        )

    try:
        import google.generativeai as genai  # type: ignore
    except ImportError:
        raise RuntimeError(
            "google-generativeai package is not installed. "
            "Run: pip install google-generativeai"
        )

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(
        model_name=config.GEMINI_MODEL,
        system_instruction=config.SYSTEM_PROMPT,
    )

    # Convert OpenAI-style history to Gemini's format.
    gemini_history = []
    for msg in history[:-1]:  # all but last message go into history
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})

    chat = model.start_chat(history=gemini_history)
    last_user_message = history[-1]["content"] if history else ""

    try:
        response = chat.send_message(last_user_message)
        return response.text.strip()
    except Exception as exc:
        raise RuntimeError(f"Gemini error: {exc}") from exc


# ─── Public interface ─────────────────────────────────────────────────────────

class Orchestrator:
    """
    Stateful conversation orchestrator.

    Usage:
        orch = Orchestrator()
        reply = orch.chat("What time is it?")
    """

    def __init__(self) -> None:
        self.history: list[dict] = []

    def chat(self, user_message: str, force_gemini: bool = False,
             memory_context: str = "") -> str:
        """
        Process *user_message*, update history, and return JARVIS's reply.

        If *force_gemini* is True, or Ollama fails and Gemini is configured,
        the fallback LLM is used transparently.
        """
        self.history.append({"role": "user", "content": user_message})
        self.history = _trim_history(self.history)

        reply: Optional[str] = None
        used_fallback = False

        if not force_gemini:
            try:
                reply = _chat_ollama(self.history, memory_context=memory_context)
                logger.debug("Response from Ollama (%s).", config.OLLAMA_MODEL)
            except RuntimeError as exc:
                logger.warning("Ollama unavailable: %s", exc)
                if config.GEMINI_FALLBACK_ENABLED:
                    logger.info("Falling back to Gemini (%s).", config.GEMINI_MODEL)
                    used_fallback = True
                else:
                    # Re-raise so the engine can surface the error to the user.
                    self.history.pop()  # don't keep failed turn
                    raise

        if reply is None:
            # Either force_gemini=True or Ollama failed and fallback is enabled.
            try:
                reply = _chat_gemini(self.history)
                logger.debug(
                    "Response from Gemini (%s)%s.",
                    config.GEMINI_MODEL,
                    " [fallback]" if used_fallback else "",
                )
            except RuntimeError:
                self.history.pop()  # don't keep failed turn
                raise

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> None:
        """Clear conversation history."""
        self.history.clear()
        logger.info("Conversation history cleared.")
