"""
tools/notes.py — Local note-taking tool for JARVIS.

Saves, lists, searches, and reads markdown notes stored under data/notes/.
All operations are local — no cloud, no API key.

Commands:
    "take a note: buy groceries tomorrow"
    "show my notes"
    "search notes for groceries"
    "read note 1"
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from .base import BaseTool

import config

logger = logging.getLogger(__name__)

NOTES_DIR = config.DATA_DIR / "notes"


class NotesTool(BaseTool):
    name = "notes"
    description = (
        "Take, list, search, or read notes. "
        "e.g. 'take a note: buy groceries', 'show my notes', 'search notes for X'."
    )

    def __init__(self) -> None:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)

    def run(self, query: str) -> str:
        q = query.lower().strip()

        # Take / create a note
        if re.search(r"\b(take|add|create|write|save|make)\b.{0,20}\bnote", q):
            content = re.split(r"note[:\s]+", query, maxsplit=1, flags=re.IGNORECASE)
            text = content[-1].strip() if len(content) > 1 else query.strip()
            return self._save_note(text)

        # Search notes
        m = re.search(r"search\s+notes?\s+(?:for\s+)?(.+)", q)
        if m:
            return self._search_notes(m.group(1).strip())

        # Read specific note
        m = re.search(r"read\s+note\s+(\d+)", q)
        if m:
            return self._read_note(int(m.group(1)))

        # List / show notes
        if re.search(r"\b(show|list|view|display|my)\b.{0,10}\bnotes?\b", q):
            return self._list_notes()

        # Delete note
        m = re.search(r"delete\s+note\s+(\d+)", q)
        if m:
            return self._delete_note(int(m.group(1)))

        return "I didn't understand that note command, Sir. Try 'take a note: your text'."

    def _save_note(self, text: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = NOTES_DIR / f"note_{timestamp}.md"
        filename.write_text(
            f"# Note — {datetime.now().strftime('%B %d, %Y %I:%M %p')}\n\n{text}\n",
            encoding="utf-8",
        )
        logger.info("Note saved: %s", filename.name)
        return f"Note saved, Sir: \"{text[:60]}{'…' if len(text) > 60 else ''}\""

    def _list_notes(self) -> str:
        files = sorted(NOTES_DIR.glob("note_*.md"), reverse=True)
        if not files:
            return "You have no notes yet, Sir."
        lines = [f"You have {len(files)} note{'s' if len(files) != 1 else ''}, Sir:"]
        for i, f in enumerate(files[:10], 1):
            first_line = self._first_line(f)
            lines.append(f"  {i}. {first_line}")
        return "\n".join(lines)

    def _search_notes(self, keyword: str) -> str:
        files = sorted(NOTES_DIR.glob("note_*.md"), reverse=True)
        matches = []
        for f in files:
            content = f.read_text(encoding="utf-8")
            if keyword.lower() in content.lower():
                matches.append(self._first_line(f))
        if not matches:
            return f"No notes found matching '{keyword}', Sir."
        lines = [f"Found {len(matches)} matching note{'s' if len(matches) != 1 else ''}, Sir:"]
        for i, m in enumerate(matches[:5], 1):
            lines.append(f"  {i}. {m}")
        return "\n".join(lines)

    def _read_note(self, index: int) -> str:
        files = sorted(NOTES_DIR.glob("note_*.md"), reverse=True)
        if not files:
            return "You have no notes, Sir."
        if index < 1 or index > len(files):
            return f"Note {index} doesn't exist. You have {len(files)} note(s), Sir."
        content = files[index - 1].read_text(encoding="utf-8").strip()
        # Strip the markdown header
        content = re.sub(r"^#.+\n+", "", content).strip()
        return f"Note {index}: {content}"

    def _delete_note(self, index: int) -> str:
        files = sorted(NOTES_DIR.glob("note_*.md"), reverse=True)
        if not files or index < 1 or index > len(files):
            return f"Note {index} doesn't exist, Sir."
        files[index - 1].unlink()
        return f"Note {index} deleted, Sir."

    def _first_line(self, path: Path) -> str:
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip().lstrip("#").strip()
                if line:
                    return line
        except Exception:
            pass
        return path.stem
