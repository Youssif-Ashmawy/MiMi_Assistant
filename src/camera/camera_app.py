import os
import sys
import time

import cv2
import mediapipe as mp
import numpy as np

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

GESTURE_COLORS = {
    "Thumb_Up": (100, 255, 100),
    "Thumb_Down": (100, 100, 255),
    "Open_Palm": (0, 200, 255),
    "Victory": (255, 50, 200),
    "Closed_Fist": (0, 0, 255),
    "ILoveYou": (0, 200, 200),
    "Pointing_Up": (255, 200, 0),
    "None": (160, 160, 160),
}

# ─── Mouse Mode State ──────────────────────────────────────────────────────
MAX_HANDS = 2
mouse_mode = [False] * MAX_HANDS
mouse_ctrl = [MouseController(), MouseController()]
_was_dragging = [False] * MAX_HANDS

MOUSE_TOGGLE_HOLD_S = 1.2
mouse_toggle_start = [None] * MAX_HANDS
mouse_toggle_gesture = "ILoveYou"

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]
PALM_LANDMARKS = [0, 5, 9, 13, 17]


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


# ─── Drawing Helpers ───────────────────────────────────────────────────────
def draw_hand_skeleton(frame, hand_landmarks, color):
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]
    for a, b in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], color, 2, cv2.LINE_AA)
    for i, (x, y) in enumerate(pts):
        r = 7 if i == 0 else 4
        cv2.circle(frame, (x, y), r, color, -1)
        cv2.circle(frame, (x, y), r, (255, 255, 255), 1)


def draw_hold_arc(frame, hand_landmarks, progress, color):
    h, w = frame.shape[:2]
    cx = int(np.mean([hand_landmarks[i].x for i in PALM_LANDMARKS]) * w)
    cy = int(np.mean([hand_landmarks[i].y for i in PALM_LANDMARKS]) * h)
    angle = int(360 * progress)
    cv2.ellipse(frame, (cx, cy), (32, 32), -90, 0, angle, color, 4, cv2.LINE_AA)
    cv2.ellipse(frame, (cx, cy), (32, 32), -90, angle, 360, (80, 80, 80), 2, cv2.LINE_AA)


def draw_mouse_hud(frame, hand_landmarks, mouse_result):
    h, w = frame.shape[:2]
    tip = hand_landmarks[8]
    tx, ty = int(tip.x * w), int(tip.y * h)

    cv2.drawMarker(frame, (tx, ty), (0, 255, 255), cv2.MARKER_CROSS, 24, 2, cv2.LINE_AA)

    progress = mouse_result["pinch_progress"]
    if progress > 0.0:
        angle = int(360 * progress)
        arc_col = (0, 255, 0) if progress < 1.0 else (0, 255, 255)
        cv2.ellipse(frame, (tx, ty), (20, 20), -90, 0, angle, arc_col, 3, cv2.LINE_AA)
        if progress >= 1.0:
            cv2.putText(frame, "DOUBLE CLICK", (tx + 22, ty - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2, cv2.LINE_AA)

    lcol = (0, 255, 0) if mouse_result["pinch_left"] < 0.13 else (120, 120, 120)
    cv2.circle(frame, (tx - 18, ty - 18), 8, lcol, -1)

    rcol = (0, 0, 255) if mouse_result["pinch_right"] < 0.13 else (120, 120, 120)
    cv2.circle(frame, (tx + 18, ty - 18), 8, rcol, -1)

    if mouse_result["scrolling"]:
        cv2.putText(frame, "SCROLL", (tx + 20, ty),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 200, 0), 2, cv2.LINE_AA)


