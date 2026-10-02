"""
tools/clipboard.py — Clipboard monitor and actor for JARVIS.

Reads, summarises, and acts on clipboard content.
Uses stdlib tkinter for clipboard access — no extra install needed on Windows.

Commands:
    "read my clipboard"
    "summarise clipboard"
    "what's in my clipboard"
    "copy <text> to clipboard"
"""

import logging
import re
from .base import BaseTool

logger = logging.getLogger(__name__)


def _get_clipboard() -> str:
    """Read the current clipboard text."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        text = root.clipboard_get()
        root.destroy()
        return text
    except Exception as exc:
        logger.warning("Clipboard read failed: %s", exc)
        return ""


def _set_clipboard(text: str) -> None:
    """Write text to the clipboard."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()   # keep alive long enough for paste
        root.after(500, root.destroy)
        root.mainloop()
    except Exception as exc:
        logger.warning("Clipboard write failed: %s", exc)


class ClipboardTool(BaseTool):
    name = "clipboard"
    description = (
        "Read, summarise, or copy text to/from clipboard. "
        "e.g. 'read my clipboard', 'summarise clipboard', 'copy Hello to clipboard'."
    )

    def run(self, query: str) -> str:
        q = query.lower().strip()

        # Copy to clipboard
        m = re.search(r"copy\s+(.+?)\s+to\s+clipboard", query, re.IGNORECASE)
        if m:
            text = m.group(1).strip()
            _set_clipboard(text)
            return f"Copied to clipboard, Sir: \"{text[:60]}\""

        # Read clipboard
        if re.search(r"\b(read|get|show|what.?s in|whats in)\b.*clipboard", q):
            content = _get_clipboard()
            if not content:
                return "The clipboard is empty, Sir."
            preview = content[:300]
            suffix = "…" if len(content) > 300 else ""
            return f"Clipboard contains: {preview}{suffix}"

        # Summarise clipboard — return truncated for LLM to summarise
        if re.search(r"\b(summar|analyse|analyze|explain)\b.*clipboard", q):
            content = _get_clipboard()
            if not content:
                return "The clipboard is empty, Sir."
            # Return the raw content so the engine can pass to LLM
            return f"Here is the clipboard content for you to summarise:\n\n{content[:1000]}"

        # Default: read
        content = _get_clipboard()
        if not content:
            return "The clipboard is empty, Sir."
        return f"Clipboard: {content[:200]}"
