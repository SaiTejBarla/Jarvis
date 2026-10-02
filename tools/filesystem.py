"""
tools/filesystem.py — File system tool for JARVIS.

List, read, summarise, and search local files and folders.
Operates only within safe allowed paths (home dir + project dir).

Commands:
    "list files in Downloads"
    "what files are in Documents"
    "read file C:/Users/Me/notes.txt"
    "summarise file report.txt"
    "find files named *.py in jarvis"
"""

import logging
import os
import re
from pathlib import Path
from .base import BaseTool

logger = logging.getLogger(__name__)

# Safe base directories — only search/read within these
_SAFE_ROOTS = [
    Path.home(),
    Path("C:/jarvis"),
]

# File extensions safe to read as text
_TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
    ".csv", ".html", ".xml", ".ini", ".cfg", ".log", ".rst",
}

_MAX_READ_BYTES = 4000  # max chars to return from a file


def _is_safe(path: Path) -> bool:
    """Return True if path is within an allowed safe root."""
    try:
        path = path.resolve()
        return any(
            str(path).startswith(str(root.resolve()))
            for root in _SAFE_ROOTS
        )
    except Exception:
        return False


class FileSystemTool(BaseTool):
    name = "filesystem"
    description = (
        "List, read, or search local files and folders. "
        "e.g. 'list files in Downloads', 'read file notes.txt', 'find .py files in jarvis'."
    )

    def run(self, query: str) -> str:
        q = query.lower().strip()

        # List files in a directory
        m = re.search(r"(?:list|show|what.?s in|whats in)\s+(?:files?\s+in\s+)?(.+)", q)
        if m and not re.search(r"\b(read|find|search)\b", q):
            return self._list_dir(m.group(1).strip())

        # Find files by pattern
        m = re.search(r"find\s+(?:files?\s+)?(?:named\s+)?(\S+)\s+in\s+(.+)", q)
        if m:
            return self._find_files(m.group(1).strip(), m.group(2).strip())

        # Read / summarise a file
        m = re.search(r"(?:read|open|show|summarise|summarize)\s+(?:file\s+)?(.+)", query, re.IGNORECASE)
        if m:
            return self._read_file(m.group(1).strip())

        return "I didn't understand that file command, Sir."

    def _resolve(self, name: str) -> Path:
        """Resolve a name like 'Downloads', 'Documents', or a full path."""
        p = Path(name)
        if p.is_absolute():
            return p
        # Common shorthand names
        shortcuts = {
            "desktop": Path.home() / "Desktop",
            "downloads": Path.home() / "Downloads",
            "documents": Path.home() / "Documents",
            "pictures": Path.home() / "Pictures",
            "music": Path.home() / "Music",
            "videos": Path.home() / "Videos",
            "jarvis": Path("C:/jarvis"),
        }
        lower = name.lower().strip()
        if lower in shortcuts:
            return shortcuts[lower]
        # Try relative to home
        candidate = Path.home() / name
        if candidate.exists():
            return candidate
        return p

    def _list_dir(self, name: str) -> str:
        path = self._resolve(name)
        if not _is_safe(path):
            return f"Access denied to '{name}', Sir. I can only access home and project directories."
        if not path.exists():
            return f"Directory '{name}' not found, Sir."
        if not path.is_dir():
            return self._read_file(name)
        try:
            entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
            dirs = [e for e in entries if e.is_dir()]
            files = [e for e in entries if e.is_file()]
            lines = [f"Contents of {path} ({len(dirs)} folders, {len(files)} files):"]
            for d in dirs[:10]:
                lines.append(f"  📁 {d.name}/")
            for f in files[:15]:
                size = f.stat().st_size
                size_str = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
                lines.append(f"  📄 {f.name} ({size_str})")
            if len(dirs) + len(files) > 25:
                lines.append(f"  … and {len(dirs) + len(files) - 25} more")
            return "\n".join(lines)
        except PermissionError:
            return f"Permission denied reading '{name}', Sir."

    def _find_files(self, pattern: str, location: str) -> str:
        path = self._resolve(location)
        if not _is_safe(path):
            return f"Access denied to '{location}', Sir."
        if not path.exists():
            return f"Directory '{location}' not found, Sir."
        # Ensure glob pattern
        if "*" not in pattern and "." in pattern:
            glob_pat = f"**/*{pattern}"
        elif "*" not in pattern:
            glob_pat = f"**/*{pattern}*"
        else:
            glob_pat = f"**/{pattern}"
        try:
            matches = list(path.glob(glob_pat))[:20]
            if not matches:
                return f"No files matching '{pattern}' found in {location}, Sir."
            lines = [f"Found {len(matches)} file(s) matching '{pattern}':"]
            for m in matches:
                lines.append(f"  📄 {m.relative_to(path)}")
            return "\n".join(lines)
        except Exception as exc:
            return f"Search failed: {exc}"

    def _read_file(self, name: str) -> str:
        path = self._resolve(name)
        if not _is_safe(path):
            return f"Access denied to '{name}', Sir."
        if not path.exists():
            return f"File '{name}' not found, Sir."
        if path.is_dir():
            return self._list_dir(name)
        if path.suffix.lower() not in _TEXT_EXTENSIONS:
            return f"'{path.name}' is a binary file — I can only read text files, Sir."
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
            if len(content) > _MAX_READ_BYTES:
                return f"{content[:_MAX_READ_BYTES]}\n\n… (file truncated, {len(content)} total chars)"
            return f"Contents of {path.name}:\n\n{content}"
        except Exception as exc:
            return f"Could not read '{path.name}': {exc}"
