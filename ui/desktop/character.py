"""
Trixie 2.0 — Animated desktop character (Phase 2 + 3).

Style: "minimal face" — two expressive eyes and a mouth on a soft rounded
container, drawn procedurally with QPainter. No image assets needed, which
keeps the overlay working at any size on any platform.

States:
    idle       — gentle breathing, occasional blink
    listening  — wide eyes, subtle pulse ring
    thinking   — eyes look up, orbiting dot
    talking    — mouth animates open/closed
    working    — narrowed eyes looking down
    sleeping   — closed eyes, floating z's
    happy      — curved smiling eyes, bounce
    roaming    — same face as idle; movement handled by the roam timer

Behaviour:
    • Frameless, translucent, always-on-top, not in taskbar
    • Drag anywhere to reposition (roaming pauses while dragging)
    • Left-click emits `clicked` (the app toggles the chat panel)
    • After long idle the character roams slowly along the screen edges
"""

from __future__ import annotations

import math
import random

from PyQt6.QtCore import QPoint, QPointF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

SIZE = 96          # widget is SIZE x SIZE px
FPS = 30
ROAM_AFTER_S = 90  # start roaming after this many seconds of idle
ROAM_SPEED = 1.2   # px per tick while roaming

BODY = QColor(38, 40, 48)
BODY_EDGE = QColor(96, 108, 148)
EYE = QColor(148, 196, 255)
MOUTH = QColor(148, 196, 255)
ZZZ = QColor(148, 196, 255, 180)


