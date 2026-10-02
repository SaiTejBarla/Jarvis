"""
tools/system.py — System control tools for JARVIS.

Supports:
  - Open applications by name
  - Control system volume (Windows)
  - Get battery status
  - Lock the screen
  - Shutdown / restart (with confirmation flag)
"""

import logging
import os
import subprocess
import sys
from .base import BaseTool

logger = logging.getLogger(__name__)

# Map of common app names → executable or command
_APP_MAP = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "browser": "start chrome",
    "chrome": "start chrome",
    "edge": "start msedge",
    "explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "spotify": "spotify",
    "vscode": "code",
    "vs code": "code",
    "cmd": "start cmd",
    "terminal": "start cmd",
    "paint": "mspaint.exe",
    "word": "start winword",
    "excel": "start excel",
}


class OpenAppTool(BaseTool):
    name = "open_app"
    description = "Open an application on the computer. Query should be the app name."

    def run(self, query: str) -> str:
        app = query.lower().strip()
        cmd = _APP_MAP.get(app)

        if cmd is None:
            # Try to run it directly as a command
            cmd = app

        try:
            if sys.platform == "win32":
                if cmd.startswith("start "):
                    subprocess.Popen(cmd, shell=True)
                else:
                    subprocess.Popen(cmd, shell=True,
                                     creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(cmd, shell=True)
            return f"Opening {query}, Sir."
        except Exception as exc:
            logger.warning("Open app failed for %r: %s", query, exc)
            return f"I couldn't open '{query}'. Please check the app name."


class VolumeTool(BaseTool):
    name = "volume"
    description = (
        "Control system volume. Query: 'mute', 'unmute', 'up', 'down', "
        "or a number 0-100."
    )

    def run(self, query: str) -> str:
        q = query.lower().strip()
        try:
            from ctypes import cast, POINTER  # type: ignore
            from comtypes import CLSCTX_ALL  # type: ignore
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))

            if q == "mute":
                volume.SetMute(1, None)
                return "System muted, Sir."
            if q == "unmute":
                volume.SetMute(0, None)
                return "System unmuted, Sir."
            if q == "up":
                cur = volume.GetMasterVolumeLevelScalar()
                volume.SetMasterVolumeLevelScalar(min(1.0, cur + 0.1), None)
                return f"Volume increased to {int(min(1.0, cur + 0.1) * 100)}%."
            if q == "down":
                cur = volume.GetMasterVolumeLevelScalar()
                volume.SetMasterVolumeLevelScalar(max(0.0, cur - 0.1), None)
                return f"Volume decreased to {int(max(0.0, cur - 0.1) * 100)}%."
            # Try numeric
            try:
                level = int(q.rstrip("%")) / 100.0
                level = max(0.0, min(1.0, level))
                volume.SetMasterVolumeLevelScalar(level, None)
                return f"Volume set to {int(level * 100)}%, Sir."
            except ValueError:
                pass
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("Volume control failed: %s", exc)

        # Fallback — nircmd (if installed) or PowerShell
        try:
            if q == "mute":
                subprocess.run(
                    ["powershell", "-c",
                     "$obj = New-Object -com WScript.Shell; $obj.SendKeys([char]173)"],
                    shell=True, capture_output=True
                )
                return "Muted, Sir."
        except Exception:
            pass

        return "Volume control is unavailable on this system."


class BatteryTool(BaseTool):
    name = "battery"
    description = "Check the current battery level and charging status."

    def run(self, query: str) -> str:
        try:
            import psutil  # type: ignore
            batt = psutil.sensors_battery()
            if batt is None:
                return "No battery detected — this appears to be a desktop, Sir."
            charging = "charging" if batt.power_plugged else "on battery"
            return (
                f"Battery is at {int(batt.percent)}% and {charging}, Sir."
            )
        except ImportError:
            return "Battery status unavailable. Run: pip install psutil"
        except Exception as exc:
            return f"Could not read battery status: {exc}"


class LockScreenTool(BaseTool):
    name = "lock_screen"
    description = "Lock the computer screen."

    def run(self, query: str) -> str:
        try:
            if sys.platform == "win32":
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return "Locking the screen, Sir."
            else:
                subprocess.run(["gnome-screensaver-command", "-l"])
                return "Screen locked, Sir."
        except Exception as exc:
            logger.warning("Lock screen failed: %s", exc)
            return "Could not lock the screen."
