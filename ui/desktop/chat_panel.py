"""
Trixie 2.0 — Expandable chat panel + speech bubble (Phase 2).

The panel is a frameless, rounded dark card that appears next to the
character when clicked and collapses when dismissed. The speech bubble
is a lightweight label used for short proactive nudges — it fades out
on its own after a few seconds.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

PANEL_W, PANEL_H = 320, 420

_PANEL_QSS = """
QFrame#card {
    background-color: rgba(30, 32, 40, 235);
    border: 1px solid rgba(96, 108, 148, 160);
    border-radius: 14px;
}
QLabel { color: #e8ecf4; font-size: 13px; }
QLabel#bubble_user {
    background: #2a4a7a; border-radius: 10px; padding: 7px 10px;
}
QLabel#bubble_trixie {
    background: #34363f; border-radius: 10px; padding: 7px 10px;
}
QLineEdit {
    background: #23252d; color: #e8ecf4; border: 1px solid #4a4e5c;
    border-radius: 9px; padding: 7px 10px; font-size: 13px;
}
QPushButton {
    background: #3a6ea5; color: white; border: none;
    border-radius: 9px; padding: 7px 14px; font-size: 13px;
}
QPushButton:hover { background: #4a7eb5; }
"""


class ChatPanel(QWidget):
    """Frameless chat card. Emits `message_submitted(str)` on send."""

    message_submitted = pyqtSignal(str)
    closed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(PANEL_W, PANEL_H)
        self.setStyleSheet(_PANEL_QSS)

        card = QFrame(self)
        card.setObjectName("card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("Trixie")
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #9aa2b4; font-size: 16px; }"
            "QPushButton:hover { color: white; }"
        )
        close_btn.clicked.connect(self._close)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(close_btn)
        layout.addLayout(header)

        # Message list
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._list_host = QWidget()
        self._list_host.setStyleSheet("background: transparent;")
        self._list = QVBoxLayout(self._list_host)
        self._list.setContentsMargins(0, 0, 4, 0)
        self._list.setSpacing(6)
        self._list.addStretch()
        self._scroll.setWidget(self._list_host)
        layout.addWidget(self._scroll, 1)

        # Input row
        row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Trixie…")
        self._input.returnPressed.connect(self._send)
        send = QPushButton("Send")
        send.clicked.connect(self._send)
        row.addWidget(self._input, 1)
        row.addWidget(send)
        layout.addLayout(row)

    # ── API ────────────────────────────────────────────────────────────────────

    def add_message(self, role: str, text: str) -> None:
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setObjectName("bubble_user" if role == "user" else "bubble_trixie")
        bubble.setMaximumWidth(int(PANEL_W * 0.8))

        row = QHBoxLayout()
        if role == "user":
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()
        # insert above the trailing stretch
        self._list.insertLayout(self._list.count() - 1, row)
        QTimer.singleShot(30, self._scroll_to_bottom)

    def set_busy(self, busy: bool) -> None:
        self._input.setEnabled(not busy)
        self._input.setPlaceholderText("Trixie is thinking…" if busy else "Ask Trixie…")

    def show_near(self, anchor_x: int, anchor_y: int) -> None:
        """Position the panel next to the character, staying on screen."""
        from PyQt6.QtWidgets import QApplication
        s = QApplication.primaryScreen().availableGeometry()
        x = anchor_x - PANEL_W - 12
        if x < s.left():
            x = anchor_x + 108
        y = min(max(anchor_y - PANEL_H + 96, s.top() + 8), s.bottom() - PANEL_H - 8)
        self.move(x, y)
        self.show()
        self._input.setFocus()

    # ── Internal ───────────────────────────────────────────────────────────────

    def _send(self) -> None:
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self.message_submitted.emit(text)

    def _close(self) -> None:
        self.hide()
        self.closed.emit()

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())


class SpeechBubble(QLabel):
    """Short-lived bubble near the character; fades after 5 seconds."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWordWrap(True)
        self.setMaximumWidth(240)
        self.setStyleSheet(
            "background: rgba(30, 32, 40, 235); color: #e8ecf4;"
            "border: 1px solid rgba(96, 108, 148, 160); border-radius: 10px;"
            "padding: 8px 12px; font-size: 12px;"
        )
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def say(self, text: str, anchor_x: int, anchor_y: int, ms: int = 5000) -> None:
        self.setText(text)
        self.adjustSize()
        from PyQt6.QtWidgets import QApplication
        s = QApplication.primaryScreen().availableGeometry()
        x = max(s.left() + 8, min(anchor_x - self.width() - 8, s.right() - self.width() - 8))
        y = max(s.top() + 8, anchor_y - self.height() - 8)
        self.move(x, y)
        self.show()
        self._hide_timer.start(ms)
