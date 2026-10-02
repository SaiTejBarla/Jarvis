"""
tools/news.py — News briefing via RSS feeds (no API key required).

Fetches top headlines from free RSS feeds and formats them as a briefing.
Default sources: BBC, Reuters, Google News.
"""

import logging
import re
from datetime import datetime
from typing import Optional
from .base import BaseTool

logger = logging.getLogger(__name__)

_DEFAULT_FEEDS = [
    ("BBC News", "http://feeds.bbci.co.uk/news/rss.xml"),
    ("Reuters", "https://feeds.reuters.com/reuters/topNews"),
    ("Google News", "https://news.google.com/rss"),
]


class NewsTool(BaseTool):
    name = "news"
    description = "Get the latest news headlines. Optionally filter by topic."

    def run(self, query: str) -> str:
        topic = query.strip().lower()
        headlines = self._fetch_headlines(topic)
        if not headlines:
            return "I couldn't fetch the news right now, Sir. Please try again later."

        raw = "\n".join(f"{title} ({source})" for source, title, _ in headlines[:5])
        from core.orchestrator import gemini_summarise
        summary = gemini_summarise(
            raw,
            instruction="Give a brief spoken news briefing based on these headlines in 3-4 sentences. Start with 'Here are today's top stories, Sir:'"
        )
        return summary

    def _fetch_headlines(self, topic: str) -> list[tuple]:
        """Return list of (source, title, link) tuples."""
        try:
            import xml.etree.ElementTree as ET
            import urllib.request
        except ImportError:
            return []

        all_items = []
        for source_name, url in _DEFAULT_FEEDS:
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "JARVIS/4.0"},
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    content = resp.read()
                root = ET.fromstring(content)
                # Handle both RSS and Atom
                items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
                for item in items[:10]:
                    title_el = item.find("title")
                    link_el = item.find("link")
                    if title_el is None:
                        continue
                    title = title_el.text or ""
                    link = (link_el.text or "") if link_el is not None else ""
                    # Filter by topic if provided
                    if topic and topic not in title.lower():
                        continue
                    all_items.append((source_name, title.strip(), link))
                    if len(all_items) >= 5:
                        break
            except Exception as exc:
                logger.debug("RSS feed %s failed: %s", source_name, exc)
                continue
            if len(all_items) >= 5:
                break

        return all_items
