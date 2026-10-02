"""
tools/search.py — Web search via DuckDuckGo (no API key required).

Uses the duckduckgo-search package (free, no account needed).
Gemini summarises the raw results into a concise answer (if key is set).
"""

import logging
from .base import BaseTool

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web for current information, news, or facts."

    def run(self, query: str) -> str:
        try:
            from duckduckgo_search import DDGS  # type: ignore
        except ImportError:
            return "Web search is unavailable. Run: pip install duckduckgo-search"

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))

            if not results:
                return f"No results found for: {query}"

            # Combine raw results and let Gemini summarise into a proper answer
            raw = "\n".join(
                f"{r.get('title', '')}: {r.get('body', '')}" for r in results
            )
            from core.orchestrator import gemini_summarise
            return gemini_summarise(
                raw,
                instruction=f"Based on these search results, answer this query concisely in 2-3 sentences: '{query}'"
            )
        except Exception as exc:
            logger.warning("Web search failed: %s", exc)
            return f"Web search failed: {exc}"
