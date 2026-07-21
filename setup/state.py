"""
Trixie 2.0 — First-run setup state persistence.

Stores the result of setup.model_download.first_run_setup() so that
subsequent launches (CLI, web, overlay, mobile) skip the setup flow.
"""

from __future__ import annotations

import ast
from pathlib import Path

STATE_FILE = Path.home() / ".trixie" / ".setup_complete"


def load_setup() -> dict | None:
    """Return the persisted setup result, or None if setup hasn't run."""
    if not STATE_FILE.exists():
        return None
    try:
        return ast.literal_eval(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_setup(result: dict) -> None:
    """Persist a successful setup result."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(str(result), encoding="utf-8")


def ensure_setup() -> dict:
    """
    Load the setup state, running first-run setup if needed.
    Raises RuntimeError if setup fails.
    """
    setup = load_setup()
    if setup is None:
        from setup.model_download import first_run_setup
        setup = first_run_setup()
        if not setup.get("ready"):
            raise RuntimeError("First-run setup failed — model not available.")
        save_setup(setup)
    return setup
