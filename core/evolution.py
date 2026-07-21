"""
Trixie 2.0 — Evolution tracker.

Watches every interaction and auto-updates soul/adaptations.md with
discovered user preferences. Never deletes entries — only appends.

The adaptations file is part of Trixie's portable soul: when you move
to a new device and restore from GitHub, this file travels with her
so she arrives already knowing how you like to work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
ADAPTATIONS_FILE = ROOT / "soul" / "adaptations.md"
PATTERNS_FILE = ROOT / "memory" / "evolution" / "patterns.jsonl"
MILESTONES_FILE = ROOT / "memory" / "evolution" / "milestones.md"


@dataclass
class Interaction:
    user_message: str
    trixie_response: str
    # "accepted" | "corrected" | "ignored" | "praised" | "unknown"
    outcome: str = "unknown"
    tool_used: str | None = None
    emotion: str = "neutral"
    timestamp: datetime = field(default_factory=datetime.now)


def observe(interaction: Interaction) -> None:
    """
    Observe a completed interaction. Updates patterns log and, when a
    meaningful signal is detected, appends a note to adaptations.md.
    """
    _log_pattern(interaction)

    if interaction.outcome == "corrected":
        _append_adaptation(
            "User corrected a response — may indicate over-explanation or missed intent. "
            f"Topic: '{interaction.user_message[:80]}'"
        )

    if interaction.outcome == "praised":
        style_hint = interaction.trixie_response[:100].strip()
        _append_adaptation(
            f"User expressed approval. Reinforce this response style: '{style_hint}…'"
        )

    if interaction.emotion == "frustrated":
        _append_adaptation(
            "User showed frustration during this session — "
            "consider being more concise and direct in future responses."
        )


def record_milestone(milestone: str) -> None:
    """Append a notable moment to the milestones file."""
    MILESTONES_FILE.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n## {today}\n{milestone}\n"
    if not MILESTONES_FILE.exists():
        MILESTONES_FILE.write_text("# Trixie — Evolution Milestones\n")
    with open(MILESTONES_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def _append_adaptation(note: str) -> None:
    ADAPTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n## Observed: {today}\n- {note}\n"

    if not ADAPTATIONS_FILE.exists():
        ADAPTATIONS_FILE.write_text(
            "# Trixie — Adaptations\n\n"
            "Auto-written by Trixie. Never deleted by Trixie. "
            "Always readable and editable by the user.\n"
        )

    with open(ADAPTATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


def _log_pattern(interaction: Interaction) -> None:
    PATTERNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": interaction.timestamp.isoformat(),
        "user_message": interaction.user_message[:200],
        "outcome": interaction.outcome,
        "emotion": interaction.emotion,
        "tool_used": interaction.tool_used,
    }
    with open(PATTERNS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
