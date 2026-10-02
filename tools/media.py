"""
tools/media.py — Media / music control via keyboard shortcuts.

Controls media playback (play/pause, skip, volume) using system-level
keyboard shortcuts. Works with Spotify, YouTube, VLC, Windows Media Player
— anything that responds to media keys.

No API key required — uses the keyboard module or pyautogui.
"""

import logging
import subprocess
import sys
from .base import BaseTool

logger = logging.getLogger(__name__)


def _send_media_key(key: str) -> None:
    """Send a virtual media key on Windows using PowerShell."""
    # VK codes: 0xB3=play/pause, 0xB0=next, 0xB1=prev, 0xAD=mute, 0xAF=vol up, 0xAE=vol down
    vk_map = {
        "play_pause": 0xB3,
        "next": 0xB0,
        "prev": 0xB1,
        "mute": 0xAD,
        "vol_up": 0xAF,
        "vol_down": 0xAE,
        "stop": 0xB2,
    }
    vk = vk_map.get(key)
    if vk is None:
        return
    script = (
        f"$wsh = New-Object -ComObject WScript.Shell; "
        f"$wsh.SendKeys([char]{vk})"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
    )


class MediaTool(BaseTool):
    name = "media"
    description = (
        "Control media playback: play, pause, next track, previous track, stop. "
        "Works with Spotify, YouTube, VLC, etc."
    )

    def run(self, query: str) -> str:
        q = query.lower().strip()

        if any(w in q for w in ["play", "resume", "unpause"]):
            _send_media_key("play_pause")
            return "Playing, Sir."

        if any(w in q for w in ["pause"]):
            _send_media_key("play_pause")
            return "Paused, Sir."

        if any(w in q for w in ["next", "skip", "forward"]):
            _send_media_key("next")
            return "Skipping to next track, Sir."

        if any(w in q for w in ["previous", "prev", "back", "last"]):
            _send_media_key("prev")
            return "Going to previous track, Sir."

        if any(w in q for w in ["stop"]):
            _send_media_key("stop")
            return "Stopping playback, Sir."

        if any(w in q for w in ["mute"]):
            _send_media_key("mute")
            return "Media muted, Sir."

        return "I didn't understand that media command, Sir."
