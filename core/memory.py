"""
Trixie 2.0 — Three-tier memory.

Tier 1 — Working memory
    In-process sliding-window conversation history (last N messages).
    Lives only in RAM; cleared when Trixie restarts.

Tier 2 — Episodic memory
    Explicit facts the user shares ("remember I have a meeting at 3pm").
    Persisted to SQLite. Keyword-searched at query time.

Tier 3 — Semantic memory
    RAG over the user's stored notes and documents.
    Chroma vector store, embedded with nomic-embed-text (local via Ollama).
    Falls back gracefully if Ollama is not running.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
MEMORY_DIR = ROOT / "memory"
EPISODIC_DB = MEMORY_DIR / "episodic.db"
CHROMA_DIR = MEMORY_DIR / "semantic"

MAX_WORKING_MESSAGES = 20


# ── Tier 2 — Episodic (SQLite) ─────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(EPISODIC_DB))
    c.execute(
        "CREATE TABLE IF NOT EXISTS facts "
        "(id INTEGER PRIMARY KEY, ts TEXT NOT NULL, fact TEXT NOT NULL, tags TEXT)"
    )
    c.commit()
    return c


def store_episodic(fact: str, tags: list[str] | None = None) -> None:
    """Persist a fact to the episodic SQLite store."""
    c = _conn()
    c.execute(
        "INSERT INTO facts (ts, fact, tags) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), fact, json.dumps(tags or [])),
    )
    c.commit()
    c.close()


def search_episodic(query: str, limit: int = 5) -> list[str]:
    """Keyword search over stored facts. Returns the most recent matches."""
    c = _conn()
    words = [w.lower() for w in query.split() if len(w) > 2]
    rows = c.execute(
        "SELECT fact FROM facts ORDER BY ts DESC"
    ).fetchall()
    c.close()

    results: list[str] = []
    for (fact,) in rows:
        if any(w in fact.lower() for w in words):
            results.append(fact)
            if len(results) >= limit:
                break
    return results


def get_recent_episodic(limit: int = 10) -> list[str]:
    """Return the N most recently stored facts with their dates."""
    c = _conn()
    rows = c.execute(
        "SELECT ts, fact FROM facts ORDER BY ts DESC LIMIT ?", (limit,)
    ).fetchall()
    c.close()
    return [f"[{ts[:10]}] {fact}" for ts, fact in rows]


# ── Tier 3 — Semantic (Chroma + nomic-embed-text) ─────────────────────────────

_vector_store = None


def _get_vector_store():
    global _vector_store
    if _vector_store is not None:
        return _vector_store
    try:
        from langchain_community.vectorstores import Chroma
        from langchain_ollama import OllamaEmbeddings

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        embeddings = OllamaEmbeddings(model="nomic-embed-text")
        _vector_store = Chroma(
            embedding_function=embeddings,
            persist_directory=str(CHROMA_DIR),
        )
    except Exception as exc:
        print(f"[memory] Semantic store unavailable: {exc}")
        _vector_store = None
    return _vector_store


def store_semantic(text: str, metadata: dict | None = None) -> None:
    """Embed and store a document chunk in the Chroma vector store."""
    vs = _get_vector_store()
    if vs:
        vs.add_texts([text], metadatas=[metadata or {}])


def search_semantic(query: str, k: int = 3) -> list[str]:
    """Similarity search over the Chroma store. Returns text chunks."""
    vs = _get_vector_store()
    if not vs:
        return []
    try:
        docs = vs.similarity_search(query, k=k)
        return [d.page_content for d in docs]
    except Exception:
        return []


# ── Combined retrieval ─────────────────────────────────────────────────────────

def retrieve_context(query: str) -> str:
    """
    Pull relevant context from episodic + semantic memory for the given query.
    Returns a formatted string ready for injection into the system prompt.
    """
    episodic = search_episodic(query, limit=3)
    semantic = search_semantic(query, k=2)

    parts: list[str] = []
    if episodic:
        parts.append("From your memory:\n" + "\n".join(f"• {f}" for f in episodic))
    if semantic:
        parts.append("From stored notes:\n" + "\n".join(f"• {s}" for s in semantic))

    return "\n\n".join(parts)


# ── Tier 1 — Working memory ────────────────────────────────────────────────────

class WorkingMemory:
    """
    Sliding-window conversation buffer.
    Keeps the last `max_messages` turns in RAM only.
    """

    def __init__(self, max_messages: int = MAX_WORKING_MESSAGES):
        self._max = max_messages
        self._buf: list[dict[str, str]] = []

    def add(self, role: str, content: str) -> None:
        self._buf.append({"role": role, "content": content})
        if len(self._buf) > self._max:
            self._buf = self._buf[-self._max :]

    def messages(self) -> list[dict[str, str]]:
        return list(self._buf)

    def clear(self) -> None:
        self._buf.clear()
