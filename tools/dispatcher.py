"""
tools/dispatcher.py — Intent-based tool dispatcher for JARVIS.

Routes a user query to the right tool using keyword/pattern matching.
Falls back to the LLM if no tool matches.

Phase 5: Added clipboard, screenshot, filesystem, code runner, scheduler, exporter.
"""

import logging
import re
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ToolDispatcher:
    """
    Keyword-based intent router.
    Returns a tool result string, or None if the query should go to the LLM.
    """

    def __init__(self, tts_callback: Optional[Callable[[str], None]] = None) -> None:
        from tools.search import WebSearchTool
        from tools.weather import WeatherTool
        from tools.datetime_tool import DateTimeTool
        from tools.calculator import CalculatorTool
        from tools.system import OpenAppTool, VolumeTool, BatteryTool, LockScreenTool
        from tools.reminder import ReminderTool
        from tools.news import NewsTool
        from tools.notes import NotesTool
        from tools.media import MediaTool
        from tools.clipboard import ClipboardTool
        from tools.screenshot import ScreenshotTool
        from tools.filesystem import FileSystemTool
        from tools.code_runner import CodeRunnerTool
        from tools.scheduler import SchedulerTool
        from tools.exporter import ExporterTool
        from tools.browser import BrowserTool
        from tools.home_assistant import HomeAssistantTool
        from tools.plugins import PluginRegistry

        self._datetime = DateTimeTool()
        self._weather = WeatherTool()
        self._search = WebSearchTool()
        self._calc = CalculatorTool()
        self._open_app = OpenAppTool()
        self._volume = VolumeTool()
        self._battery = BatteryTool()
        self._lock = LockScreenTool()
        self._reminder = ReminderTool(on_fire=tts_callback)
        self._news = NewsTool()
        self._notes = NotesTool()
        self._media = MediaTool()
        self._clipboard = ClipboardTool()
        self._screenshot = ScreenshotTool()
        self._filesystem = FileSystemTool()
        self._code_runner = CodeRunnerTool()
        self._scheduler = SchedulerTool(on_fire=tts_callback)
        self._exporter = ExporterTool()
        self._browser = BrowserTool()
        self._ha = HomeAssistantTool()
        self._plugins = PluginRegistry()
        self._plugins.load()

        # Multi-step planner — injected after construction to avoid circular import
        self._planner = None

    def get_planner(self):
        if self._planner is None:
            from agents.planner import TaskPlanner
            self._planner = TaskPlanner(self)
        return self._planner

    def dispatch(self, query: str) -> Optional[str]:
        """
        Try to match query to a tool. Returns tool result or None.
        """
        q = query.lower().strip()

        # ── Multi-step planner ────────────────────────────────────────────────
        from agents.planner import is_multi_step
        if is_multi_step(query):
            result = self.get_planner().run(query)
            if result:
                return result

        # ── Time / Date ───────────────────────────────────────────────────────
        if re.search(r"\b(time|date|day|today|year|month)\b", q):
            if not re.search(r"\b(weather|temperature|forecast)\b", q):
                return self._datetime.run(query)

        # ── Weather ───────────────────────────────────────────────────────────
        if re.search(r"\b(weather|temperature|forecast|hot|cold|raining|sunny)\b", q):
            city = self._extract_city(q)
            return self._weather.run(city)

        # ── Calculator ────────────────────────────────────────────────────────
        if re.search(
            r"\b(calculate|compute|evaluate|how much is|what is\s+[\d(])",
            q
        ) or re.search(r"[\d]+\s*[\+\-\*\/\^]\s*[\d]+", q):
            return self._calc.run(query)

        # ── Reminder ──────────────────────────────────────────────────────────
        if re.search(r"\b(remind|reminder|alert|notify)\b", q):
            return self._reminder.run(query)

        # ── Notes ─────────────────────────────────────────────────────────────
        if re.search(r"\b(note|notes)\b", q):
            return self._notes.run(query)

        # ── News ──────────────────────────────────────────────────────────────
        if re.search(r"\b(news|headlines|briefing|latest news)\b", q):
            topic = re.sub(
                r"\b(news|headlines|briefing|latest|about|on|the)\b", "", q
            ).strip()
            return self._news.run(topic)

        # ── Media control ─────────────────────────────────────────────────────
        if re.search(
            r"\b(play|pause|next track|previous track|skip|stop music|"
            r"next song|prev song|resume music)\b", q
        ):
            return self._media.run(query)

        # ── Open app ──────────────────────────────────────────────────────────
        if re.search(r"\b(open|launch|start)\b", q):
            app = re.sub(r"\b(open|launch|start)\b", "", q).strip()
            return self._open_app.run(app)

        # ── Volume ────────────────────────────────────────────────────────────
        if re.search(r"\b(volume|mute|unmute|louder|quieter)\b", q):
            if "unmute" in q:
                return self._volume.run("unmute")
            if "mute" in q:
                return self._volume.run("mute")
            if re.search(r"\b(up|louder|increase|raise)\b", q):
                return self._volume.run("up")
            if re.search(r"\b(down|quieter|decrease|lower)\b", q):
                return self._volume.run("down")
            m = re.search(r"(\d{1,3})\s*%?", q)
            if m:
                return self._volume.run(m.group(1))

        # ── Battery ───────────────────────────────────────────────────────────
        if re.search(r"\b(battery|charge|charging|power level)\b", q):
            return self._battery.run(query)

        # ── Lock screen ───────────────────────────────────────────────────────
        if re.search(r"\b(lock screen|lock computer|lock pc|lock the screen)\b", q):
            return self._lock.run(query)

        # ── Clipboard ─────────────────────────────────────────────────────────
        if re.search(r"\b(clipboard|copy.+to clipboard|read clipboard)\b", q):
            return self._clipboard.run(query)

        # ── Screenshot / OCR ──────────────────────────────────────────────────
        if re.search(r"\b(screenshot|whats on.+screen|read.+screen|ocr)\b", q):
            return self._screenshot.run(query)

        # ── File system ───────────────────────────────────────────────────────
        if re.search(r"\b(list files|show files|files in|read file|open file|find files|summarise file)\b", q):
            return self._filesystem.run(query)

        # ── Code runner ───────────────────────────────────────────────────────
        if re.search(r"\b(run python|execute|run code)\b", q) or q.startswith("python:"):
            return self._code_runner.run(query)

        # ── Scheduler ─────────────────────────────────────────────────────────
        if re.search(r"\b(schedule daily|daily.+at \d|show.*schedules|cancel schedule)\b", q):
            return self._scheduler.run(query)

        # ── Export conversation ────────────────────────────────────────────────
        if re.search(r"\b(export|save.+chat|save.+conversation)\b", q):
            return self._exporter.run(query)

        # ── Persona switch ────────────────────────────────────────────────────
        if re.search(r"\b(switch|change|use|activate)\b.{0,15}\b(mode|persona|jarvis|assistant|tutor|coder|brief)\b", q):
            m = re.search(r"\b(jarvis|assistant|tutor|coder|brief)\b", q)
            if m:
                from core.persona import set_persona
                return set_persona(m.group(1))

        if re.search(r"\b(list|show|what).{0,10}(modes|personas)\b", q):
            from core.persona import list_personas
            return list_personas()

        # ── Browser automation ────────────────────────────────────────────────
        if re.search(r"\b(open|go to|browse|scrape|read page|web screenshot)\b", q) and \
                re.search(r"[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", q):
            return self._browser.run(query)

        # ── Auth: show audit log ───────────────────────────────────────────────
        if re.search(r"\b(audit|audit log|action log|show log)\b", q):
            try:
                from core.audit import AuditLog
                entries = AuditLog().recent(10)
                if not entries:
                    return "No audit entries yet, Sir."
                lines = [f"Last {len(entries)} audit entries:"]
                for e in entries:
                    lines.append(f"  [{e['ts']}] {e['type']}: {e.get('query') or e.get('action') or e.get('input','')[:60]}")
                return "\n".join(lines)
            except Exception as exc:
                return f"Could not read audit log: {exc}"

        # ── Auth: revoke authorization ─────────────────────────────────────────
        if re.search(r"\b(revoke|lock|deauthorize|cancel auth)\b", q):
            try:
                from core.auth import AuthGate
                AuthGate().revoke()
                return "Authorization revoked, Sir."
            except Exception:
                pass

        # ── Home Assistant ────────────────────────────────────────────────────
        if re.search(
            r"\b(turn on|turn off|toggle|thermostat|smart home|home assistant|"
            r"the lights|the fan|the heater|the ac)\b", q
        ):
            return self._ha.run(query)

        # ── Plugins ───────────────────────────────────────────────────────────
        plugin_result = self._plugins.dispatch(query)
        if plugin_result:
            return plugin_result

        if re.search(r"\b(list plugins|show plugins|reload plugins)\b", q):
            if "reload" in q:
                return self._plugins.reload()
            return self._plugins.list_plugins()

        # ── Web search ────────────────────────────────────────────────────────
        if re.search(
            r"\b(search|look up|find|who is|when did|where is|latest)\b", q
        ):
            return self._search.run(query)

        return None  # Let the LLM handle it

    def _extract_city(self, q: str) -> str:
        m = re.search(r"(?:weather|forecast|temperature)\s+(?:in|for|at)\s+([a-z\s]+)", q)
        if m:
            return m.group(1).strip()
        m = re.search(r"([a-z\s]+)\s+(?:weather|forecast|temperature)", q)
        if m:
            return m.group(1).strip()
        city = re.sub(
            r"\b(weather|temperature|forecast|hot|cold|raining|sunny|what|is|the|in|for|at)\b",
            "", q
        ).strip()
        return city or "London"
