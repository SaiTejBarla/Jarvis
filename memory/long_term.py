"""
memory/long_term.py — Persistent long-term memory for JARVIS.

Stores facts and conversation summaries in ChromaDB (local vector store).
Also maintains a SQLite facts table for fast exact-match lookups.

Usage::

    mem = LongTermMemory()
    mem.store("User's name is Sai.")
    results = mem.recall("what is the user's name")
"""

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class LongTermMemory:
    """
    Hybrid memory: ChromaDB for semantic search + SQLite for structured facts.
    Both databases live under config.DATA_DIR.
    """

    def __init__(self) -> None:
        self._chroma = None       # lazy
        self._collection = None   # lazy
        self._db_path = config.DATA_DIR / "memory.db"
        self._ensure_sqlite()

    # ── Public API ────────────────────────────────────────────────────────────

    def store(self, text: str, metadata: Optional[dict] = None) -> None:
        """Store a fact or memory string for future recall."""
        if not text.strip():
            return
        self._ensure_chroma()
        import hashlib
        doc_id = hashlib.md5(text.encode()).hexdigest()
        try:
            meta = metadata if metadata else None
            upsert_kwargs = dict(documents=[text], ids=[doc_id])
            if meta:
                upsert_kwargs["metadatas"] = [meta]
            self._collection.upsert(**upsert_kwargs)
            logger.debug("Memory stored: %r", text[:80])
        except Exception as exc:
            logger.warning("ChromaDB store failed: %s", exc)

    def recall(self, query: str, n: int = 3) -> list[str]:
        """Retrieve the most relevant memories for a query."""
        self._ensure_chroma()
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n, self._collection.count() or 1),
            )
            docs = results.get("documents", [[]])[0]
            logger.debug("Memory recall for %r → %d results", query[:40], len(docs))
            return docs
        except Exception as exc:
            logger.warning("ChromaDB recall failed: %s", exc)
            return []

    def store_fact(self, key: str, value: str) -> None:
        """Store a structured key→value fact (e.g. 'user_name' → 'Sai')."""
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO facts(key, value) VALUES (?, ?)",
                (key.lower().strip(), value.strip()),
            )
        self.store(f"{key}: {value}")
        logger.debug("Fact stored: %s = %s", key, value)

    def get_fact(self, key: str) -> Optional[str]:
        """Retrieve a structured fact by key."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM facts WHERE key = ?",
                (key.lower().strip(),),
            ).fetchone()
        return row[0] if row else None

    def all_facts(self) -> dict[str, str]:
        """Return all stored key→value facts."""
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value FROM facts").fetchall()
        return {r[0]: r[1] for r in rows}

    def format_for_prompt(self, query: str) -> str:
        """
        Build a memory context block to inject into the system prompt.
        Combines relevant semantic memories with all structured facts.
        """
        lines = []

        facts = self.all_facts()
        if facts:
            lines.append("Known facts about the user:")
            for k, v in facts.items():
                lines.append(f"  - {k}: {v}")

        relevant = self.recall(query, n=3)
        if relevant:
            lines.append("Relevant memories:")
            for m in relevant:
                lines.append(f"  - {m}")

        return "\n".join(lines) if lines else ""

    # ── Internal ──────────────────────────────────────────────────────────────

    def _ensure_chroma(self) -> None:
        if self._collection is not None:
            return
        try:
            import chromadb  # type: ignore
            client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
            self._collection = client.get_or_create_collection(
                name="jarvis_memory",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB memory loaded (%d docs).", self._collection.count())
        except Exception as exc:
            logger.error("ChromaDB unavailable: %s — memory disabled.", exc)
            # Provide a no-op stub so callers don't crash.
            self._collection = _NullCollection()

    def _ensure_sqlite(self) -> None:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS facts "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)


class _NullCollection:
    """No-op stand-in when ChromaDB is unavailable."""
    def upsert(self, **_): pass
    def query(self, **_): return {"documents": [[]]}
    def count(self): return 0