class TrixieCharacter(QWidget):
    """Animated character widget — frameless, always-on-top, draggable."""

    clicked = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(SIZE, SIZE)

        self._state = "idle"
        self._phase = 0.0            # global animation clock (radians-ish)
        self._blink = 0.0            # 0 = open, 1 = closed
        self._next_blink = random.uniform(2, 5)
        self._idle_ticks = 0

        self._dragging = False
        self._drag_start = QPoint()
        self._roam_target: QPointF | None = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000 // FPS)

        # start perched near the bottom-right screen edge
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - SIZE - 24, screen.bottom() - SIZE - 24)

    # ── State API ──────────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self._idle_ticks = 0
            if state != "roaming":
                self._roam_target = None
            self.update()

    def state(self) -> str:
        return self._state

    # ── Animation clock ────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self._phase += 2 * math.pi / (FPS * 3)  # one slow cycle ≈ 3 s

        # Blinking (only when eyes are open states)
        if self._state in ("idle", "listening", "roaming", "happy"):
            self._next_blink -= 1 / FPS
            if self._next_blink <= 0:
                self._blink = 1.0
                self._next_blink = random.uniform(2.5, 6)
        self._blink = max(0.0, self._blink - 4 / FPS)

        # Idle → roaming after a while (Phase 3 roaming behaviour)
        if self._state == "idle" and not self._dragging:
            self._idle_ticks += 1
            if self._idle_ticks > ROAM_AFTER_S * FPS:
                self.set_state("roaming")
        if self._state == "roaming" and not self._dragging:
            self._roam_step()

        self.update()

    # ── Roaming (Phase 3) ──────────────────────────────────────────────────────

    def _edge_point(self) -> QPointF:
        """Random point along the screen edges (with margin)."""
        s = QApplication.primaryScreen().availableGeometry()
        m = 24
        edge = random.choice(("bottom", "left", "right"))
        if edge == "bottom":
            return QPointF(random.uniform(s.left() + m, s.right() - SIZE - m),
                           s.bottom() - SIZE - m)
        if edge == "left":
            return QPointF(s.left() + m,
                           random.uniform(s.top() + m, s.bottom() - SIZE - m))
        return QPointF(s.right() - SIZE - m,
                       random.uniform(s.top() + m, s.bottom() - SIZE - m))

    def _roam_step(self) -> None:
        if self._roam_target is None:
            self._roam_target = self._edge_point()
        pos = QPointF(self.pos())
        delta = self._roam_target - pos
        dist = math.hypot(delta.x(), delta.y())
        if dist < 4:
            # arrived — pause here, look around, pick a new target later
            if random.random() < 0.005:
                self._roam_target = self._edge_point()
            return
        step = min(ROAM_SPEED, dist)
        pos += delta / dist * step
        self.move(int(pos.x()), int(pos.y()))

    # ── Mouse ──────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self._drag_start = event.globalPosition().toPoint()
            if self._state == "roaming":
                self.set_state("idle")

    def mouseMoveEvent(self, event) -> None:
        delta = event.globalPosition().toPoint() - self._drag_start
        if self._dragging or delta.manhattanLength() > 4:
            self._dragging = True
            self.move(self.pos() + delta)
            self._drag_start = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._dragging:
            self.clicked.emit()
        self._dragging = False
        self._idle_ticks = 0

    # ── Drawing ────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        breath = math.sin(self._phase) * 2           # breathing offset
        bounce = 0.0
        if self._state == "happy":
            bounce = abs(math.sin(self._phase * 4)) * 6
        cx, cy = SIZE / 2, SIZE / 2 + breath - bounce

        # Soft rounded body
        r = SIZE * 0.38
        p.setPen(QPen(BODY_EDGE, 2))
        p.setBrush(QBrush(BODY))
        p.drawEllipse(QPointF(cx, cy), r, r * (1 + 0.02 * math.sin(self._phase)))

        # Listening pulse ring
        if self._state == "listening":
            pulse = (math.sin(self._phase * 3) + 1) / 2
            ring = QColor(EYE)
            ring.setAlpha(int(90 * (1 - pulse)))
            p.setPen(QPen(ring, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r + 4 + pulse * 8, r + 4 + pulse * 8)

        self._draw_eyes(p, cx, cy)
        self._draw_mouth(p, cx, cy)

        # Thinking: orbiting dot
        if self._state == "thinking":
            a = self._phase * 3
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(EYE))
            p.drawEllipse(
                QPointF(cx + math.cos(a) * (r + 8), cy - r - 4 + math.sin(a) * 4),
                3, 3,
            )

        # Sleeping: floating z's
        if self._state == "sleeping":
            p.setPen(QPen(ZZZ, 2))
            font = p.font()
            for i in range(3):
                t = (self._phase * 0.5 + i * 0.8) % 2.4
                font.setPointSize(7 + i * 2)
                p.setFont(font)
                p.drawText(
                    QPointF(cx + r * 0.5 + i * 8, cy - r * 0.6 - t * 10),
                    "z",
                )
        p.end()

    def _draw_eyes(self, p: QPainter, cx: float, cy: float) -> None:
        gap = SIZE * 0.14
        ey = cy - SIZE * 0.06
        ew, eh = SIZE * 0.075, SIZE * 0.105

        if self._state == "sleeping" or self._blink > 0.3:
            # closed eyes — flat lines
            p.setPen(QPen(EYE, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for sx in (-1, 1):
                x = cx + sx * gap
                p.drawLine(QPointF(x - ew, ey), QPointF(x + ew, ey))
            return

        if self._state == "happy":
            # upward arcs
            p.setPen(QPen(EYE, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for sx in (-1, 1):
                x = cx + sx * gap
                p.drawArc(int(x - ew), int(ey - eh / 2), int(ew * 2), int(eh),
                          30 * 16, 120 * 16)
            return

        # open eyes, with per-state pupil offset / squint
        dy = 0.0
        squint = 1.0
        if self._state == "thinking":
            dy = -eh * 0.4
        elif self._state == "working":
            dy = eh * 0.4
            squint = 0.55
        elif self._state == "listening":
            squint = 1.25

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(EYE))
        for sx in (-1, 1):
            p.drawEllipse(QPointF(cx + sx * gap, ey + dy), ew, eh * squint)

    def _draw_mouth(self, p: QPainter, cx: float, cy: float) -> None:
        my = cy + SIZE * 0.13
        mw = SIZE * 0.11

        p.setPen(QPen(MOUTH, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._state == "talking":
            openness = (math.sin(self._phase * 8) + 1) / 2
            h = 2 + openness * SIZE * 0.08
            p.setBrush(QBrush(MOUTH))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, my), mw * 0.6, h / 2)
        elif self._state in ("happy",):
            p.drawArc(int(cx - mw), int(my - mw * 0.6), int(mw * 2), int(mw * 1.2),
                      -160 * 16, 140 * 16)
        elif self._state == "sleeping":
            p.drawEllipse(QPointF(cx, my), 3, 3)
        elif self._state == "working":
            p.drawLine(QPointF(cx - mw * 0.6, my), QPointF(cx + mw * 0.6, my))
        else:  # idle / listening / thinking / roaming — small soft smile
            p.drawArc(int(cx - mw * 0.8), int(my - mw * 0.5), int(mw * 1.6), int(mw),
                      -150 * 16, 120 * 16)
