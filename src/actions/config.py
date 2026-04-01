#!/usr/bin/env python3
"""
Configuration for gesture-to-action mappings.
"""

from enum import Enum


class GestureAction(Enum):
    LOCK_SCREEN = "lock_screen"
    VOLUME_UP   = "volume_up"
    VOLUME_DOWN = "volume_down"
    MUTE_TOGGLE = "mute_toggle"
    SCREENSHOT  = "screenshot"


# Maps MediaPipe gesture names → action config.
# 'wave' is detected by the custom waving algorithm (not MediaPipe gestures).
DEFAULT_GESTURE_CONFIG = {
    "Thumb_Up": {
        "action": GestureAction.VOLUME_UP,
        "enabled": True,
        "cooldown_seconds": 2.0,
        "hold_seconds": 1.2,
        "description": "Hold Thumbs Up to raise volume",
    },
    "Thumb_Down": {
        "action": GestureAction.VOLUME_DOWN,
        "enabled": True,
        "cooldown_seconds": 2.0,
        "hold_seconds": 1.2,
        "description": "Hold Thumbs Down to lower volume",
    },
    "Open_Palm": {
        "action": GestureAction.SCREENSHOT,
        "enabled": True,
        "cooldown_seconds": 3.0,
        "hold_seconds": 1.5,
        "description": "Hold Open Palm to take a screenshot",
    },
    "Victory": {
        "action": GestureAction.MUTE_TOGGLE,
        "enabled": True,
        "cooldown_seconds": 2.0,
        "hold_seconds": 1.2,
        "description": "Hold Victory/Peace sign to toggle mute",
    },
    "Closed_Fist": {
        "action": GestureAction.LOCK_SCREEN,
        "enabled": True,
        "cooldown_seconds": 5.0,
        "hold_seconds": 2.0,
        "description": "Hold Closed Fist to lock the screen",
    },
}
