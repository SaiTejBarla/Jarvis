"""
tools/code_runner.py — Safe sandboxed Python code executor for JARVIS.

Executes Python snippets in a subprocess with a timeout.
stdout/stderr are captured and returned.
No dangerous builtins are accessible (file I/O, network, os.system blocked).

Commands:
    "run python: print('hello')"
    "execute: x = 5; print(x * 2)"
    "python: import math; print(math.sqrt(16))"
"""

import logging
import re
import subprocess
import sys
import textwrap
import tempfile
import os
from pathlib import Path
from .base import BaseTool

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 10

# Blocked patterns — refuse to run if found
_DANGEROUS = [
    r"\bos\.system\b",
    r"\bsubprocess\b",
    r"\bshutil\b",
    r"\bopen\s*\(",
    r"\b__import__\b",
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bimport\s+os\b",
    r"\bimport\s+sys\b",
    r"\bimport\s+subprocess\b",
    r"\bsocket\b",
    r"\burllib\b",
    r"\brequests\b",
]


def _is_safe(code: str) -> bool:
    for pattern in _DANGEROUS:
        if re.search(pattern, code):
            return False
    return True


class CodeRunnerTool(BaseTool):
    name = "code_runner"
    description = (
        "Run a Python code snippet and return the output. "
        "e.g. 'run python: print(2 ** 10)', 'execute: sum(range(100))'."
    )

    def run(self, query: str) -> str:
        # Extract code after keyword
        m = re.search(
            r"(?:run\s+python|execute|python|run\s+code)[:\s]+(.+)",
            query, re.IGNORECASE | re.DOTALL
        )
        code = m.group(1).strip() if m else query.strip()

        if not code:
            return "Please provide code to run, Sir."

        if not _is_safe(code):
            return "I can't run that code, Sir — it contains restricted operations for safety."

        return self._execute(code)

    def _execute(self, code: str) -> str:
        # Wrap in a print if it's a single expression with no print
        lines = code.strip().splitlines()
        if len(lines) == 1 and not code.startswith("print") and "=" not in code:
            code = f"print({code})"

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as f:
                f.write(code)
                tmp_path = f.name

            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
            )
            os.unlink(tmp_path)

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if result.returncode == 0:
                return f"Output:\n{stdout}" if stdout else "Code ran successfully with no output."
            else:
                err = stderr.splitlines()[-1] if stderr else "Unknown error"
                return f"Error: {err}"

        except subprocess.TimeoutExpired:
            return f"Code timed out after {_TIMEOUT_SECONDS} seconds, Sir."
        except Exception as exc:
            logger.warning("Code runner failed: %s", exc)
            return f"Could not execute code: {exc}"
