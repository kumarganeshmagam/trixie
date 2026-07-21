"""
Trixie 2.0 — Unified entry point.

Detects the runtime environment and delegates to the right UI shell:

  Android / iOS  → Kivy mobile app  (ui/mobile/app.py)
  --web flag     → FastAPI web app  (ui/web/server.py)   opens in browser
  --overlay flag → PyQt6 animated character overlay (ui/desktop/app.py)
  default        → CLI chat loop

On first run (any platform): model download happens automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _is_mobile() -> bool:
    import os
    if os.environ.get("ANDROID_ROOT") or os.environ.get("ANDROID_DATA"):
        return True
    sdk = os.environ.get("SDK_NAME", "")
    if "iphone" in sdk.lower() or os.environ.get("BRIEFCASE_PLATFORM") == "iOS":
        return True
    return False


# ── Mobile (Kivy) ─────────────────────────────────────────────────────────────
if _is_mobile():
    from ui.mobile.app import run
    run()

# ── Web mode ──────────────────────────────────────────────────────────────────
elif "--web" in sys.argv:
    from ui.web.server import run as web_run
    web_run()

# ── Overlay mode (PyQt6 animated character) ───────────────────────────────────
elif "--overlay" in sys.argv:
    from ui.desktop.app import run as overlay_run
    overlay_run()

# ── CLI (desktop default) ─────────────────────────────────────────────────────
else:
    from datetime import datetime

    from setup.state import load_setup as _load_setup, save_setup as _save_setup

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
            return lambda _: None

    def _greeting() -> str:
        h = datetime.now().hour
        if 6 <= h < 12:  return "Good morning"
        if 12 <= h < 17: return "Good afternoon"
        if 17 <= h < 21: return "Good evening"
        return "Hey"

    def _handle_special(cmd: str, agent, speak) -> bool:
        if cmd == "/reset":
            agent.reset_working_memory()
            print("Trixie: Working memory cleared.\n")
            return True
        if cmd == "/memory":
            from core.memory import get_recent_episodic
            facts = get_recent_episodic(10)
            print("Trixie: " + ("\n".join(f"  {f}" for f in facts) if facts else "No memories yet.") + "\n")
            return True
        if cmd == "/why":
            from core.decisions import explain_last_decision
            print(f"Trixie:\n{explain_last_decision()}\n")
            return True
        if cmd == "/patterns":
            from core.patterns import export_patterns_summary
            print(f"Trixie:\n{export_patterns_summary()}\n")
            return True
        if cmd.startswith("/vision"):
            from core.vision import vision
            parts = cmd.split()
            if len(parts) == 2 and parts[1] == "on":    msg = vision.enable()
            elif len(parts) == 2 and parts[1] == "off": msg = vision.disable()
            else: msg = f"Vision is {'ON' if vision.enabled else 'OFF'}. Use /vision on|off."
            print(f"Trixie: {msg}\n"); speak(msg)
            return True
        if cmd.startswith("/sync"):
            parts = cmd.split()
            if len(parts) < 3:
                print("Trixie: Usage: /sync push|pull <github-repo-url>\n")
                return True
            from setup.sync import sync_push, sync_pull
            sync_push(parts[2]) if parts[1] == "push" else sync_pull(parts[2])
            return True
        return False

    def main() -> None:
        setup = _load_setup()
        if setup is None:
            print("=" * 56)
            print("  Welcome to Trixie 2.0 — first-time setup")
            print("=" * 56)
            from setup.model_download import first_run_setup
            setup = first_run_setup()
            if not setup.get("ready"):
                print("\n[error] Setup failed. See messages above.")
                sys.exit(1)
            _save_setup(setup)
            print("\nSetup complete!\n")

        from core.model import get_llm
        print(f"[trixie] Loading model ({setup.get('backend', 'ollama')}) …")
        llm = get_llm(backend=setup.get("backend", "ollama"),
                      model_path=setup.get("model_path"))

        from core.agent import TrixieAgent
        agent = TrixieAgent(llm)
        speak = _make_speak()

        welcome = f"{_greeting()}! I'm Trixie. How can I help?"
        print(f"\nTrixie: {welcome}")
        speak(welcome)
        print()
        print("  /reset  /memory  /why  /patterns  /vision on|off  /sync push|pull <repo>  exit")
        print("─" * 56)

        while True:
            try:
                user_input = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nTrixie: Goodbye!"); break
            if not user_input: continue
            if user_input.lower() in ("exit", "quit", "bye"):
                farewell = "Good night!" if datetime.now().hour < 6 else "Take care!"
                print(f"\nTrixie: {farewell}"); speak(farewell); break
            if user_input.startswith("/"):
                _handle_special(user_input, agent, speak); continue
            response = agent.chat(user_input)
            print(f"\nTrixie: {response}")
            speak(response)
            print("─" * 56)

    main()
