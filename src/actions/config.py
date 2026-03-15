#!/usr/bin/env python3
"""
Configuration for gesture actions
"""

from enum import Enum
from typing import Dict, Callable

class GestureAction(Enum):
    """Available gesture actions"""
    LOGOUT = "logout"
    LOCK_SCREEN = "lock_screen"
    CUSTOM = "custom"

# Default configuration for gesture actions
DEFAULT_GESTURE_CONFIG = {
    "wave": {
        "action": GestureAction.LOGOUT,
        "enabled": True,
        "cooldown_seconds": 5.0  # Prevent multiple rapid triggers
    },
    "thumbs_up": {
        "action": GestureAction.CUSTOM,
        "enabled": False,
        "custom_message": "Thumbs up detected!"
    }
}

# Action mapping
ACTION_MAPPING: Dict[GestureAction, Callable] = {}
