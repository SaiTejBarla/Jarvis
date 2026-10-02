"""
tools/screenshot.py — Screenshot capture + OCR for JARVIS.

Takes a screenshot and reads text from it using pytesseract (free, local).
Answers questions about what's currently on screen.

Requirements:
    pip install Pillow pytesseract pyautogui
    Install Tesseract-OCR: https://github.com/UB-Mannheim/tesseract/wiki
    (Windows installer — free, open source)

Commands:
    "take a screenshot"
    "what's on my screen"
    "read the screen"
    "ocr my screen"
"""

import logging
import re
from pathlib import Path
from .base import BaseTool
import config

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR = config.DATA_DIR / "screenshots"


class ScreenshotTool(BaseTool):
    name = "screenshot"
    description = (
        "Take a screenshot and/or read text from the screen using OCR. "
        "e.g. 'what's on my screen', 'take a screenshot', 'read the screen'."
    )

    def __init__(self) -> None:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def run(self, query: str) -> str:
        q = query.lower().strip()
        do_ocr = re.search(r"\b(read|ocr|text|what.?s on|whats on|see)\b", q) is not None

        # Take screenshot
        img_path = self._capture()
        if not img_path:
            return "I couldn't take a screenshot. Please install pyautogui: pip install pyautogui Pillow"

        if do_ocr:
            text = self._ocr(img_path)
            if text:
                return f"I can see this text on your screen:\n\n{text[:800]}"
            return (
                "Screenshot taken but I couldn't read any text. "
                "Tesseract OCR may not be installed. "
                "See: https://github.com/UB-Mannheim/tesseract/wiki"
            )

        return f"Screenshot saved to: {img_path}"

    def _capture(self):
        try:
            import pyautogui  # type: ignore
            from datetime import datetime
            filename = SCREENSHOTS_DIR / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            img = pyautogui.screenshot()
            img.save(str(filename))
            logger.info("Screenshot saved: %s", filename.name)
            return filename
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("Screenshot failed: %s", exc)
            return None

    def _ocr(self, img_path: Path) -> str:
        try:
            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
            img = Image.open(img_path)
            text = pytesseract.image_to_string(img)
            return text.strip()
        except ImportError:
            return ""
        except Exception as exc:
            logger.warning("OCR failed: %s", exc)
            return ""
