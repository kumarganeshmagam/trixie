"""
Trixie 2.0 — Decision logger.

Every non-trivial action Trixie takes is logged here with:
  - What triggered it
  - What context (memory/soul) informed the decision
  - What the decision was
  - The reasoning
  - The outcome (updated after the fact)

This makes it possible to answer "Why did you do that?" accurately,
from actual logged data rather than post-hoc rationalisation.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
DECISIONS_FILE = ROOT / "memory" / "decisions.jsonl"


def log_decision(
    trigger: str,
    decision: str,
    reasoning: str,
    context_used: list[str] | None = None,
    outcome: str = "pending",
    emotion: str = "neutral",
) -> None:
    """
    Append a decision record to memory/decisions.jsonl.

    Args:
        trigger:      What caused Trixie to act (e.g. "user opened VS Code").
        decision:     What Trixie decided to do.
        reasoning:    Why — in plain language.
        context_used: List of memory/soul snippets that informed the decision.
        outcome:      "accepted" | "rejected" | "ignored" | "pending"
        emotion:      Detected user state at decision time.
    """
    DECISIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(),
        "trigger": trigger,
        "context_used": context_used or [],
        "decision": decision,
        "reasoning": reasoning,
        "outcome": outcome,
        "emotion_detected": emotion,
    }
    with open(DECISIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def update_outcome(decision_text: str, outcome: str) -> None:
    """Update the outcome field of the most recent matching decision."""
    if not DECISIONS_FILE.exists():
        return
    lines = DECISIONS_FILE.read_text(encoding="utf-8").splitlines()
    updated = []
    found = False
    for line in reversed(lines):
        if not found:
            try:
                rec = json.loads(line)
                if rec.get("decision") == decision_text:
                    rec["outcome"] = outcome
                    line = json.dumps(rec)
                    found = True
            except json.JSONDecodeError:
                pass
        updated.append(line)
    DECISIONS_FILE.write_text("\n".join(reversed(updated)) + "\n", encoding="utf-8")


def get_recent_decisions(limit: int = 10) -> list[dict]:
    """Return the N most recent decision records."""
    if not DECISIONS_FILE.exists():
        return []
    records: list[dict] = []
    with open(DECISIONS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records[-limit:]


def explain_last_decision() -> str:
    """
    Return a human-readable explanation of the most recent logged decision.
    Used when the user asks "Why did you do that?"
    """
    records = get_recent_decisions(limit=1)
    if not records:
        return "I haven't logged any decisions yet this session."
    d = records[0]
    ctx = "\n  • ".join(d.get("context_used") or []) or "none"
    return (
        f"At {d['timestamp'][:19]}:\n"
        f"Triggered by: {d['trigger']}\n"
        f"Decision: {d['decision']}\n"
        f"Reasoning: {d['reasoning']}\n"
        f"Context used:\n  • {ctx}\n"
        f"Outcome: {d['outcome']}"
    )
