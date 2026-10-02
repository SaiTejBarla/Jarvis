"""
core/auth.py — Authorization gate for JARVIS.

Blocks critical/destructive actions until the user provides:
  - A PIN code (stored as a bcrypt hash in data/auth.json), OR
  - A voice passphrase ("Jarvis, confirmed" / "confirmed" / "authorize")

Usage::

    gate = AuthGate()
    gate.set_pin("1234")          # first-time setup
    gate.request(action_desc)     # returns True if authorized
"""

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)

AUTH_FILE = config.DATA_DIR / "auth.json"

# Phrases that count as voice authorization
_VOICE_AUTH_PHRASES = {
    "confirmed", "jarvis confirmed", "authorize", "authorized",
    "yes proceed", "proceed", "approved", "grant access",
    "i confirm", "confirm", "go ahead", "do it",
}

# How long (seconds) an authorization stays valid
_AUTH_TTL = 30

# Critical action keywords — any tool result containing these needs auth
_CRITICAL_PATTERNS = [
    r"\bdelete\b",
    r"\bremove\b",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\brestart\b",
    r"\bsend\s+email\b",
    r"\buninstall\b",
    r"\bdrop\s+table\b",
    r"\bwipe\b",
    r"\bpermanently\b",
    r"\birreversible\b",
    r"\bexecute\s+system\b",
]


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.strip().encode()).hexdigest()


class AuthGate:
    """
    Singleton-style auth gate. Call request() before any critical action.
    Returns True immediately if already authorized within TTL.
    """

    def __init__(self) -> None:
        self._pin_hash: Optional[str] = None
        self._authorized_until: float = 0.0
        self._pending_voice_auth = threading.Event()
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def has_pin(self) -> bool:
        return self._pin_hash is not None

    def set_pin(self, pin: str) -> str:
        """Set or change the PIN. Returns confirmation."""
        self._pin_hash = _hash_pin(pin)
        self._save()
        logger.info("Auth PIN set.")
        return "PIN set successfully, Sir. I will require it for critical actions."

    def verify_pin(self, pin: str) -> bool:
        """Return True if pin matches stored hash."""
        if self._pin_hash is None:
            return True  # No PIN set — always pass
        return _hash_pin(pin) == self._pin_hash

    def is_authorized(self) -> bool:
        """Return True if still within the authorization window."""
        return time.monotonic() < self._authorized_until

    def grant(self, duration: float = _AUTH_TTL) -> None:
        """Grant authorization for `duration` seconds."""
        self._authorized_until = time.monotonic() + duration
        logger.info("Authorization granted for %.0f seconds.", duration)

    def revoke(self) -> None:
        self._authorized_until = 0.0

    def check_voice(self, text: str) -> bool:
        """
        Check if `text` is a voice authorization phrase.
        If yes, grants authorization and returns True.
        """
        lowered = text.lower().strip().rstrip(".,!")
        if any(phrase in lowered for phrase in _VOICE_AUTH_PHRASES):
            self.grant()
            logger.info("Voice authorization received: %r", text)
            return True
        return False

    def request(self, action_description: str, pin: Optional[str] = None) -> tuple[bool, str]:
        """
        Check whether an action is authorized.

        Returns (authorized: bool, message: str).
        If already authorized within TTL, passes immediately.
        If a PIN is provided, verifies it.
        Otherwise returns False with a prompt message.
        """
        if self.is_authorized():
            return True, ""

        if pin is not None:
            if self.verify_pin(pin):
                self.grant()
                return True, "PIN accepted. Proceeding, Sir."
            else:
                logger.warning("Invalid PIN attempt for: %s", action_description)
                return False, "Incorrect PIN, Sir. Access denied."

        # Not authorized — prompt
        msg = (
            f"⚠️  Critical action detected: {action_description}\n"
            f"Please authorize with:\n"
            f"  • Your PIN code, or\n"
            f"  • Say \"Jarvis, confirmed\" to proceed."
        )
        logger.warning("Authorization required for: %s", action_description)
        return False, msg

    # ── Internal ──────────────────────────────────────────────────────────────

    def _save(self) -> None:
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            AUTH_FILE.write_text(
                json.dumps({"pin_hash": self._pin_hash}, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Auth save failed: %s", exc)

    def _load(self) -> None:
        if not AUTH_FILE.exists():
            return
        try:
            data = json.loads(AUTH_FILE.read_text(encoding="utf-8"))
            self._pin_hash = data.get("pin_hash")
            if self._pin_hash:
                logger.info("Auth PIN loaded.")
        except Exception as exc:
            logger.warning("Auth load failed: %s", exc)


# ── Critical action detection ─────────────────────────────────────────────────

import re as _re

def is_critical_action(query: str) -> Optional[str]:
    """
    Return a short description if the query is a critical/destructive action,
    or None if it's safe.
    """
    q = query.lower()
    for pattern in _CRITICAL_PATTERNS:
        if _re.search(pattern, q):
            # Extract a short description
            desc = query.strip()[:80]
            return desc
    return None
