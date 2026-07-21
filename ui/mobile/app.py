"""
Trixie 2.0 — Mobile UI (Kivy).

Chat interface with:
  • First-run download screen (progress bar while GGUF downloads)
  • Bubble-style chat history (user right, Trixie left)
  • Text input + Send button
  • Status pill (Ready / Thinking… / Downloading…)
  • Settings button → vision toggle, memory view, sync

Packaged via Buildozer (Android) or Briefcase (iOS + Android).
"""

from __future__ import annotations

import threading
from pathlib import Path

# ── Kivy config must happen before any other kivy import ──────────────────────
from kivy.config import Config
Config.set("graphics", "resizable", "1")
Config.set("input", "mouse", "mouse,disable_multitouch")

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import get_color_from_hex

# ── Colour palette ─────────────────────────────────────────────────────────────
BG        = get_color_from_hex("#0f0f0f")
SURFACE   = get_color_from_hex("#1a1a1a")
TRIXIE_BG = get_color_from_hex("#1e2a3a")
USER_BG   = get_color_from_hex("#2a1e3a")
ACCENT    = get_color_from_hex("#7c6af7")
TEXT      = get_color_from_hex("#e8e8e8")
MUTED     = get_color_from_hex("#888888")
DANGER    = get_color_from_hex("#f77c7c")

Window.clearcolor = BG


# ── First-run download screen ──────────────────────────────────────────────────

class DownloadScreen(BoxLayout):
    """Full-screen download UI shown on first launch while the GGUF downloads."""

    def __init__(self, on_done, **kwargs):
        super().__init__(orientation="vertical", padding=dp(32), spacing=dp(16), **kwargs)
        self._on_done = on_done

        self.add_widget(Label(
            text="Setting up Trixie",
            font_size=dp(24),
            bold=True,
            color=TEXT,
            size_hint_y=None,
            height=dp(48),
        ))
        self.add_widget(Label(
            text="Downloading Gemma 4B — this happens once (~2.7 GB).\n"
                 "Keep the app open and stay on Wi-Fi.",
            font_size=dp(14),
            color=MUTED,
            halign="center",
            size_hint_y=None,
            height=dp(56),
        ))

        self._progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(12))
        self.add_widget(self._progress)

        self._label = Label(text="Starting…", font_size=dp(13), color=MUTED,
                            size_hint_y=None, height=dp(28))
        self.add_widget(self._label)

        # Kick off download in background thread
        threading.Thread(target=self._download, daemon=True).start()

    def _download(self):
        from setup.model_download import first_run_setup

        def _progress_cb(downloaded: int, total: int):
            if total > 0:
                pct = (downloaded / total) * 100
                mb_done = downloaded / 1_048_576
                mb_total = total / 1_048_576
                Clock.schedule_once(
                    lambda _dt: self._update_ui(pct, f"{mb_done:.0f} / {mb_total:.0f} MB"), 0
                )

        result = first_run_setup(progress_cb=_progress_cb, light_model=False)
        Clock.schedule_once(lambda _dt: self._on_done(result), 0)

    def _update_ui(self, pct: float, label: str):
        self._progress.value = pct
        self._label.text = label


# ── Chat bubble ────────────────────────────────────────────────────────────────

class ChatBubble(BoxLayout):
    def __init__(self, text: str, role: str, **kwargs):
        super().__init__(
            orientation="horizontal",
            size_hint_y=None,
            padding=(dp(8), dp(4)),
            **kwargs,
        )

        is_user = role == "user"
        bg_color = USER_BG if is_user else TRIXIE_BG
        align = "right" if is_user else "left"

        lbl = Label(
            text=text,
            color=TEXT,
            font_size=dp(15),
            text_size=(Window.width * 0.72, None),
            halign=align,
            valign="top",
            markup=True,
        )
        lbl.bind(texture_size=lambda inst, sz: setattr(inst, "size", sz))
        lbl.bind(texture_size=lambda inst, _sz: setattr(self, "height", inst.height + dp(20)))

        with lbl.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(*bg_color)
            self._rect = RoundedRectangle(pos=lbl.pos, size=lbl.size, radius=[dp(12)])
            lbl.bind(pos=lambda i, v: setattr(self._rect, "pos", v))
            lbl.bind(size=lambda i, v: setattr(self._rect, "size", v))

        spacer = Label(size_hint_x=0.25)
        if is_user:
            self.add_widget(spacer)
            self.add_widget(lbl)
        else:
            self.add_widget(lbl)
            self.add_widget(spacer)