def draw_mouse_mode_border(frame):
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (3, 3), (w - 3, h - 3), (0, 200, 255), 4)
    cv2.putText(frame, "MOUSE MODE", (w // 2 - 80, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2, cv2.LINE_AA)


def draw_legend(frame, any_mouse_mode):
    h, w = frame.shape[:2]
    lines = list(GESTURE_ACTIONS.items())
    mouse_line = ("ILoveYou", {"label": "Toggle Mouse Mode", "hold": MOUSE_TOGGLE_HOLD_S})
    all_lines = [mouse_line] + lines

    panel_w, line_h = 320, 22
    start_y = h - len(all_lines) * line_h - 20

    overlay = frame.copy()
    cv2.rectangle(overlay, (w - panel_w - 10, start_y - 10), (w - 5, h - 10), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for i, (gname, cfg) in enumerate(all_lines):
        col = GESTURE_COLORS.get(gname, (200, 200, 200))
        cv2.putText(frame, f"{gname}: {cfg['label']} ({cfg['hold']}s)",
                    (w - panel_w - 5, start_y + i * line_h),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)

    if any_mouse_mode:
        mouse_guide = [
            "  Move:        index fingertip",
            "  Left click:  thumb+index pinch",
            "  Right click: thumb+middle pinch",
            "  Scroll:      Pointing_Up + move",
        ]
        gy = start_y - len(mouse_guide) * 18 - 8
        for j, gl in enumerate(mouse_guide):
            cv2.putText(frame, gl, (w - panel_w - 5, gy + j * 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 200, 255), 1, cv2.LINE_AA)


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

messages = []
INACTIVITY_TIMEOUT_S = 5.0
last_hand_seen_t = time.time()

notify("MiMi Assistant", "Camera is active — gesture control ready")
print("[MiMi] Camera ready.")

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

    any_mouse_mode = any(mouse_mode)

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
            gesture_score = 0.0
            if recognition_result.gestures and idx < len(recognition_result.gestures):
                gesture_score = recognition_result.gestures[idx][0].score

            color = GESTURE_COLORS.get(gesture_name, (0, 255, 0))
            skel_color = (0, 200, 255) if mouse_mode[idx] else color
            draw_hand_skeleton(frame, hand_landmarks, skel_color)

            toggled, toggle_progress = detect_mouse_toggle(gesture_name, idx, now_s)
            if toggled:
                mouse_mode[idx] = not mouse_mode[idx]
                if mouse_mode[idx]:
                    print(f"[MiMi] Hand {idx + 1}: Mouse mode ON")
                    notify("MiMi Assistant", "Mouse Mode ON")
                    messages.append(("Mouse mode ON", now_s + 2.0, (0, 200, 255)))
                else:
                    print(f"[MiMi] Hand {idx + 1}: Mouse mode OFF")
                    mouse_ctrl[idx].reset()
                    notify("MiMi Assistant", "Mouse Mode OFF")
                    messages.append(("Mouse mode OFF", now_s + 2.0, (160, 160, 160)))

            y = 38 + idx * 95

            if mouse_mode[idx]:
                drag_trigger = any(
                    all_gesture_names[i] == "Pointing_Up"
                    for i in range(len(all_gesture_names))
                    if i != idx
                )
                mouse_result = mouse_ctrl[idx].process(hand_landmarks, gesture_name, drag_trigger)
                draw_mouse_hud(frame, hand_landmarks, mouse_result)

                action_label = ""
                if mouse_result["double_click"]:
                    action_label = "Double Click"
                    notify("MiMi Assistant", "Double Click")
                elif mouse_result["dragging"] and not _was_dragging[idx]:
                    action_label = "Dragging"
                    notify("MiMi Assistant", "Dragging")
                elif mouse_result["left_click"]:
                    action_label = "Left Click"
                    notify("MiMi Assistant", "Left Click")
                elif mouse_result["right_click"]:
                    action_label = "Right Click"
                    notify("MiMi Assistant", "Right Click")
                elif mouse_result["scrolling"]:
                    action_label = "Scroll"
                _was_dragging[idx] = mouse_result["dragging"]

                cv2.putText(frame, f"Hand {idx + 1}: MOUSE {action_label}",
                            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 200, 255), 2, cv2.LINE_AA)
                cv2.putText(frame, "ILoveYou to exit mouse mode",
                            (10, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

                if toggle_progress > 0.04:
                    draw_hold_arc(frame, hand_landmarks, toggle_progress, (0, 200, 255))

            else:
                if toggle_progress > 0.04:
                    draw_hold_arc(frame, hand_landmarks, toggle_progress, GESTURE_COLORS["ILoveYou"])
                    cv2.putText(frame, f"Mouse mode {int(toggle_progress * 100)}%",
                                (10, y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                                GESTURE_COLORS["ILoveYou"], 1, cv2.LINE_AA)

                hold_triggered, hold_progress = detect_static_gesture(gesture_name, idx, now_s)

                if hold_triggered:
                    action = GESTURE_ACTIONS[gesture_name]["action"]
                    label = GESTURE_ACTIONS[gesture_name]["label"]
                    dispatch_action(action, idx)
                    notify("MiMi Assistant", label)
                    messages.append((f"{label}!", now_s + 2.5, color))

                if hold_progress > 0.04 and gesture_name in GESTURE_ACTIONS:
                    draw_hold_arc(frame, hand_landmarks, hold_progress, color)

                cv2.putText(frame, f"Hand {idx + 1}: {gesture_name} ({gesture_score:.2f})",
                            (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)

                if gesture_name in GESTURE_ACTIONS and hold_progress > 0.04:
                    pct = int(hold_progress * 100)
                    lbl = GESTURE_ACTIONS[gesture_name]["label"]
                    cv2.putText(frame, f"Hold: {lbl} {pct}%",
                                (10, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)

    if any_mouse_mode:
        draw_mouse_mode_border(frame)

    draw_legend(frame, any_mouse_mode)

    idle_s = now_s - last_hand_seen_t
    if idle_s >= INACTIVITY_TIMEOUT_S:
        print("[MiMi] No hand detected — closing camera.")
        break
    elif idle_s >= INACTIVITY_TIMEOUT_S - 3:
        remaining = int(INACTIVITY_TIMEOUT_S - idle_s) + 1
        cv2.putText(frame, f"No hand — closing in {remaining}s",
                    (10, frame.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 100, 255), 2, cv2.LINE_AA)

    messages = [(t, u, c) for t, u, c in messages if now_s < u]
    for i, (txt, _, col) in enumerate(messages[-3:]):
        cv2.putText(frame, txt, (30, frame.shape[0] - 40 - i * 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 2, cv2.LINE_AA)

    cv2.imshow("MiMi Assistant - Gesture Control", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
recognizer.close()
