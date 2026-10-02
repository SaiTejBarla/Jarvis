"""
agents/monitor.py — Proactive background monitor agent (Phase 7).

Watches system state in the background and proactively alerts JARVIS
when something noteworthy happens:

  - Low battery (< 15%)
  - High CPU usage (> 90% for 30s)
  - High RAM usage (> 90%)
  - Scheduled task reminders (handled separately by scheduler)
  - Daily briefing at configured time

The monitor calls an on_alert(message) callback, which the voice loop
or tray uses to speak/notify the alert.
"""

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Poll interval in seconds
_POLL_INTERVAL = 30


class MonitorAgent:
    """
    Background watchdog that proactively fires alerts.
    Instantiate and call start(). Runs on a daemon thread.
    """

    def __init__(self, on_alert: Optional[Callable[[str], None]] = None) -> None:
        self._on_alert = on_alert
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._alerted: set = set()   # track which alerts already fired this session

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="monitor")
        self._thread.start()
        logger.info("Monitor agent started.")

    def stop(self) -> None:
        self._running = False

    def set_callback(self, cb: Callable[[str], None]) -> None:
        self._on_alert = cb

    # ── Internal ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            try:
                self._check_battery()
                self._check_cpu()
                self._check_ram()
            except Exception as exc:
                logger.debug("Monitor check failed: %s", exc)
            time.sleep(_POLL_INTERVAL)

    def _alert(self, key: str, message: str) -> None:
        """Fire alert once per session per key."""
        if key in self._alerted:
            return
        self._alerted.add(key)
        logger.info("Monitor alert: %s", message)
        print(f"\n\033[93m[MONITOR]\033[0m  {message}")
        if self._on_alert:
            try:
                self._on_alert(message)
            except Exception as exc:
                logger.warning("Monitor callback failed: %s", exc)

    def _reset_alert(self, key: str) -> None:
        self._alerted.discard(key)

    def _check_battery(self) -> None:
        try:
            import psutil  # type: ignore
            batt = psutil.sensors_battery()
            if batt is None:
                return
            pct = int(batt.percent)
            if not batt.power_plugged:
                if pct <= 5:
                    self._alert("battery_critical",
                                f"Warning, Sir — battery critically low at {pct}%. Please plug in immediately.")
                elif pct <= 15:
                    self._alert("battery_low",
                                f"Sir, battery is at {pct}%. I recommend plugging in soon.")
                else:
                    # Reset so alert can fire again if it drops further
                    if pct > 20:
                        self._reset_alert("battery_low")
                    if pct > 10:
                        self._reset_alert("battery_critical")
        except ImportError:
            pass

    def _check_cpu(self) -> None:
        try:
            import psutil  # type: ignore
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 90:
                self._alert("cpu_high",
                            f"Sir, CPU usage is at {int(cpu)}%. Your system is under heavy load.")
            elif cpu < 70:
                self._reset_alert("cpu_high")
        except ImportError:
            pass

    def _check_ram(self) -> None:
        try:
            import psutil  # type: ignore
            ram = psutil.virtual_memory()
            pct = int(ram.percent)
            if pct > 90:
                self._alert("ram_high",
                            f"Sir, RAM usage is at {pct}%. You may want to close some applications.")
            elif pct < 80:
                self._reset_alert("ram_high")
        except ImportError:
            pass
