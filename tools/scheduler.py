"""
tools/scheduler.py — Daily scheduled task runner for JARVIS.

Runs recurring tasks at fixed times every day (e.g. morning briefing at 8am).
Schedules are persisted in data/schedules.json and survive restarts.

Usage:
    "schedule daily briefing at 8am"
    "add daily reminder at 9:00 to drink water"
    "show my schedules"
    "cancel schedule 1"
"""

import json
import logging
import re
import threading
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Callable, Optional

import config

logger = logging.getLogger(__name__)

SCHEDULES_FILE = config.DATA_DIR / "schedules.json"


class ScheduledTask:
    def __init__(self, task_id: int, hour: int, minute: int, message: str) -> None:
        self.task_id = task_id
        self.hour = hour
        self.minute = minute
        self.message = message
        self.last_run_date: Optional[str] = None  # "YYYY-MM-DD"

    def to_dict(self) -> dict:
        return {
            "id": self.task_id,
            "hour": self.hour,
            "minute": self.minute,
            "message": self.message,
            "last_run_date": self.last_run_date,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ScheduledTask":
        t = cls(d["id"], d["hour"], d["minute"], d["message"])
        t.last_run_date = d.get("last_run_date")
        return t

    def time_str(self) -> str:
        suffix = "AM" if self.hour < 12 else "PM"
        h = self.hour % 12 or 12
        return f"{h}:{self.minute:02d} {suffix}"


class SchedulerTool:
    """
    Manages daily recurring scheduled tasks.
    The on_fire callback is called with the task message when it's time.
    """

    name = "scheduler"
    description = (
        "Schedule a daily recurring task. "
        "e.g. 'schedule daily briefing at 8am', 'show my schedules', 'cancel schedule 1'."
    )

    def __init__(self, on_fire: Optional[Callable[[str], None]] = None) -> None:
        self._on_fire = on_fire
        self._tasks: list[ScheduledTask] = []
        self._lock = threading.Lock()
        self._load()
        self._start_ticker()

    def run(self, query: str) -> str:
        q = query.lower().strip()

        # Show schedules
        if re.search(r"\b(show|list|view|my)\b.*schedule", q):
            return self._list_schedules()

        # Cancel a schedule
        m = re.search(r"cancel\s+schedule\s+(\d+)", q)
        if m:
            return self._cancel(int(m.group(1)))

        # Add a schedule
        hour, minute = self._parse_time(q)
        if hour is None:
            return "I couldn't parse the time. Try: 'schedule daily briefing at 8am'."

        task_m = re.search(
            r"(?:schedule|add)\s+(?:daily\s+)?(.+?)\s+at\s+\d", query, re.IGNORECASE
        )
        message = task_m.group(1).strip() if task_m else query.strip()

        return self._add(hour, minute, message)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _add(self, hour: int, minute: int, message: str) -> str:
        with self._lock:
            task_id = max((t.task_id for t in self._tasks), default=0) + 1
            task = ScheduledTask(task_id, hour, minute, message)
            self._tasks.append(task)
            self._save()
        h = hour % 12 or 12
        suffix = "AM" if hour < 12 else "PM"
        return f"Daily schedule set: '{message}' at {h}:{minute:02d} {suffix}, Sir."

    def _cancel(self, task_id: int) -> str:
        with self._lock:
            before = len(self._tasks)
            self._tasks = [t for t in self._tasks if t.task_id != task_id]
            if len(self._tasks) == before:
                return f"Schedule {task_id} not found, Sir."
            self._save()
        return f"Schedule {task_id} cancelled, Sir."

    def _list_schedules(self) -> str:
        with self._lock:
            tasks = list(self._tasks)
        if not tasks:
            return "You have no scheduled tasks, Sir."
        lines = [f"You have {len(tasks)} scheduled task(s), Sir:"]
        for t in tasks:
            lines.append(f"  {t.task_id}. {t.message} — daily at {t.time_str()}")
        return "\n".join(lines)

    def _parse_time(self, text: str) -> tuple[Optional[int], int]:
        # "8am", "8:30am", "14:00", "2pm"
        m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
        if not m:
            return None, 0
        hour = int(m.group(1))
        minute = int(m.group(2)) if m.group(2) else 0
        meridiem = m.group(3)
        if meridiem == "pm" and hour < 12:
            hour += 12
        elif meridiem == "am" and hour == 12:
            hour = 0
        return hour, minute

    def _tick(self) -> None:
        """Called every 30 seconds — check if any task should fire."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        with self._lock:
            for task in self._tasks:
                if (
                    now.hour == task.hour
                    and now.minute == task.minute
                    and task.last_run_date != today
                ):
                    task.last_run_date = today
                    self._save()
                    msg = f"Scheduled task: {task.message}."
                    logger.info("Scheduler firing: %s", msg)
                    print(f"\n\033[93m[SCHEDULE]\033[0m  {msg}")
                    if self._on_fire:
                        try:
                            self._on_fire(msg)
                        except Exception as exc:
                            logger.warning("Scheduler callback failed: %s", exc)

        # Reschedule
        t = threading.Timer(30.0, self._tick)
        t.daemon = True
        t.start()

    def _start_ticker(self) -> None:
        t = threading.Timer(10.0, self._tick)
        t.daemon = True
        t.start()

    def _save(self) -> None:
        try:
            config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            SCHEDULES_FILE.write_text(
                json.dumps([t.to_dict() for t in self._tasks], indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Scheduler save failed: %s", exc)

    def _load(self) -> None:
        if not SCHEDULES_FILE.exists():
            return
        try:
            data = json.loads(SCHEDULES_FILE.read_text(encoding="utf-8"))
            self._tasks = [ScheduledTask.from_dict(d) for d in data]
            logger.info("Scheduler loaded %d task(s).", len(self._tasks))
        except Exception as exc:
            logger.warning("Scheduler load failed: %s", exc)
