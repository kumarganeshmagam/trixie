"""
Trixie 2.0 — Usage pattern tracking + proactive triggers (Phase 4).

Everything here is local:
  • Events are stored in memory/patterns.db (SQLite) — never uploaded.
  • Patterns are derived on-device with simple frequency analysis.
  • Every proactive suggestion is logged to memory/decisions.jsonl so the
    user can always ask "why did you suggest that?"

Event kinds tracked:
  session_start / session_end   — when Trixie is used
  chat                          — a chat turn happened (hour-of-day pattern)
  app_open                      — Trixie opened an app for the user
  topic                         — coarse topic of a request (code / search / memory)
"""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
PATTERNS_DB = ROOT / "memory" / "patterns.db"


# ── Storage ────────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    PATTERNS_DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(PATTERNS_DB))
    c.execute(
        "CREATE TABLE IF NOT EXISTS events "
        "(id INTEGER PRIMARY KEY, ts TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT)"
    )
    c.commit()
    return c


def record_event(kind: str, detail: str = "") -> None:
    """Record a usage event. Local only — never leaves the device."""
    c = _conn()
    c.execute(
        "INSERT INTO events (ts, kind, detail) VALUES (?, ?, ?)",
        (datetime.now().isoformat(), kind, detail),
    )
    c.commit()
    c.close()


def _events_since(days: int = 30) -> list[tuple[str, str, str]]:
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    c = _conn()
    rows = c.execute(
        "SELECT ts, kind, detail FROM events WHERE ts >= ? ORDER BY ts", (cutoff,)
    ).fetchall()
    c.close()
    return rows


# ── Pattern analysis ───────────────────────────────────────────────────────────

@dataclass
class UsagePatterns:
    active_hours: list[int]        # hours of day the user is usually active
    frequent_apps: list[str]       # apps Trixie opens most often
    frequent_topics: list[str]     # what the user usually asks about
    total_events: int


def get_patterns(days: int = 30) -> UsagePatterns:
    """Derive coarse usage patterns from the local event log."""
    rows = _events_since(days)
    hours = Counter(datetime.fromisoformat(ts).hour for ts, kind, _ in rows if kind == "chat")
    apps = Counter(detail for _, kind, detail in rows if kind == "app_open" and detail)
    topics = Counter(detail for _, kind, detail in rows if kind == "topic" and detail)
    return UsagePatterns(
        active_hours=[h for h, n in hours.most_common(4) if n >= 3],
        frequent_apps=[a for a, n in apps.most_common(3) if n >= 2],
        frequent_topics=[t for t, n in topics.most_common(3) if n >= 3],
        total_events=len(rows),
    )


# ── Proactive triggers ─────────────────────────────────────────────────────────

def check_proactive_trigger(now: datetime | None = None) -> str | None:
    """
    Decide whether Trixie should proactively surface something right now.
    Returns a short suggestion string, or None if she should stay quiet.

    Deliberately conservative: at most one suggestion per session-hour,
    and only when a pattern is well-established (seen 3+ times).
    """
    now = now or datetime.now()
    patterns = get_patterns()
    if patterns.total_events < 10:
        return None  # not enough history — don't guess

    # Don't repeat: only one proactive nudge per rolling hour
    rows = _events_since(days=1)
    for ts, kind, _ in reversed(rows):
        if kind == "proactive_shown":
            if datetime.fromisoformat(ts) > now - timedelta(hours=1):
                return None
            break

    suggestion: str | None = None
    reasoning = ""

    if now.hour in patterns.active_hours and patterns.frequent_topics:
        topic = patterns.frequent_topics[0]
        suggestion = f"You're usually working on {topic} around now — want to pick that up?"
        reasoning = (
            f"Hour {now.hour} is one of the user's active hours; "
            f"'{topic}' is their most frequent topic (last 30 days)."
        )
    elif patterns.frequent_apps and now.hour in patterns.active_hours:
        app = patterns.frequent_apps[0]
        suggestion = f"Want me to open {app}? You usually use it around this time."
        reasoning = f"'{app}' is the most frequently opened app during hour {now.hour}."

    if suggestion:
        record_event("proactive_shown", suggestion)
        from core.decisions import log_decision
        log_decision(
            trigger=f"time-of-day pattern match at {now.strftime('%H:%M')}",
            decision=f"surface proactive suggestion: {suggestion}",
            reasoning=reasoning,
            context_used=[
                f"active hours: {patterns.active_hours}",
                f"frequent topics: {patterns.frequent_topics}",
                f"frequent apps: {patterns.frequent_apps}",
            ],
        )
    return suggestion


def classify_topic(message: str) -> str:
    """Coarse topic bucket for pattern tracking (not used for routing)."""
    lower = message.lower()
    if any(w in lower for w in ("code", "program", "script", "debug", "function", "python")):
        return "coding"
    if any(w in lower for w in ("open", "launch", "start", "play")):
        return "apps"
    if any(w in lower for w in ("remember", "memory", "recall", "forgot")):
        return "memory"
    if any(w in lower for w in ("what", "who", "when", "where", "search", "wiki")):
        return "search"
    return "chat"


def export_patterns_summary() -> str:
    """Human-readable summary — used by the /patterns command."""
    p = get_patterns()
    if p.total_events < 10:
        return "Not enough usage history yet to see patterns. Keep using Trixie!"
    lines = [f"Based on {p.total_events} local events (last 30 days):"]
    if p.active_hours:
        hrs = ", ".join(f"{h}:00" for h in sorted(p.active_hours))
        lines.append(f"• You're usually active around: {hrs}")
    if p.frequent_topics:
        lines.append(f"• Frequent topics: {', '.join(p.frequent_topics)}")
    if p.frequent_apps:
        lines.append(f"• Apps I open for you most: {', '.join(p.frequent_apps)}")
    lines.append("(All of this is stored locally in memory/patterns.db — nothing is uploaded.)")
    return "\n".join(lines)
