"""
Trixie 2.0 — Vision system.

Trixie can see your screen — but only when you allow it.

  Default state : OFF
  Toggle voice  : "Hey Trixie, you can look" / "Trixie, stop watching"
  Toggle hotkey : Ctrl+Shift+V (wired up in the UI layer)
  Toggle UI     : Settings → Vision → On / Off / Active-window only

Privacy guarantees:
  • Screenshots are NEVER written to disk.
  • The raw image is converted to a one-sentence text description and
    then immediately discarded.
  • Only the text description may be stored in episodic memory (if relevant).
  • Trixie announces every time vision is activated.
"""

from __future__ import annotations

import base64
import io


class VisionSystem:
    def __init__(self) -> None:
        self._enabled = False

    # ── Public toggle ──────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> str:
        self._enabled = True
        return "Vision enabled — I can now see your screen."

    def disable(self) -> str:
        self._enabled = False
        return "Vision disabled — I can no longer see your screen."

    def toggle(self) -> str:
        return self.enable() if not self._enabled else self.disable()

    # ── Capture ────────────────────────────────────────────────────────────────

    def capture_jpeg_b64(self, max_width: int = 1280, max_height: int = 800) -> str | None:
        """
        Capture the primary monitor and return a base-64-encoded JPEG string.
        Returns None if vision is off or capture fails.

        The returned string is NEVER written to disk — callers must discard it
        after passing it to the model.
        """
        if not self._enabled:
            return None
        try:
            import mss
            from PIL import Image

            with mss.mss() as sct:
                raw = sct.grab(sct.monitors[0])

            img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
            img.thumbnail((max_width, max_height))

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            return base64.b64encode(buf.getvalue()).decode()
        except ImportError:
            print("[vision] mss or Pillow not installed — vision unavailable.")
            return None
        except Exception as exc:
            print(f"[vision] Capture error: {exc}")
            return None

    # ── Describe ───────────────────────────────────────────────────────────────

    def describe_context(self, llm=None) -> str:
        """
        Capture the screen, describe it in one sentence, discard the image.

        Args:
            llm: A LangChain chat model with vision support (e.g. llava or
                 gemma3-vision via Ollama). If None, returns a placeholder.

        Returns:
            A one-sentence plain-text description of what the user is doing.
            The image is never stored.
        """
        if not self._enabled:
            return "Vision is off. The user has not enabled screen access."

        img_b64 = self.capture_jpeg_b64()
        if img_b64 is None:
            return "Could not capture screen."

        if llm is None:
            return "(Vision model not configured — screen captured but not described.)"

        try:
            from langchain_core.messages import HumanMessage

            msg = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": (
                            "Describe what the user is currently working on "
                            "in one brief sentence. Focus on the active application "
                            "and visible task."
                        ),
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    },
                ]
            )
            response = llm.invoke([msg])
            description = (
                response.content
                if hasattr(response, "content")
                else str(response)
            )
            # img_b64 goes out of scope here — never written to disk
            return description.strip()
        except Exception as exc:
            return f"Could not describe screen: {exc}"


# ── Module-level singleton ─────────────────────────────────────────────────────
# Import and use this instance everywhere — do not create new VisionSystem objects.
vision = VisionSystem()
