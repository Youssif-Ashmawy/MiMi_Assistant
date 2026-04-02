"""
Mouse Controller
Translates hand landmark positions into mouse actions.

Controls (active only when mouse mode is ON for a hand):
  Move         — index fingertip (landmark 8) → cursor position
  Left click   — pinch thumb+index, stay still, release before 1.4s
  Double click — pinch thumb+index, stay still, hold 1.4s
  Drag & drop  — pinch thumb+index (Hand 1) + other hand Pointing_Up (Hand 2)
                 → grabs item; drop when Hand 2 leaves Pointing_Up
  Right click  — pinch thumb+middle
  Scroll up    — Thumb_Down gesture
  Scroll down  — Thumb_Up gesture
"""

import time
import pyautogui
import numpy as np

try:
    from Quartz.CoreGraphics import (
        CGEventCreateMouseEvent,
        CGEventPost,
        CGEventSetIntegerValueField,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGEventLeftMouseDragged,
        kCGMouseEventClickState,
        kCGHIDEventTap,
    )
    _HAS_QUARTZ = True
except ImportError:
    _HAS_QUARTZ = False

pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

SCREEN_W, SCREEN_H = pyautogui.size()

SMOOTH_ALPHA        = 0.25
MARGIN              = 0.15
PINCH_THRESHOLD     = 0.13
CLICK_COOLDOWN      = 0.5
DOUBLE_CLICK_HOLD_S = 1.4
SCROLL_AMOUNT       = 5
SCROLL_TICK_S       = 0.12


