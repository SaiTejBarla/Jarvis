"""
tools/datetime_tool.py — Time and date information tool.
"""

from datetime import datetime
from .base import BaseTool


class DateTimeTool(BaseTool):
    name = "datetime"
    description = "Get the current date, time, day of week, or year."

    def run(self, query: str) -> str:
        now = datetime.now()
        q = query.lower()

        if "time" in q:
            return f"The current time is {now.strftime('%I:%M %p')}."
        if "date" in q:
            return f"Today is {now.strftime('%A, %B %d, %Y')}."
        if "day" in q:
            return f"Today is {now.strftime('%A')}."
        if "year" in q:
            return f"The current year is {now.year}."
        if "month" in q:
            return f"The current month is {now.strftime('%B')}."

        # Default: return full datetime
        return (
            f"It is {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}."
        )
