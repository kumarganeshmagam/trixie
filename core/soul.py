"""
Trixie 2.0 — Soul loader.

Reads soul/ files on every call so edits take effect immediately
without restarting Trixie. The soul is the system prompt.

File load order:
  1. identity.md   — who Trixie is
  2. rules.md      — what she will and won't do
  3. personality.md — how she communicates
  4. adaptations.md — discovered user preferences (auto-written over time)
"""

from __future__ import annotations
from pathlib import Path

SOUL_DIR = Path(__file__).parent.parent / "soul"


def load_soul() -> str:
    """Merge all soul files into a single block of text."""
    files = ["identity.md", "rules.md", "personality.md", "adaptations.md"]
    sections: list[str] = []
    for fname in files:
        path = SOUL_DIR / fname
        if path.exists():
            content = path.read_text(encoding="utf-8").strip()
            if content:
                sections.append(content)
    return "\n\n---\n\n".join(sections)


def build_system_prompt(
    memory_context: str = "",
    emotion: str = "",
    vision_context: str = "",
) -> str:
    """
    Build the full system prompt for a single inference call.

    Args:
        memory_context: Relevant snippets retrieved from episodic/semantic memory.
        emotion:        Detected user emotional state (e.g. 'tired', 'frustrated').
        vision_context: One-sentence screen description from the vision system.
    """
    soul = load_soul()

    parts = [
        "You are Trixie, a personal AI assistant running entirely on the user's device.\n\n"
        + soul
    ]

    if vision_context:
        parts.append(f"Screen context (what the user is currently doing):\n{vision_context}")

    if memory_context:
        parts.append(f"Relevant context from memory:\n{memory_context}")

    if emotion and emotion != "neutral":
        parts.append(
            f"Detected user state: {emotion}. "
            "Adapt your response style accordingly per personality.md."
        )

    parts.append(
        "Be brief and direct. "
        "Announce before taking any system action. "
        "Never reveal the underlying model name unless directly asked. "
        "You are Trixie — that is your only identity."
    )

    return "\n\n".join(parts)
