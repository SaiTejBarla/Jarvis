"""
core/engine.py — The JARVIS brain loop.

Phase 4+5: Adds browser automation, auth gate, audit log, persona modes,
long-term memory, and tool dispatch.

The Engine owns the Orchestrator, ToolDispatcher, LongTermMemory, AuthGate,
and AuditLog. It exposes a clean, mode-agnostic `process()` method that the
CLI, voice layer, and web UI all call.
"""

import logging
import re
from typing import Optional

from core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


class JarvisEngine:
    """
    Top-level runtime object for JARVIS.
    Instantiate once at startup; call `process()` for every user turn.
    """

    def __init__(self) -> None:
        self.orchestrator = Orchestrator()

        # Memory
        try:
            from memory.long_term import LongTermMemory
            self.memory = LongTermMemory()
        except Exception as exc:
            logger.warning("Long-term memory unavailable: %s", exc)
            self.memory = None

        # Auth gate
        try:
            from core.auth import AuthGate
            self.auth = AuthGate()
        except Exception as exc:
            logger.warning("Auth gate unavailable: %s", exc)
            self.auth = None

        # Audit log
        try:
            from core.audit import AuditLog
            self.audit = AuditLog()
        except Exception as exc:
            logger.warning("Audit log unavailable: %s", exc)
            self.audit = None

        # Tool dispatcher — lazy
        self._dispatcher = None

        # Monitor agent (Phase 7)
        try:
            from agents.monitor import MonitorAgent
            self.monitor = MonitorAgent()
            self.monitor.start()
        except Exception as exc:
            logger.warning("Monitor agent unavailable: %s", exc)
            self.monitor = None

        logger.info("JARVIS engine initialised.")

    # ── Public API ────────────────────────────────────────────────────────────

    def process(self, user_input: str, voice_mode: bool = False,
                pin: Optional[str] = None) -> str:
        """
        Handle a single user message and return JARVIS's reply.

        Flow:
          1. Check for voice passphrase authorization.
          2. Check for PIN setup command.
          3. Detect corrections — store them and acknowledge.
          4. Detect critical actions — block unless authorized.
          5. Try tool dispatch / multi-step planner.
          6. Inject memory context and fall through to LLM.
        """
        user_input = user_input.strip()
        if not user_input:
            return ""

        logger.info("User → %s", user_input)

        # 1. Voice passphrase auth check (always checked first)
        if self.auth and self.auth.check_voice(user_input):
            msg = "Authorization granted, Sir. You may proceed."
            self._audit_auth("voice passphrase accepted", user_input)
            return msg

        # 2. PIN setup command
        pin_setup = re.match(r"(?:set|change)\s+(?:my\s+)?pin\s+(?:to\s+)?(\d{4,8})", user_input, re.IGNORECASE)
        if pin_setup and self.auth:
            return self.auth.set_pin(pin_setup.group(1))

        # 3. Self-learning: detect corrections and store them.
        correction = self._detect_correction(user_input)
        if correction:
            return correction

        # 4. Critical action check — block if not authorized.
        from core.auth import is_critical_action
        critical_desc = is_critical_action(user_input)
        if critical_desc and self.auth:
            authorized, msg = self.auth.request(critical_desc, pin=pin)
            if not authorized:
                self._audit_critical(critical_desc, blocked=True)
                return msg
            self._audit_critical(critical_desc, blocked=False)

        # 5. Try tool dispatch first.
        tool_result = self._try_tool(user_input)
        if tool_result:
            logger.info("Tool result → %s", tool_result[:120])
            self._remember(user_input, tool_result)
            return tool_result

        # 6. Inject memory context and call LLM.
        memory_context = self._get_memory_context(user_input)
        try:
            reply = self.orchestrator.chat(user_input, memory_context=memory_context)
        except RuntimeError as exc:
            reply = f"⚠️  {exc}"

        logger.info("JARVIS → %s", reply[:120] + ("…" if len(reply) > 120 else ""))

        if self.audit:
            self.audit.log_llm(user_input, reply)

        self._remember(user_input, reply)
        self.sync_exporter_history()

        return reply

    def reset_memory(self) -> None:
        """Clear the in-session conversation history."""
        self.orchestrator.reset()

    def set_tts_callback(self, callback) -> None:
        """Wire a TTS callback into reminder, scheduler, and monitor."""
        disp = self._get_dispatcher()
        if hasattr(disp, "_reminder"):
            disp._reminder._on_fire = callback
        if hasattr(disp, "_scheduler"):
            disp._scheduler._on_fire = callback
        if self.monitor:
            self.monitor.set_callback(callback)

    def set_reminder_callback(self, callback) -> None:
        """Alias for set_tts_callback — kept for backwards compatibility."""
        self.set_tts_callback(callback)

    def sync_exporter_history(self) -> None:
        """Push current conversation history to the exporter tool."""
        disp = self._get_dispatcher()
        if hasattr(disp, "_exporter"):
            disp._exporter.set_history(self.orchestrator.history)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _try_tool(self, user_input: str) -> Optional[str]:
        try:
            dispatcher = self._get_dispatcher()
            result = dispatcher.dispatch(user_input)
            if result and self.audit:
                self.audit.log_tool("dispatcher", user_input, result)
            return result
        except Exception as exc:
            logger.warning("Tool dispatch error: %s", exc)
            return None

    def _get_dispatcher(self):
        if self._dispatcher is None:
            try:
                from tools.dispatcher import ToolDispatcher
                self._dispatcher = ToolDispatcher()
            except Exception as exc:
                logger.warning("ToolDispatcher unavailable: %s", exc)
                self._dispatcher = _NullDispatcher()
        return self._dispatcher

    def _get_memory_context(self, query: str) -> str:
        if self.memory is None:
            return ""
        try:
            return self.memory.format_for_prompt(query)
        except Exception:
            return ""

    def _remember(self, user_input: str, reply: str) -> None:
        if self.memory is None:
            return
        try:
            self.memory.store(f"User asked: {user_input}\nJARVIS replied: {reply}")
            self._extract_facts(user_input)
        except Exception as exc:
            logger.debug("Memory store failed: %s", exc)

    def _extract_facts(self, text: str) -> None:
        """Parse simple self-referential facts from user input."""
        patterns = [
            (r"my name is ([A-Za-z]+)", "user_name"),
            (r"i(?:'m| am) ([A-Za-z]+)", "user_name"),
            (r"i(?:'m| am) (\d+) years? old", "user_age"),
            (r"i(?:'m| am) from ([A-Za-z\s]+)", "user_location"),
            (r"i live in ([A-Za-z\s]+)", "user_location"),
            (r"i work (?:at|for) ([A-Za-z\s]+)", "user_workplace"),
        ]
        for pattern, key in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                self.memory.store_fact(key, m.group(1).strip())
                logger.info("Fact extracted: %s = %s", key, m.group(1).strip())

    def _detect_correction(self, text: str) -> Optional[str]:
        """Detect corrections and store them."""
        if self.memory is None:
            return None
        patterns = [
            r"(?:no[,.]?\s+)?(?:actually|wrong[,.]?\s+|that'?s?\s+(?:wrong|incorrect)[,.]?\s+)(.+)\s+is\s+(.+)",
            r"(?:no[,.]?\s+)?the\s+(?:correct\s+)?answer\s+is\s+(.+)",
            r"(?:i\s+meant|i\s+mean)\s+(.+)",
            r"correct(?:ion)?[:\s]+(.+)",
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                self.memory.store(f"Correction from user: {text.strip()}")
                logger.info("Correction stored: %s", text.strip())
                return "Noted and corrected, Sir. I'll remember that."
        return None

    def _audit_auth(self, event: str, action: str = "") -> None:
        if self.audit:
            self.audit.log_auth(event, action)

    def _audit_critical(self, action: str, blocked: bool) -> None:
        if self.audit:
            self.audit.log_critical(action, blocked)


class _NullDispatcher:
    def dispatch(self, _): return None