# ── Message list ───────────────────────────────────────────────────────────────

class MessageList(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(do_scroll_x=False, **kwargs)
        self._box = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            padding=(dp(8), dp(8)),
            size_hint_y=None,
        )
        self._box.bind(minimum_height=self._box.setter("height"))
        self.add_widget(self._box)

    def add_message(self, text: str, role: str):
        bubble = ChatBubble(text=text, role=role)
        self._box.add_widget(bubble)
        Clock.schedule_once(lambda _dt: self.scroll_to(bubble), 0.1)

    def add_thinking(self) -> Label:
        lbl = Label(
            text="[i]Trixie is thinking…[/i]",
            markup=True,
            color=MUTED,
            font_size=dp(13),
            size_hint_y=None,
            height=dp(28),
            halign="left",
        )
        self._box.add_widget(lbl)
        Clock.schedule_once(lambda _dt: self.scroll_to(lbl), 0.1)
        return lbl

    def remove_widget_safe(self, widget):
        if widget in self._box.children:
            self._box.remove_widget(widget)


# ── Settings modal ─────────────────────────────────────────────────────────────

class SettingsModal(ModalView):
    def __init__(self, agent, **kwargs):
        super().__init__(size_hint=(0.9, 0.7), **kwargs)
        self._agent = agent

        layout = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(12))

        layout.add_widget(Label(
            text="Settings", font_size=dp(20), bold=True, color=TEXT,
            size_hint_y=None, height=dp(40),
        ))

        # Vision toggle
        vision_btn = Button(
            text="Vision: OFF — tap to enable",
            size_hint_y=None, height=dp(48),
            background_color=SURFACE,
        )
        def _toggle_vision(btn):
            from core.vision import vision
            msg = vision.toggle()
            btn.text = f"Vision: {'ON' if vision.enabled else 'OFF'} — {msg}"
        vision_btn.bind(on_press=_toggle_vision)
        layout.add_widget(vision_btn)

        # Memory view
        mem_btn = Button(
            text="View stored memories",
            size_hint_y=None, height=dp(48),
            background_color=SURFACE,
        )
        def _show_memory(_btn):
            from core.memory import get_recent_episodic
            facts = get_recent_episodic(10)
            content = "\n".join(facts) if facts else "No memories stored yet."
            _info_popup("Memory", content)
        mem_btn.bind(on_press=_show_memory)
        layout.add_widget(mem_btn)

        # Why last decision
        why_btn = Button(
            text="Why did Trixie do that?",
            size_hint_y=None, height=dp(48),
            background_color=SURFACE,
        )
        def _show_why(_btn):
            from core.decisions import explain_last_decision
            _info_popup("Last Decision", explain_last_decision())
        why_btn.bind(on_press=_show_why)
        layout.add_widget(why_btn)

        # Clear working memory
        reset_btn = Button(
            text="Reset conversation",
            size_hint_y=None, height=dp(48),
            background_color=SURFACE,
        )
        def _reset(_btn):
            if agent:
                agent.reset_working_memory()
            self.dismiss()
        reset_btn.bind(on_press=_reset)
        layout.add_widget(reset_btn)

        close_btn = Button(
            text="Close",
            size_hint_y=None, height=dp(44),
            background_color=DANGER,
        )
        close_btn.bind(on_press=lambda _: self.dismiss())
        layout.add_widget(close_btn)

        self.add_widget(layout)


def _info_popup(title: str, content: str):
    modal = ModalView(size_hint=(0.9, 0.6))
    box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
    box.add_widget(Label(text=title, font_size=dp(18), bold=True, color=TEXT,
                         size_hint_y=None, height=dp(36)))
    box.add_widget(Label(text=content, color=TEXT, font_size=dp(13),
                         text_size=(Window.width * 0.8, None), halign="left"))
    btn = Button(text="OK", size_hint_y=None, height=dp(44), background_color=ACCENT)
    btn.bind(on_press=lambda _: modal.dismiss())
    box.add_widget(btn)
    modal.add_widget(box)
    modal.open()


# ── Main chat screen ───────────────────────────────────────────────────────────

