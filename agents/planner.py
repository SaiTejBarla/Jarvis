"""
agents/planner.py — Autonomous multi-step task planner for JARVIS.

Given a complex goal, breaks it into steps, executes tools in sequence,
and synthesises a final answer from all intermediate results.

Example:
    "Research the weather in Tokyo and remind me to pack an umbrella in 1 hour"
    → Step 1: weather("Tokyo")
    → Step 2: reminder("pack an umbrella", 3600)
    → Final: combined summary spoken back
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Conjunctions that suggest multi-step intent
_MULTI_STEP_PATTERNS = [
    r"\band\s+(?:also\s+)?(?:then\s+)?(?:remind|open|search|find|calculate|check)",
    r"\bthen\b.{5,50}\b(remind|open|search|find|calculate|check)\b",
    r"\bafter\s+that\b",
    r"\bfirst\b.{5,80}\bthen\b",
    r"\bstep\s+\d\b",
]


def is_multi_step(query: str) -> bool:
    """Return True if the query likely requires multiple tool calls."""
    q = query.lower()
    return any(re.search(p, q) for p in _MULTI_STEP_PATTERNS)


class TaskPlanner:
    """
    Splits a complex query into sub-tasks, runs each through the dispatcher,
    and merges the results into one coherent reply.
    """

    def __init__(self, dispatcher) -> None:
        self._dispatcher = dispatcher

    def run(self, query: str) -> Optional[str]:
        """
        Attempt multi-step execution. Returns combined result or None
        if the query doesn't decompose cleanly.
        """
        steps = self._split_steps(query)
        if len(steps) < 2:
            return None  # Not multi-step — let normal dispatch handle it

        logger.info("Planner: %d steps identified for: %r", len(steps), query[:60])
        results = []
        for i, step in enumerate(steps, 1):
            step = step.strip()
            if not step:
                continue
            logger.info("Planner step %d: %r", i, step)
            result = self._dispatcher.dispatch(step)
            if result:
                results.append(result)
            else:
                # Step needs LLM — skip for now, planner only handles tools
                logger.debug("Planner step %d had no tool match, skipping.", i)

        if not results:
            return None

        if len(results) == 1:
            return results[0]

        # Merge multiple results
        joined = "\n".join(f"• {r}" for r in results)
        return f"Done, Sir. Here's a summary:\n{joined}"

    def _split_steps(self, query: str) -> list[str]:
        """
        Split a compound query into individual task strings.
        Tries comma+and splits, then 'and then', then plain 'and'.
        """
        q = query.strip()

        # "do X, then do Y, and also do Z"
        parts = re.split(r",\s*(?:and\s+)?(?:also\s+)?(?:then\s+)?", q)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        # "do X and then do Y"
        parts = re.split(r"\s+and\s+then\s+", q, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        # "do X and do Y"
        parts = re.split(r"\s+and\s+", q, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        return [q]
