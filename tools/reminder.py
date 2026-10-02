"""
tools/reminder.py — Proactive reminder system for JARVIS.

Parses natural language like "remind me in 10 minutes to call mom"
and fires a spoken + printed reminder using a background thread timer.
"""

import logging
import re
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Callback type: called when a reminder fires with the reminder text
ReminderCallback = Callable[[str], None]


def _parse_duration(text: str) -> Optional[int]:
    """
    Parse a natural language duration string and return seconds.
    e.g. "10 minutes" → 600, "1 hour" → 3600, "30 seconds" → 30
    Returns None if parsing fails.
    """
    text = text.lower()
    patterns = [
        (r"(\d+)\s*hour", 3600),
        (r"(\d+)\s*hr", 3600),
        (r"(\d+)\s*minute", 60),
        (r"(\d+)\s*min", 60),
        (r"(\d+)\s*second", 1),
        (r"(\d+)\s*sec", 1),
    ]
    for pattern, multiplier in patterns:
        m = re.search(pattern, text)
        if m:
            return int(m.group(1)) * multiplier
    return None


class ReminderTool:
    """
    Parses reminder requests and schedules them on background threads.
    The on_fire callback is called with the reminder message when the timer fires.
    """

    name = "reminder"
    description = (
        "Set a reminder. Query format: 'remind me in X minutes/hours to <task>'."
    )

    def __init__(self, on_fire: Optional[ReminderCallback] = None) -> None:
        self._on_fire = on_fire
        self._timers: list[threading.Timer] = []

    def run(self, query: str) -> str:
        q = query.lower()

        # Extract duration
        seconds = _parse_duration(q)
        if seconds is None:
            return (
                "I couldn't understand the time. "
                "Try: 'remind me in 10 minutes to call mom'."
            )

        # Extract the task after "to"
        task_match = re.search(r"\bto\b(.+)$", query, re.IGNORECASE)
        task = task_match.group(1).strip() if task_match else "do that"

        fire_at = datetime.now() + timedelta(seconds=seconds)
        human_time = fire_at.strftime("%I:%M %p")

        timer = threading.Timer(seconds, self._fire, args=(task,))
        timer.daemon = True
        timer.start()
        self._timers.append(timer)

        mins = seconds // 60
        secs = seconds % 60
        duration_str = (
            f"{mins} minute{'s' if mins != 1 else ''}" if mins
            else f"{secs} second{'s' if secs != 1 else ''}"
        )

        logger.info("Reminder set: '%s' in %s (at %s)", task, duration_str, human_time)
        return f"Reminder set. I'll remind you to {task} in {duration_str}, Sir."

    def _fire(self, task: str) -> None:
        message = f"Reminder, Sir: {task}."
        logger.info("Reminder fired: %s", task)
        print(f"\n\033[93m[REMINDER]\033[0m  {message}")
        if self._on_fire:
            try:
                self._on_fire(message)
            except Exception as exc:
                logger.warning("Reminder callback failed: %s", exc)

    def cancel_all(self) -> None:
        """Cancel all pending reminders."""
        for t in self._timers:
            t.cancel()
        self._timers.clear()