class MouseController:
    """Stateful per-hand mouse controller."""

    _IDLE     = "idle"
    _PINCHING = "pinching"   # pinch held, no drag trigger yet
    _DRAGGING = "dragging"   # mousedown sent, following hand

    def __init__(self):
        self._smooth_x: float | None = None
        self._smooth_y: float | None = None

        self._left_state         = self._IDLE
        self._pinch_start_t:     float = 0.0
        self._pinch_origin_x:    int   = 0
        self._pinch_origin_y:    int   = 0
        self._double_click_fired       = False
        self._last_left_click:   float = 0.0

        self._right_held               = False
        self._last_right_click:  float = 0.0

        self._last_scroll_t:     float = 0.0

    # ── Public ────────────────────────────────────────────────────────────

    def reset(self):
        if self._left_state == self._DRAGGING:
            self._quartz_mouse_up(self._pinch_origin_x, self._pinch_origin_y)
        self._smooth_x = self._smooth_y = None
        self._left_state = self._IDLE
        self._right_held = False

    def process(self, hand_landmarks, gesture_name: str,
                drag_trigger: bool = False) -> dict:
        """
        Process one frame.

        drag_trigger — True when the *other* hand is showing Pointing_Up.

        Returns dict with keys:
          cursor_px, left_click, double_click, dragging,
          right_click, scrolling, pinch_left, pinch_right, pinch_progress
        """
        now = time.time()
        result = {
            "cursor_px":      (0, 0),
            "left_click":     False,
            "double_click":   False,
            "dragging":       False,
            "right_click":    False,
            "scrolling":      False,
            "pinch_left":     1.0,
            "pinch_right":    1.0,
            "pinch_progress": 0.0,
        }

        palm_size = self._palm_size(hand_landmarks)
        if palm_size < 1e-5:
            return result

        # ── Smooth cursor ─────────────────────────────────────────────────
        idx_tip = hand_landmarks[8]
        sx, sy  = self._to_screen(idx_tip.x, idx_tip.y)
        if self._smooth_x is None:
            self._smooth_x, self._smooth_y = float(sx), float(sy)
        else:
            self._smooth_x += SMOOTH_ALPHA * (sx - self._smooth_x)
            self._smooth_y += SMOOTH_ALPHA * (sy - self._smooth_y)
        cx, cy = int(self._smooth_x), int(self._smooth_y)
        result["cursor_px"] = (cx, cy)

        # ── Scroll ────────────────────────────────────────────────────────
        if gesture_name in ("Thumb_Up", "Thumb_Down"):
            if now - self._last_scroll_t >= SCROLL_TICK_S:
                direction = -1 if gesture_name == "Thumb_Up" else 1
                pyautogui.scroll(direction * SCROLL_AMOUNT)
                self._last_scroll_t = now
                result["scrolling"] = True
            return result

        # ── Pinch distances ───────────────────────────────────────────────
        pinch_left  = self._pinch(hand_landmarks, 4, 8,  palm_size)
        pinch_right = self._pinch(hand_landmarks, 4, 12, palm_size)
        result["pinch_left"]  = pinch_left
        result["pinch_right"] = pinch_right

        # ── Left pinch state machine ──────────────────────────────────────

        # DRAGGING is checked first and is independent of pinch state —
        # only drag_trigger (other hand Pointing_Up) controls grab/drop.
        if self._left_state == self._DRAGGING:
            if not drag_trigger:
                # Other hand lowered → drop
                self._quartz_mouse_up(cx, cy)
                self._left_state = self._IDLE
            else:
                self._quartz_drag(cx, cy)
                result["dragging"] = True

        else:
            pinching = pinch_left < PINCH_THRESHOLD

            if pinching:
                # IDLE → PINCHING
                if self._left_state == self._IDLE:
                    self._left_state         = self._PINCHING
                    self._pinch_start_t      = now
                    self._pinch_origin_x     = cx
                    self._pinch_origin_y     = cy
                    self._double_click_fired = False

                # PINCHING
                if self._left_state == self._PINCHING:
                    held_for = now - self._pinch_start_t
                    result["pinch_progress"] = min(held_for / DOUBLE_CLICK_HOLD_S, 1.0)

                    if drag_trigger:
                        # Other hand signals grab → start drag
                        self._left_state = self._DRAGGING
                        self._quartz_mouse_down(self._pinch_origin_x, self._pinch_origin_y)

                    elif held_for >= DOUBLE_CLICK_HOLD_S and not self._double_click_fired:
                        if now - self._last_left_click > CLICK_COOLDOWN:
                            self._quartz_double_click(self._pinch_origin_x,
                                                      self._pinch_origin_y)
                            self._last_left_click    = now
                            self._double_click_fired = True
                            result["double_click"]   = True

            else:
                # Pinch released
                if self._left_state == self._PINCHING and not self._double_click_fired:
                    if now - self._last_left_click > CLICK_COOLDOWN:
                        self._quartz_click(self._pinch_origin_x, self._pinch_origin_y)
                        self._last_left_click = now
                        result["left_click"]  = True

                self._left_state = self._IDLE

        # Move cursor only in IDLE (Quartz drag events handle it otherwise,
        # and we freeze it during PINCHING for click accuracy)
        if self._left_state == self._IDLE:
            pyautogui.moveTo(cx, cy)

        # ── Right click ───────────────────────────────────────────────────
        if pinch_right < PINCH_THRESHOLD:
            if not self._right_held and now - self._last_right_click > CLICK_COOLDOWN:
                pyautogui.click(button="right")
                self._last_right_click = now
                result["right_click"]  = True
            self._right_held = True
        else:
            self._right_held = False

        return result

    # ── Quartz helpers ────────────────────────────────────────────────────

    @staticmethod
    def _quartz_event(event_type, x: int, y: int, click_count: int = 1):
        if not _HAS_QUARTZ:
            return
        point = (float(x), float(y))
        evt   = CGEventCreateMouseEvent(None, event_type, point, 0)
        CGEventSetIntegerValueField(evt, kCGMouseEventClickState, click_count)
        CGEventPost(kCGHIDEventTap, evt)

    def _quartz_mouse_down(self, x, y):
        self._quartz_event(kCGEventLeftMouseDown, x, y)

    def _quartz_mouse_up(self, x, y):
        self._quartz_event(kCGEventLeftMouseUp, x, y)

    def _quartz_drag(self, x, y):
        self._quartz_event(kCGEventLeftMouseDragged, x, y)

    def _quartz_click(self, x, y):
        self._quartz_event(kCGEventLeftMouseDown, x, y)
        self._quartz_event(kCGEventLeftMouseUp,   x, y)

    def _quartz_double_click(self, x, y):
        for count in (1, 2):
            self._quartz_event(kCGEventLeftMouseDown, x, y, count)
            self._quartz_event(kCGEventLeftMouseUp,   x, y, count)
            if count == 1:
                time.sleep(0.05)

    # ── Other helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _to_screen(nx, ny):
        x = (nx - MARGIN) / (1.0 - 2 * MARGIN)
        y = (ny - MARGIN) / (1.0 - 2 * MARGIN)
        return (int(max(0.0, min(1.0, x)) * SCREEN_W),
                int(max(0.0, min(1.0, y)) * SCREEN_H))

    @staticmethod
    def _palm_size(lm):
        w, m = lm[0], lm[9]
        return ((w.x - m.x) ** 2 + (w.y - m.y) ** 2) ** 0.5

    @staticmethod
    def _pinch(lm, a, b, palm_size):
        la, lb = lm[a], lm[b]
        return ((la.x - lb.x) ** 2 + (la.y - lb.y) ** 2) ** 0.5 / palm_size
