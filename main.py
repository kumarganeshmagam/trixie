"""
Trixie 2.0 — Entry point.

First run:
  1. Detects platform (desktop → Ollama, mobile → llama.cpp/GGUF)
  2. Downloads and sets up the model automatically
  3. Writes ~/.trixie/.setup_complete to skip setup on future runs

After setup:
  Starts the CLI chat loop (Phase 1 foundation).
  UI shells (desktop overlay, mobile, web) will import TrixieAgent
  from core.agent and call .chat() — same interface.

Special commands in the CLI:
  exit / quit / bye       — end session
  /reset                  — clear working memory (long-term memory kept)
  /memory                 — show recent episodic memory entries
  /why                    — explain Trixie's last decision
  /vision on|off          — toggle screen awareness
  /sync push|pull <repo>  — backup / restore soul + memory via GitHub
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Ensure project root is importable regardless of where Python is invoked from
sys.path.insert(0, str(Path(__file__).parent))


# ── Setup state file ──────────────────────────────────────────────────────────

_STATE_FILE = Path.home() / ".trixie" / ".setup_complete"


def _load_setup_result() -> dict | None:
    if not _STATE_FILE.exists():
        return None
    try:
        import ast
        return ast.literal_eval(_STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_setup_result(result: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(str(result), encoding="utf-8")


# ── TTS helper ────────────────────────────────────────────────────────────────

def _make_speak():
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 185)
        engine.setProperty("volume", 1.0)
        voices = engine.getProperty("voices")
        if len(voices) > 1:
            engine.setProperty("voice", voices[1].id)

        def speak(text: str) -> None:
            engine.say(text)
            engine.runAndWait()

        return speak
    except Exception:
        # TTS unavailable — fall back to print-only
        return lambda text: None


# ── Greeting ──────────────────────────────────────────────────────────────────

def _greeting() -> str:
    hour = datetime.now().hour
    if 6 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 21:
        return "Good evening"
    return "Hey"


# ── Special command handlers ──────────────────────────────────────────────────

def _handle_special(cmd: str, agent, speak) -> bool:
    """
    Handle /commands. Returns True if the command was handled (skip normal chat).
    """
    cmd = cmd.strip()

    if cmd == "/reset":
        agent.reset_working_memory()
        print("Trixie: Working memory cleared. Long-term memory is untouched.\n")
        return True

    if cmd == "/memory":
        from core.memory import get_recent_episodic
        facts = get_recent_episodic(limit=10)
        if facts:
            print("Trixie: Here's what I remember:\n" + "\n".join(f"  {f}" for f in facts))
        else:
            print("Trixie: No episodic memories stored yet.")
        print()
        return True

    if cmd == "/why":
        from core.decisions import explain_last_decision
        print(f"Trixie:\n{explain_last_decision()}\n")
        return True

    if cmd.startswith("/vision"):
        from core.vision import vision
        parts = cmd.split()
        if len(parts) == 2 and parts[1] == "on":
            msg = vision.enable()
        elif len(parts) == 2 and parts[1] == "off":
            msg = vision.disable()
        else:
            msg = f"Vision is currently {'ON' if vision.enabled else 'OFF'}. Use /vision on or /vision off."
        print(f"Trixie: {msg}\n")
        speak(msg)
        return True

    if cmd.startswith("/sync"):
        parts = cmd.split()
        if len(parts) < 3:
            print("Trixie: Usage: /sync push <github-repo-url>  or  /sync pull <github-repo-url>\n")
            return True
        direction, repo = parts[1], parts[2]
        from setup.sync import sync_push, sync_pull
        if direction == "push":
            sync_push(repo)
        elif direction == "pull":
            sync_pull(repo)
        else:
            print("Trixie: Unknown sync direction. Use 'push' or 'pull'.\n")
        return True

    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── Step 1: first-run model setup ─────────────────────────────────────────
    setup_result = _load_setup_result()

    if setup_result is None:
        print("=" * 56)
        print("  Welcome to Trixie 2.0 — first-time setup")
        print("=" * 56)
        print("Detecting platform and downloading the model …\n")

        from setup.model_download import first_run_setup
        setup_result = first_run_setup()

        if not setup_result.get("ready"):
            print("\n[error] Setup failed. Check the messages above.")
            print("        Manual install guide: https://ollama.com/download")
            sys.exit(1)

        _save_setup_result(setup_result)
        print("\nSetup complete — Trixie is ready.\n")

    # ── Step 2: load the model ─────────────────────────────────────────────────
    from core.model import get_llm

    backend = setup_result.get("backend", "ollama")
    model_path = setup_result.get("model_path")
    print(f"[trixie] Loading model ({backend}) …")
    llm = get_llm(backend=backend, model_path=model_path)

    # ── Step 3: build the agent ────────────────────────────────────────────────
    from core.agent import TrixieAgent

    agent = TrixieAgent(llm)
    speak = _make_speak()

    # ── Step 4: greet the user ─────────────────────────────────────────────────
    greeting = _greeting()
    welcome = f"{greeting}! I'm Trixie. How can I help?"
    print(f"\nTrixie: {welcome}")
    speak(welcome)
    print()
    print("  /reset        clear working memory")
    print("  /memory       show stored facts")
    print("  /why          explain last decision")
    print("  /vision on|off  toggle screen awareness")
    print("  /sync push|pull <repo>  backup / restore to GitHub")
    print("  exit          quit")
    print("─" * 56)

    # ── Step 5: chat loop ──────────────────────────────────────────────────────
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTrixie: Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "bye"):
            farewell = "Take care!" if datetime.now().hour >= 6 else "Good night!"
            print(f"\nTrixie: {farewell}")
            speak(farewell)
            break

        if user_input.startswith("/"):
            _handle_special(user_input, agent, speak)
            continue

        response = agent.chat(user_input)
        print(f"\nTrixie: {response}")
        speak(response)
        print("─" * 56)


if __name__ == "__main__":
    main()
