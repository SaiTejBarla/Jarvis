"""
tools/base.py — Base class for all JARVIS tools.

Every tool is a subclass of BaseTool that implements:
    - name: str          — unique identifier used by the dispatcher
    - description: str   — shown to the LLM for intent matching
    - run(query) -> str  — executes the tool and returns a plain-text result
"""

from abc import ABC, abstractmethod


class BaseTool(ABC):
    name: str = ""
    description: str = ""

    @abstractmethod
    def run(self, query: str) -> str:
        """Execute the tool and return a plain-text result."""
        ...

    def __repr__(self) -> str:
        return f"<Tool:{self.name}>"
