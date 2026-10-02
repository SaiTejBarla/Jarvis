"""
tools/plugins.py — Plugin / skill system for JARVIS (Phase 7).

Allows dropping new tool files into data/plugins/ without editing core code.
Each plugin is a Python file that defines a class inheriting from BaseTool.

Plugin contract:
  - File: data/plugins/my_tool.py
  - Class: any class with name, description, and run(query) -> str
  - No base class import required — duck typing is used

Example plugin (data/plugins/joke_tool.py):

    class JokeTool:
        name = "joke"
        description = "Tell a random joke."

        def run(self, query):
            return "Why do programmers prefer dark mode? Because light attracts bugs."

Usage:
    registry = PluginRegistry()
    registry.load()
    result = registry.dispatch("tell me a joke")
"""

import importlib.util
import logging
import re
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)

PLUGINS_DIR = config.DATA_DIR / "plugins"


class PluginRegistry:
    """
    Loads and dispatches to user-defined plugins from data/plugins/.
    """

    def __init__(self) -> None:
        self._plugins: list = []

    def load(self) -> int:
        """Load all plugins from PLUGINS_DIR. Returns number loaded."""
        PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
        self._plugins.clear()
        count = 0
        for path in sorted(PLUGINS_DIR.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(path.stem, path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Find classes with name + description + run
                for attr_name in dir(module):
                    cls = getattr(module, attr_name)
                    if (
                        isinstance(cls, type)
                        and hasattr(cls, "name")
                        and hasattr(cls, "description")
                        and hasattr(cls, "run")
                        and cls.name  # not empty
                    ):
                        instance = cls()
                        self._plugins.append(instance)
                        logger.info("Plugin loaded: %s (%s)", cls.name, path.name)
                        count += 1
            except Exception as exc:
                logger.warning("Plugin load failed for %s: %s", path.name, exc)
        return count

    def dispatch(self, query: str) -> Optional[str]:
        """
        Try each plugin's name/description keyword match.
        Returns first match result or None.
        """
        q = query.lower().strip()
        for plugin in self._plugins:
            # Match by plugin name or keywords from description
            keywords = re.findall(r"\b\w{3,}\b", plugin.name + " " + plugin.description)
            if any(kw.lower() in q for kw in keywords):
                try:
                    result = plugin.run(query)
                    if result:
                        logger.info("Plugin %s handled: %r", plugin.name, query[:60])
                        return result
                except Exception as exc:
                    logger.warning("Plugin %s failed: %s", plugin.name, exc)
        return None

    def list_plugins(self) -> str:
        if not self._plugins:
            return (
                f"No plugins loaded, Sir. "
                f"Drop Python files into {PLUGINS_DIR} to add skills."
            )
        lines = [f"Loaded {len(self._plugins)} plugin(s), Sir:"]
        for p in self._plugins:
            lines.append(f"  • {p.name}: {p.description[:60]}")
        return "\n".join(lines)

    def reload(self) -> str:
        n = self.load()
        return f"Plugins reloaded. {n} plugin(s) active, Sir."
