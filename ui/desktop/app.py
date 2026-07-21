"""
Trixie 2.0 — Desktop overlay application (Phase 2 + 3 + 4).

Launch with:  python main.py --overlay

Wires together:
  • TrixieCharacter  — animated always-on-top face (idle/thinking/talking/…)
  • ChatPanel        — expandable chat card next to the character
  • SpeechBubble     — short proactive nudges (Phase 4 triggers)
  • TrixieAgent      — the LangGraph core (inference runs off the UI thread)

Keyboard:
  Ctrl+Shift+V  — toggle vision (works while the chat panel has focus)
  Esc           — collapse the chat panel

Character state machine:
  idle → (click) → listening → (send) → thinking/working → talking → idle
  idle → (90 s untouched) → roaming
  idle → (10 min untouched) → sleeping   (any interaction wakes her)
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication

from ui.desktop.character import TrixieCharacter
from ui.desktop.chat_panel import ChatPanel, SpeechBubble

SLEEP_AFTER_MS = 10 * 60 * 1000       # sleeping after 10 min without interaction
PROACTIVE_CHECK_MS = 15 * 60 * 1000   # check Phase-4 triggers every 15 min


class _InferenceWorker(QObject):
    """Runs agent.chat() off the UI thread so the overlay never freezes."""

    finished = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, agent) -> None:
        super().__init__()
        self._agent = agent

    def ask(self, text: str) -> None:
        try:
            self.finished.emit(self._agent.chat(text))
        except Exception as exc:
            self.failed.emit(f"Something went wrong: {exc}")


class _TTSWorker(QObject):
    """
    Speaks responses aloud off the UI thread. The started/finished signals
    drive the character's talking animation, so mouth movement is in sync
    with actual speech playback (Phase 6 voice sync).
    """

    started = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self._engine = None
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", 185)
        except Exception:
            pass  # no TTS available — animation falls back to a timer

    @property
    def available(self) -> bool:
        return self._engine is not None

    def speak(self, text: str) -> None:
        if self._engine is None:
            return
        self.started.emit()
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception:
            pass
        self.finished.emit()


class TrixieOverlay(QObject):
    """Owns the character, panel, bubble, and the inference thread."""

    _request = pyqtSignal(str)
    _speak = pyqtSignal(str)

    def __init__(self, agent) -> None:
        super().__init__()
        self.character = TrixieCharacter()
        self.panel = ChatPanel()
        self.bubble = SpeechBubble()

        # Inference thread
        self._thread = QThread()
        self._worker = _InferenceWorker(agent)
        self._worker.moveToThread(self._thread)
        self._request.connect(self._worker.ask)
        self._worker.finished.connect(self._on_response)
        self._worker.failed.connect(self._on_response)
        self._thread.start()

        # TTS thread — playback state drives the talking animation
        self._tts_thread = QThread()
        self._tts = _TTSWorker()
        self._tts.moveToThread(self._tts_thread)
        self._speak.connect(self._tts.speak)
        self._tts.started.connect(lambda: self.character.set_state("talking"))
        self._tts.finished.connect(self._after_talking)
        self._tts_thread.start()

        # Wiring
        self.character.clicked.connect(self._toggle_panel)
        self.panel.message_submitted.connect(self._on_user_message)
        self.panel.closed.connect(lambda: self.character.set_state("idle"))

        # Shortcuts (active while the panel is focused)
        QShortcut(QKeySequence("Ctrl+Shift+V"), self.panel, self._toggle_vision)
        QShortcut(QKeySequence("Escape"), self.panel, self.panel.hide)

        # Sleep timer — restarts on every interaction
        self._sleep_timer = QTimer(self)
        self._sleep_timer.setSingleShot(True)
        self._sleep_timer.timeout.connect(lambda: self.character.set_state("sleeping"))
        self._sleep_timer.start(SLEEP_AFTER_MS)

        # Phase 4 — proactive trigger check
        self._proactive_timer = QTimer(self)
        self._proactive_timer.timeout.connect(self._check_proactive)
        self._proactive_timer.start(PROACTIVE_CHECK_MS)

        self.character.show()

    # ── Interaction ────────────────────────────────────────────────────────────

    def _wake(self) -> None:
        if self.character.state() == "sleeping":
            self.character.set_state("idle")
        self._sleep_timer.start(SLEEP_AFTER_MS)

    def _toggle_panel(self) -> None:
        self._wake()
        if self.panel.isVisible():
            self.panel.hide()
            self.character.set_state("idle")
        else:
            pos = self.character.pos()
            self.panel.show_near(pos.x(), pos.y())
            self.character.set_state("listening")

    def _on_user_message(self, text: str) -> None:
        self._wake()
        self.panel.add_message("user", text)
        self.panel.set_busy(True)
        self.character.set_state("thinking")
        self._request.emit(text)

    def _on_response(self, text: str) -> None:
        self.panel.set_busy(False)
        self.panel.add_message("trixie", text)
        if self._tts.available:
            # talking animation starts/stops with real speech playback
            self._speak.emit(text)
        else:
            # no TTS — approximate talking duration from text length
            self.character.set_state("talking")
            QTimer.singleShot(min(6000, 1500 + 40 * len(text)), self._after_talking)

    def _after_talking(self) -> None:
        self.character.set_state("listening" if self.panel.isVisible() else "idle")

    def _toggle_vision(self) -> None:
        from core.vision import vision
        msg = vision.toggle() if hasattr(vision, "toggle") else (
            vision.disable() if vision.enabled else vision.enable()
        )
        pos = self.character.pos()
        self.bubble.say(msg, pos.x(), pos.y())

    # ── Phase 4 — proactive presence ───────────────────────────────────────────

    def _check_proactive(self) -> None:
        if self.panel.isVisible() or self.character.state() == "sleeping":
            return  # don't interrupt an open conversation; let her sleep
        try:
            from core.patterns import check_proactive_trigger
            suggestion = check_proactive_trigger()
        except Exception:
            return
        if suggestion:
            self.character.set_state("happy")
            pos = self.character.pos()
            self.bubble.say(suggestion, pos.x(), pos.y(), ms=8000)
            QTimer.singleShot(8000, lambda: self.character.set_state("idle"))

    def shutdown(self) -> None:
        self._thread.quit()
        self._tts_thread.quit()
        self._thread.wait(2000)
        self._tts_thread.wait(2000)


def run() -> None:
    """Entry point for `python main.py --overlay`."""
    # First-run setup (model download) happens before the UI appears
    from setup.state import ensure_setup

    try:
        setup = ensure_setup()
    except RuntimeError as exc:
        print(f"[error] {exc} — run `python main.py` for details.")
        sys.exit(1)

    from core.model import get_llm
    from core.agent import TrixieAgent

    llm = get_llm(backend=setup.get("backend", "ollama"),
                  model_path=setup.get("model_path"))
    agent = TrixieAgent(llm)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # character is a Tool window
    overlay = TrixieOverlay(agent)

    from core.patterns import record_event
    record_event("session_start", "overlay")
    app.aboutToQuit.connect(overlay.shutdown)
    app.aboutToQuit.connect(lambda: record_event("session_end", "overlay"))

    sys.exit(app.exec())
