"""
Trixie 2.0 — Empathy engine.

Detects the user's emotional state from message content + time-of-day signals,
then returns a short instruction that shapes Trixie's response style.

Trixie does NOT perform fake empathy ("I'm so sorry you feel that way!").
She adjusts her *behaviour* — response length, tone, level of detail — based
on what the user's state calls for.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


EMOTIONAL_STATES = ["focused", "frustrated", "tired", "happy", "rushed", "neutral"]


@dataclass
class EmotionSignal:
    state: str
    confidence: float  # 0.0 – 1.0
    signals: list[str] = field(default_factory=list)


def detect_emotion(message: str, now: datetime | None = None) -> EmotionSignal:
    """
    Infer emotional state from message text + current time.
    Pure heuristics — no model inference required for this step.
    """
    if now is None:
        now = datetime.now()

    msg = message.lower().strip()
    scores: dict[str, float] = {s: 0.0 for s in EMOTIONAL_STATES}
    signals: list[str] = []

    # ── Frustration ────────────────────────────────────────────────────────────
    frustration_kw = [
        "ugh", "why", "again", "broken", "not working", "doesn't work",
        "wrong", "error", "fail", "stupid", "wtf", "bug", "issue", "problem",
    ]
    if any(kw in msg for kw in frustration_kw):
        scores["frustrated"] += 0.55
        signals.append("frustration keywords")
    if msg.count("!") > 1:
        scores["frustrated"] += 0.20
        signals.append("multiple exclamation marks")

    # ── Tiredness ──────────────────────────────────────────────────────────────
    tired_kw = ["tired", "sleepy", "exhausted", "can't think", "later", "tomorrow"]
    if any(kw in msg for kw in tired_kw):
        scores["tired"] += 0.65
        signals.append("tired keywords")
    hour = now.hour
    if 0 <= hour < 6 or hour >= 23:
        scores["tired"] += 0.30
        signals.append("late night / early morning hour")

    # ── Rushed ─────────────────────────────────────────────────────────────────
    rushed_kw = ["quick", "fast", "asap", "hurry", "urgent", "briefly", "just"]
    if any(kw in msg for kw in rushed_kw):
        scores["rushed"] += 0.65
        signals.append("urgency keywords")
    if len(msg.split()) <= 4:
        scores["rushed"] += 0.20
        signals.append("very short message")

    # ── Happy / positive ───────────────────────────────────────────────────────
    happy_kw = ["great", "awesome", "perfect", "love it", "nice", "brilliant", "thanks"]
    if any(kw in msg for kw in happy_kw):
        scores["happy"] += 0.50
        signals.append("positive sentiment")

    # ── Focused (deep work) ────────────────────────────────────────────────────
    if len(msg.split()) > 35:
        scores["focused"] += 0.30
        signals.append("long, detailed message")
    technical_kw = ["function", "class", "import", "error:", "traceback", "returns", "assert"]
    if any(kw in msg for kw in technical_kw):
        scores["focused"] += 0.20
        signals.append("technical content")

    best = max(scores, key=lambda k: scores[k])
    confidence = scores[best]

    if confidence < 0.20:
        best = "neutral"
        confidence = 0.0

    return EmotionSignal(state=best, confidence=round(confidence, 2), signals=signals)


def shape_response_instruction(emotion: str) -> str:
    """
    Return a short behavioural instruction to append to the system prompt
    based on the detected emotional state.
    """
    instructions: dict[str, str] = {
        "frustrated": (
            "The user seems frustrated. Skip any preamble. "
            "Be direct and solution-focused. One acknowledgement sentence at most, "
            "then immediately address the problem."
        ),
        "tired": (
            "The user seems tired. Keep your entire response to two sentences maximum. "
            "Offer to handle things rather than explaining how to do them."
        ),
        "rushed": (
            "The user is in a hurry. One sentence answer only. "
            "No context, no caveats, no follow-up questions unless essential."
        ),
        "happy": (
            "The user is in a good mood. Be warm and match the energy naturally."
        ),
        "focused": (
            "The user is in deep focus mode. Be minimal — brief answer, no interruptions. "
            "If the topic is non-urgent, indicate you can go deeper when they're ready."
        ),
        "neutral": "",
    }
    return instructions.get(emotion, "")