class ChatScreen(BoxLayout):
    def __init__(self, agent, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self._agent = agent

        # ── Top bar ────────────────────────────────────────────────────────────
        top = BoxLayout(
            size_hint_y=None, height=dp(52),
            padding=(dp(12), dp(8)),
            spacing=dp(8),
        )
        top.add_widget(Label(
            text="[b]Trixie[/b]", markup=True, font_size=dp(18), color=ACCENT,
            size_hint_x=1,
        ))
        self._status = Label(
            text="Ready", font_size=dp(12), color=MUTED,
            size_hint_x=None, width=dp(80),
        )
        top.add_widget(self._status)
        settings_btn = Button(
            text="⚙", font_size=dp(20),
            size_hint=(None, None), size=(dp(40), dp(40)),
            background_color=(0, 0, 0, 0), color=MUTED,
        )
        settings_btn.bind(on_press=lambda _: SettingsModal(agent=self._agent).open())
        top.add_widget(settings_btn)
        self.add_widget(top)

        # ── Message list ───────────────────────────────────────────────────────
        self._messages = MessageList()
        self.add_widget(self._messages)
        self._messages.add_message("Hey! I'm Trixie. How can I help?", "trixie")

        # ── Input row ──────────────────────────────────────────────────────────
        input_row = BoxLayout(
            size_hint_y=None, height=dp(56),
            padding=(dp(8), dp(6)),
            spacing=dp(8),
        )
        self._input = TextInput(
            hint_text="Message Trixie…",
            multiline=False,
            font_size=dp(15),
            background_color=SURFACE,
            foreground_color=TEXT,
            cursor_color=ACCENT,
            padding=(dp(12), dp(12)),
        )
        self._input.bind(on_text_validate=self._send)
        input_row.add_widget(self._input)

        send_btn = Button(
            text="Send",
            size_hint=(None, 1),
            width=dp(72),
            background_color=ACCENT,
            font_size=dp(14),
        )
        send_btn.bind(on_press=self._send)
        input_row.add_widget(send_btn)
        self.add_widget(input_row)

    def _send(self, *_):
        text = self._input.text.strip()
        if not text:
            return
        self._input.text = ""
        self._messages.add_message(text, "user")
        self._set_status("Thinking…")

        thinking_lbl = self._messages.add_thinking()
        threading.Thread(
            target=self._get_response,
            args=(text, thinking_lbl),
            daemon=True,
        ).start()

    def _get_response(self, text: str, thinking_lbl):
        try:
            response = self._agent.chat(text)
        except Exception as exc:
            response = f"[Sorry, something went wrong: {exc}]"
        Clock.schedule_once(lambda _dt: self._show_response(response, thinking_lbl), 0)

    def _show_response(self, response: str, thinking_lbl):
        self._messages.remove_widget_safe(thinking_lbl)
        self._messages.add_message(response, "trixie")
        self._set_status("Ready")

    def _set_status(self, text: str):
        self._status.text = text


# ── Kivy App ───────────────────────────────────────────────────────────────────

class TrixieApp(App):
    def build(self):
        self.title = "Trixie"
        self._agent = None
        self._root = BoxLayout(orientation="vertical")
        self._start_setup()
        return self._root

    def _start_setup(self):
        """Check if setup is needed; if so, show download screen first."""
        state_file = Path.home() / ".trixie" / ".setup_complete"

        if state_file.exists():
            try:
                import ast
                result = ast.literal_eval(state_file.read_text(encoding="utf-8"))
                self._launch_chat(result)
                return
            except Exception:
                pass

        # Show download screen
        dl = DownloadScreen(on_done=self._on_download_done)
        self._root.add_widget(dl)

    def _on_download_done(self, result: dict):
        if not result.get("ready"):
            self._root.clear_widgets()
            self._root.add_widget(Label(
                text="Setup failed. Check your internet connection and restart.",
                color=DANGER, font_size=dp(16),
            ))
            return
        state_file = Path.home() / ".trixie" / ".setup_complete"
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(str(result), encoding="utf-8")
        self._launch_chat(result)

    def _launch_chat(self, setup_result: dict):
        def _init():
            from core.model import get_llm
            from core.agent import TrixieAgent
            llm = get_llm(
                backend=setup_result.get("backend", "llama_cpp"),
                model_path=setup_result.get("model_path"),
            )
            agent = TrixieAgent(llm)
            Clock.schedule_once(lambda _dt: self._show_chat(agent), 0)

        threading.Thread(target=_init, daemon=True).start()

    def _show_chat(self, agent):
        self._agent = agent
        self._root.clear_widgets()
        self._root.add_widget(ChatScreen(agent=agent))


def run():
    TrixieApp().run()


if __name__ == "__main__":
    run()
