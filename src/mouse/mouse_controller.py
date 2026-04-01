"""
Mouse Controller
Translates hand landmark positions into mouse actions.

Controls (active only when mouse mode is ON):
  Move         — index fingertip (landmark 8) → cursor position
  Left click   — pinch thumb (4) + index (8)
  Right click  — pinch thumb (4) + middle (12)
  Scroll       — Pointing_Up gesture + vertical hand movement
"""

import time
import pyautogui
import numpy as np

# Never crash on fast movements to screen corner
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0          # Remove built-in delay — we control timing ourselves

# ── Screen dimensions (queried once at startup) ────────────────────────────
SCREEN_W, SCREEN_H = pyautogui.size()

# ── Smoothing ──────────────────────────────────────────────────────────────
# Exponential moving average alpha — lower = smoother but more lag
SMOOTH_ALPHA = 0.25

# ── Camera-to-screen mapping ───────────────────────────────────────────────
# Shrink the active camera zone so you don't need to reach frame edges.
# e.g. MARGIN=0.15 means the middle 70% of the frame maps to the full screen.
MARGIN = 0.15

# ── Pinch detection ────────────────────────────────────────────────────────
PINCH_THRESHOLD = 0.13     # normalised distance (fraction of palm size)
CLICK_COOLDOWN  = 0.5      # seconds between successive clicks of the same button

# ── Scroll ─────────────────────────────────────────────────────────────────
SCROLL_SENSITIVITY = 40    # how many pixels of finger movement = 1 scroll click


class MouseController:
    """Stateful per-hand mouse controller."""

    def __init__(self):
        # Smoothed cursor position
        self._smooth_x: float | None = None
        self._smooth_y: float | None = None

        # Click state
        self._last_left_click  = 0.0
        self._last_right_click = 0.0
        self._left_held        = False
        self._right_held       = False

        # Scroll state
        self._prev_scroll_y: float | None = None

    # ── Public API ─────────────────────────────────────────────────────────

    def reset(self):
        """Call when mouse mode is turned off to clear stale state."""
        self._smooth_x = None
        self._smooth_y = None
        self._prev_scroll_y = None
        self._left_held = False
        self._right_held = False

    def process(self, hand_landmarks, gesture_name: str) -> dict:
        """
        Process one frame of hand landmarks.

        Returns a dict with keys:
          cursor_px   (int, int)  — pixel position on screen
          left_click  bool        — left click fired this frame
          right_click bool        — right click fired this frame
          scrolling   bool        — scroll active this frame
          pinch_left  float       — normalised pinch distance thumb↔index
          pinch_right float       — normalised pinch distance thumb↔middle
        """
        now = time.time()
        result = {
            "cursor_px":   (0, 0),
            "left_click":  False,
            "right_click": False,
            "scrolling":   False,
            "pinch_left":  1.0,
            "pinch_right": 1.0,
        }

        palm_size = self._palm_size(hand_landmarks)
        if palm_size < 1e-5:
            return result

        # ── Cursor movement (always driven by index tip) ──────────────────
        idx_tip = hand_landmarks[8]
        sx, sy = self._to_screen(idx_tip.x, idx_tip.y)

        if self._smooth_x is None:
            self._smooth_x, self._smooth_y = float(sx), float(sy)
        else:
            self._smooth_x += SMOOTH_ALPHA * (sx - self._smooth_x)
            self._smooth_y += SMOOTH_ALPHA * (sy - self._smooth_y)

        cx, cy = int(self._smooth_x), int(self._smooth_y)
        result["cursor_px"] = (cx, cy)
        pyautogui.moveTo(cx, cy)

        # ── Scroll mode: Pointing_Up gesture → track vertical delta ───────
        if gesture_name == "Pointing_Up":
            if self._prev_scroll_y is not None:
                delta_y = idx_tip.y - self._prev_scroll_y
                scroll_clicks = -int(delta_y * SCROLL_SENSITIVITY)
                if scroll_clicks != 0:
                    pyautogui.scroll(scroll_clicks)
                    result["scrolling"] = True
            self._prev_scroll_y = idx_tip.y
            # Don't do click detection in scroll mode
            return result
        else:
            self._prev_scroll_y = None

        # ── Pinch distances ───────────────────────────────────────────────
        pinch_left  = self._pinch(hand_landmarks, 4, 8,  palm_size)
        pinch_right = self._pinch(hand_landmarks, 4, 12, palm_size)
        result["pinch_left"]  = pinch_left
        result["pinch_right"] = pinch_right

        # ── Left click (thumb ↔ index) ────────────────────────────────────
        if pinch_left < PINCH_THRESHOLD:
            if not self._left_held and now - self._last_left_click > CLICK_COOLDOWN:
                pyautogui.click(button="left")
                self._last_left_click = now
                result["left_click"] = True
            self._left_held = True
        else:
            self._left_held = False

        # ── Right click (thumb ↔ middle) ──────────────────────────────────
        if pinch_right < PINCH_THRESHOLD:
            if not self._right_held and now - self._last_right_click > CLICK_COOLDOWN:
                pyautogui.click(button="right")
                self._last_right_click = now
                result["right_click"] = True
            self._right_held = True
        else:
            self._right_held = False

        return result

    # ── Private helpers ────────────────────────────────────────────────────

    @staticmethod
    def _to_screen(norm_x: float, norm_y: float) -> tuple[int, int]:
        """Map normalised [0,1] landmark coords → screen pixel, with margin."""
        x = (norm_x - MARGIN) / (1.0 - 2 * MARGIN)
        y = (norm_y - MARGIN) / (1.0 - 2 * MARGIN)
        x = max(0.0, min(1.0, x))
        y = max(0.0, min(1.0, y))
        return int(x * SCREEN_W), int(y * SCREEN_H)

    @staticmethod
    def _palm_size(hand_landmarks) -> float:
        """Distance wrist (0) → middle MCP (9) as a normalisation factor."""
        w = hand_landmarks[0]
        m = hand_landmarks[9]
        return ((w.x - m.x) ** 2 + (w.y - m.y) ** 2) ** 0.5

    @staticmethod
    def _pinch(hand_landmarks, a: int, b: int, palm_size: float) -> float:
        """Normalised distance between landmarks a and b."""
        la, lb = hand_landmarks[a], hand_landmarks[b]
        d = ((la.x - lb.x) ** 2 + (la.y - lb.y) ** 2) ** 0.5
        return d / palm_size
