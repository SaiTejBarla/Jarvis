"""
tools/browser.py — Browser automation for JARVIS using Playwright.

Supports:
  - Opening URLs
  - Web scraping / reading page content
  - Clicking elements and filling forms
  - Taking web screenshots

Requires:
    pip install playwright
    playwright install chromium

Commands:
    "open google.com"
    "go to https://news.ycombinator.com"
    "scrape https://example.com"
    "read page https://example.com"
"""

import logging
import re
from typing import Optional
from .base import BaseTool

logger = logging.getLogger(__name__)

# Max chars to return from a scraped page
_MAX_SCRAPE_CHARS = 3000


class BrowserTool(BaseTool):
    name = "browser"
    description = (
        "Open URLs, read web pages, and interact with websites. "
        "e.g. 'open google.com', 'scrape https://example.com', 'read page reddit.com'."
    )

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None

    def run(self, query: str) -> str:
        q = query.lower().strip()

        # Extract URL from query
        url = self._extract_url(query)

        # Scrape / read page content
        if re.search(r"\b(scrape|read page|read the page|get content|fetch|browse)\b", q):
            if not url:
                return "Please provide a URL, Sir. e.g. 'scrape https://example.com'"
            return self._scrape(url)

        # Take a web screenshot
        if re.search(r"\b(screenshot|capture|snap)\b", q) and url:
            return self._web_screenshot(url)

        # Default: just open the URL
        if url:
            return self._open(url)

        return "Please provide a URL, Sir."

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract a URL from the query text."""
        # Full URL with scheme
        m = re.search(r"https?://\S+", text)
        if m:
            return m.group(0).rstrip(".,;)")

        # Domain-like pattern (e.g. "google.com", "reddit.com/r/python")
        m = re.search(r"\b([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/\S*)?)\b", text)
        if m:
            return "https://" + m.group(1).rstrip(".,;)")

        return None

    def _ensure_browser(self) -> bool:
        """Lazy-init Playwright browser. Returns False if unavailable."""
        if self._browser is not None:
            return True
        try:
            from playwright.sync_api import sync_playwright  # type: ignore
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            logger.info("Playwright browser launched.")
            return True
        except ImportError:
            logger.warning("Playwright not installed. Run: pip install playwright && playwright install chromium")
            return False
        except Exception as exc:
            logger.warning("Playwright launch failed: %s", exc)
            return False

    def _open(self, url: str) -> str:
        """Open a URL in the default system browser (non-headless)."""
        import subprocess, sys
        try:
            if sys.platform == "win32":
                subprocess.Popen(["start", url], shell=True)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", url])
            else:
                subprocess.Popen(["xdg-open", url])
            return f"Opening {url} in your browser, Sir."
        except Exception as exc:
            return f"Could not open browser: {exc}"

    def _scrape(self, url: str) -> str:
        """Scrape visible text from a web page using Playwright."""
        if not self._ensure_browser():
            return (
                "Browser automation unavailable. "
                "Run: pip install playwright && playwright install chromium"
            )
        try:
            page = self._browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (JARVIS browser)"})
            page.goto(url, timeout=15000, wait_until="domcontentloaded")

            # Extract visible text
            text = page.evaluate("""() => {
                const body = document.body;
                if (!body) return '';
                // Remove scripts and styles
                const scripts = body.querySelectorAll('script, style, nav, footer, header');
                scripts.forEach(s => s.remove());
                return body.innerText;
            }""")
            page.close()

            if not text:
                return f"I couldn't read any text from {url}, Sir."

            # Let Gemini summarise the page content
            from core.orchestrator import gemini_summarise
            summary = gemini_summarise(
                text,
                instruction=f"Summarise the key information from this web page ({url}) in 3-4 sentences."
            )
            return f"Summary of {url}:\n\n{summary}"
        except Exception as exc:
            logger.warning("Scrape failed for %s: %s", url, exc)
            return f"Could not read {url}: {exc}"

    def _web_screenshot(self, url: str) -> str:
        """Take a screenshot of a web page."""
        if not self._ensure_browser():
            return "Browser automation unavailable."
        try:
            from datetime import datetime
            import config
            shots_dir = config.DATA_DIR / "screenshots"
            shots_dir.mkdir(parents=True, exist_ok=True)
            filename = shots_dir / f"web_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            page = self._browser.new_page()
            page.goto(url, timeout=15000, wait_until="domcontentloaded")
            page.screenshot(path=str(filename), full_page=False)
            page.close()

            return f"Web screenshot saved: {filename.name}, Sir."
        except Exception as exc:
            return f"Web screenshot failed: {exc}"

    def close(self) -> None:
        """Clean up Playwright resources."""
        try:
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
