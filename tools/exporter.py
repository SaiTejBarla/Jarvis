"""
tools/exporter.py — Conversation export tool for JARVIS.

Exports the current session's conversation history to a markdown or
plain-text file in data/exports/.

Commands:
    "export conversation"
    "save this chat"
    "export to markdown"
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from .base import BaseTool

import config

logger = logging.getLogger(__name__)

EXPORTS_DIR = config.DATA_DIR / "exports"


class ExporterTool(BaseTool):
    name = "exporter"
    description = "Export the current conversation to a markdown file."

    # History is injected by the engine after init
    _history: Optional[list] = None

    def set_history(self, history: list) -> None:
        self._history = history

    def run(self, query: str) -> str:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        history = self._history or []
        if not history:
            return "There's nothing to export yet, Sir."

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = EXPORTS_DIR / f"conversation_{ts}.md"

        lines = [
            f"# JARVIS Conversation Export",
            f"*Exported: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*",
            "",
            "---",
            "",
        ]
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                lines.append(f"**You:** {content}")
            elif role == "assistant":
                lines.append(f"**JARVIS:** {content}")
            lines.append("")

        filename.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Conversation exported to %s", filename.name)
        return f"Conversation exported to: {filename.name}, Sir."
