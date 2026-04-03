import os
import sys
import time

import cv2
import mediapipe as mp

# Add src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from actions.system_operations import SystemOperations
from mouse.mouse_controller import MouseController
from utils.notifier import notify

# ─── MediaPipe Setup ───────────────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
    "gesture_recognizer.task",
)

options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)
recognizer = GestureRecognizer.create_from_options(options)

# ─── System Gesture Config ─────────────────────────────────────────────────
GESTURE_ACTIONS = {
    "Thumb_Up": {"action": "volume_up", "hold": 1.2, "cooldown": 2.0, "label": "Volume Up"},
    "Thumb_Down": {"action": "volume_down", "hold": 1.2, "cooldown": 2.0, "label": "Volume Down"},
    "Open_Palm": {"action": "screenshot", "hold": 1.5, "cooldown": 3.0, "label": "Screenshot"},
    "Victory": {"action": "mute_toggle", "hold": 1.2, "cooldown": 2.0, "label": "Mute Toggle"},
    "Closed_Fist": {"action": "lock_screen", "hold": 2.0, "cooldown": 5.0, "label": "Lock Screen"},
}

last_action_time = {k: 0.0 for k in GESTURE_ACTIONS}
gesture_hold_start = [None, None]
gesture_hold_name = [None, None]

# ─── Mouse Mode State ──────────────────────────────────────────────────────
MAX_HANDS = 2
mouse_mode = [False] * MAX_HANDS
mouse_ctrl = [MouseController(), MouseController()]
_was_dragging = [False] * MAX_HANDS

MOUSE_TOGGLE_HOLD_S = 1.2
mouse_toggle_start = [None] * MAX_HANDS
mouse_toggle_gesture = "ILoveYou"


# ─── Static Gesture Hold Detection ────────────────────────────────────────
def detect_static_gesture(gesture_name, hand_idx, now_s):
    if gesture_name not in GESTURE_ACTIONS:
        gesture_hold_start[hand_idx] = None
        gesture_hold_name[hand_idx] = None
        return False, 0.0

    cfg = GESTURE_ACTIONS[gesture_name]

    if gesture_hold_name[hand_idx] != gesture_name:
        gesture_hold_start[hand_idx] = now_s
        gesture_hold_name[hand_idx] = gesture_name

    held_for = now_s - gesture_hold_start[hand_idx]
    hold_progress = min(held_for / cfg["hold"], 1.0)
    in_cooldown = now_s - last_action_time[gesture_name] < cfg["cooldown"]
    triggered = held_for >= cfg["hold"] and not in_cooldown

    if triggered:
        last_action_time[gesture_name] = now_s
        gesture_hold_start[hand_idx] = now_s

    return triggered, hold_progress


# ─── Mouse Toggle Hold Detection ──────────────────────────────────────────
def detect_mouse_toggle(gesture_name, hand_idx, now_s):
    if gesture_name != mouse_toggle_gesture:
        mouse_toggle_start[hand_idx] = None
        return False, 0.0

    if mouse_toggle_start[hand_idx] is None:
        mouse_toggle_start[hand_idx] = now_s

    held_for = now_s - mouse_toggle_start[hand_idx]
    progress = min(held_for / MOUSE_TOGGLE_HOLD_S, 1.0)

    if held_for >= MOUSE_TOGGLE_HOLD_S:
        mouse_toggle_start[hand_idx] = None
        return True, 1.0

    return False, progress


# ─── Action Dispatch ───────────────────────────────────────────────────────
def dispatch_action(action_name, hand_idx):
    print(f"[MiMi] Action '{action_name}' triggered by hand {hand_idx + 1}")
    actions = {
        "lock_screen": SystemOperations.lock_screen,
        "volume_up": SystemOperations.volume_up,
        "volume_down": SystemOperations.volume_down,
        "mute_toggle": SystemOperations.mute_toggle,
        "screenshot": SystemOperations.take_screenshot,
    }
    fn = actions.get(action_name)
    if fn:
        fn()
    else:
        print(f"[MiMi] Unknown action: {action_name}")


# ─── Camera Setup ──────────────────────────────────────────────────────────
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    for idx in [1, 2]:
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            print(f"[MiMi] Opened camera at index {idx}")
            break
    else:
        print("[MiMi] ERROR: No camera found. Exiting.")
        sys.exit(1)

INACTIVITY_TIMEOUT_S = 5.0
last_hand_seen_t = time.time()

notify("MiMi Assistant", "Camera is active — gesture control ready")
print("[MiMi] Camera ready (headless — no GUI window).")

# ─── Main Loop ─────────────────────────────────────────────────────────────
while True:
    ret, frame = cap.read()
    if not ret:
        print("[MiMi] Camera read failed. Exiting.")
        break

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    timestamp_ms = int(time.time() * 1000)
    recognition_result = recognizer.recognize_for_video(mp_image, timestamp_ms)
    now_s = time.time()

    if recognition_result.hand_landmarks:
        last_hand_seen_t = now_s

        all_gesture_names = []
        for i in range(len(recognition_result.hand_landmarks)):
            if recognition_result.gestures and i < len(recognition_result.gestures):
                all_gesture_names.append(recognition_result.gestures[i][0].category_name)
            else:
                all_gesture_names.append("None")

        for idx, hand_landmarks in enumerate(recognition_result.hand_landmarks):
            gesture_name = all_gesture_names[idx]

            # ── ILoveYou → toggle mouse mode ────────────────────────────
            toggled, _ = detect_mouse_toggle(gesture_name, idx, now_s)
            if toggled:
                mouse_mode[idx] = not mouse_mode[idx]
                if mouse_mode[idx]:
                    print(f"[MiMi] Hand {idx + 1}: Mouse mode ON")
                    notify("MiMi Assistant", "Mouse Mode ON")
                else:
                    print(f"[MiMi] Hand {idx + 1}: Mouse mode OFF")
                    mouse_ctrl[idx].reset()
                    notify("MiMi Assistant", "Mouse Mode OFF")

            # ── Mouse mode branch ────────────────────────────────────────
            if mouse_mode[idx]:
                drag_trigger = any(
                    all_gesture_names[i] == "Pointing_Up"
                    for i in range(len(all_gesture_names))
                    if i != idx
                )
                mouse_result = mouse_ctrl[idx].process(
                    hand_landmarks, gesture_name, drag_trigger
                )

                if mouse_result["double_click"]:
                    notify("MiMi Assistant", "Double Click")
                elif mouse_result["dragging"] and not _was_dragging[idx]:
                    notify("MiMi Assistant", "Dragging")
                elif mouse_result["left_click"]:
                    notify("MiMi Assistant", "Left Click")
                elif mouse_result["right_click"]:
                    notify("MiMi Assistant", "Right Click")
                _was_dragging[idx] = mouse_result["dragging"]

            # ── Normal gesture branch ────────────────────────────────────
            else:
                hold_triggered, _ = detect_static_gesture(gesture_name, idx, now_s)
                if hold_triggered:
                    action = GESTURE_ACTIONS[gesture_name]["action"]
                    label = GESTURE_ACTIONS[gesture_name]["label"]
                    dispatch_action(action, idx)
                    notify("MiMi Assistant", label)

    # ── Inactivity ─────────────────────────────────────────────────────
    idle_s = now_s - last_hand_seen_t
    if idle_s >= INACTIVITY_TIMEOUT_S:
        print("[MiMi] No hand detected — closing camera.")
        break

cap.release()
recognizer.close()
