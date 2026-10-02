"""
core/audit.py — Action audit log for JARVIS.

Every tool call, auth event, and critical action is appended to
data/logs/audit.log in structured JSON-lines format.

Usage::

    audit = AuditLog()
    audit.log_tool("weather", "London", "Weather in London: ...")
    audit.log_auth("PIN accepted", "delete files in Downloads")
    audit.log_critical("delete files", blocked=True)
"""

import json
import logging
import threading
from datetime import datetime
from pathlib import Path

import config

logger = logging.getLogger(__name__)

AUDIT_FILE = config.DATA_DIR / "logs" / "audit.log"


class AuditLog:
    """Thread-safe append-only audit log in JSON-lines format."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

    def log_tool(self, tool_name: str, query: str, result: str) -> None:
        self._append({
            "type": "tool_call",
            "tool": tool_name,
            "query": query[:200],
            "result_preview": result[:200],
        })

    def log_auth(self, event: str, action: str = "") -> None:
        self._append({
            "type": "auth",
            "event": event,
            "action": action[:200],
        })

    def log_critical(self, action: str, blocked: bool) -> None:
        self._append({
            "type": "critical_action",
            "action": action[:200],
            "blocked": blocked,
        })

    def log_llm(self, user_input: str, reply: str) -> None:
        self._append({
            "type": "llm_reply",
            "input": user_input[:200],
            "reply_preview": reply[:200],
        })

    def recent(self, n: int = 20) -> list[dict]:
        """Return the last n audit entries."""
        try:
            lines = AUDIT_FILE.read_text(encoding="utf-8").strip().splitlines()
            entries = []
            for line in lines[-n:]:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
            return list(reversed(entries))
        except Exception:
            return []

    def _append(self, entry: dict) -> None:
        entry["ts"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._lock:
                with open(AUDIT_FILE, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")
        except Exception as exc:
            logger.debug("Audit log write failed: %s", exc)
