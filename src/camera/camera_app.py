import cv2
import mediapipe as mp
import numpy as np
import time
import sys
import os

# Add src directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from actions.system_operations import SystemOperations

# ─── MediaPipe Setup ───────────────────────────────────────────────────────
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'models', 'gesture_recognizer.task'
)

options = GestureRecognizerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=VisionRunningMode.VIDEO,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
recognizer = GestureRecognizer.create_from_options(options)

# ─── Hand Skeleton Drawing ─────────────────────────────────────────────────
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]

PALM_LANDMARKS = [0, 5, 9, 13, 17]

# ─── Static Gesture Hold Configuration ────────────────────────────────────
GESTURE_ACTIONS = {
    "Thumb_Up":    {"action": "volume_up",   "hold": 1.2, "cooldown": 2.0, "label": "Volume Up"},
    "Thumb_Down":  {"action": "volume_down", "hold": 1.2, "cooldown": 2.0, "label": "Volume Down"},
    "Open_Palm":   {"action": "screenshot",  "hold": 1.5, "cooldown": 3.0, "label": "Screenshot"},
    "Victory":     {"action": "mute_toggle", "hold": 1.2, "cooldown": 2.0, "label": "Mute Toggle"},
    "Closed_Fist": {"action": "lock_screen", "hold": 2.0, "cooldown": 5.0, "label": "Lock Screen"},
}

last_action_time   = {k: 0.0 for k in GESTURE_ACTIONS}
gesture_hold_start = [None] * 2
gesture_hold_name  = [None] * 2

GESTURE_COLORS = {
    "Thumb_Up":    (100, 255, 100),
    "Thumb_Down":  (100, 100, 255),
    "Open_Palm":   (0,   200, 255),
    "Victory":     (255,  50, 200),
    "Closed_Fist": (0,    0,  255),
    "None":        (160, 160, 160),
}

# ─── Static Gesture Hold Detection ────────────────────────────────────────
def detect_static_gesture(gesture_name, hand_idx, now_s):
    """
    Track how long a static gesture has been held.
    Returns (triggered: bool, hold_progress: float 0-1).
    """
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


# ─── Action Dispatch ───────────────────────────────────────────────────────
def dispatch_action(action_name, hand_idx):
    print(f"[MiMi] Action '{action_name}' triggered by hand {hand_idx + 1}")
    actions = {
        "lock_screen": SystemOperations.lock_screen,
        "volume_up":   SystemOperations.volume_up,
        "volume_down": SystemOperations.volume_down,
        "mute_toggle": SystemOperations.mute_toggle,
        "screenshot":  SystemOperations.take_screenshot,
    }
    fn = actions.get(action_name)
    if fn:
        fn()
    else:
        print(f"[MiMi] Unknown action: {action_name}")


# ─── Drawing Helpers ───────────────────────────────────────────────────────
def draw_hand_skeleton(frame, hand_landmarks, color=(0, 255, 0)):
    h, w = frame.shape[:2]
    pts = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks]

    for (a, b) in HAND_CONNECTIONS:
        cv2.line(frame, pts[a], pts[b], color, 2, cv2.LINE_AA)

    for i, (x, y) in enumerate(pts):
        radius = 7 if i == 0 else 4
        cv2.circle(frame, (x, y), radius, color, -1)
        cv2.circle(frame, (x, y), radius, (255, 255, 255), 1)


def draw_hold_arc(frame, hand_landmarks, progress, color):
    h, w = frame.shape[:2]
    cx = int(np.mean([hand_landmarks[i].x for i in PALM_LANDMARKS]) * w)
    cy = int(np.mean([hand_landmarks[i].y for i in PALM_LANDMARKS]) * h)
    angle = int(360 * progress)
    cv2.ellipse(frame, (cx, cy), (32, 32), -90, 0, angle, color, 4, cv2.LINE_AA)
    cv2.ellipse(frame, (cx, cy), (32, 32), -90, angle, 360, (80, 80, 80), 2, cv2.LINE_AA)


def draw_legend(frame):
    h, w = frame.shape[:2]
    panel_w, line_h = 290, 22
    start_y = h - len(GESTURE_ACTIONS) * line_h - 20

    overlay = frame.copy()
    cv2.rectangle(overlay, (w - panel_w - 10, start_y - 10),
                  (w - 5, h - 10), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    for i, (gname, cfg) in enumerate(GESTURE_ACTIONS.items()):
        col = GESTURE_COLORS.get(gname, (200, 200, 200))
        text = f"{gname}: {cfg['label']} ({cfg['hold']}s)"
        cv2.putText(frame, text,
                    (w - panel_w - 5, start_y + i * line_h),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, col, 1, cv2.LINE_AA)


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

# ─── Inactivity Timeout ────────────────────────────────────────────────────
INACTIVITY_TIMEOUT_S = 5.0     # seconds without any hand visible before auto-close
last_hand_seen_t = time.time()

print("[MiMi] Camera ready. Gesture guide:")
for gname, cfg in GESTURE_ACTIONS.items():
    print(f"  {gname:<14} -> {cfg['label']:<14} (hold {cfg['hold']}s)")
print(f"  Camera auto-closes after {int(INACTIVITY_TIMEOUT_S)}s of no hand detected.")

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
        last_hand_seen_t = now_s   # reset inactivity timer whenever a hand is visible

        for idx, hand_landmarks in enumerate(recognition_result.hand_landmarks):
            gesture_name = "None"
            gesture_score = 0.0
            if recognition_result.gestures and idx < len(recognition_result.gestures):
                g = recognition_result.gestures[idx][0]
                gesture_name = g.category_name
                gesture_score = g.score

            color = GESTURE_COLORS.get(gesture_name, (0, 255, 0))
            draw_hand_skeleton(frame, hand_landmarks, color)

            hold_triggered, hold_progress = detect_static_gesture(gesture_name, idx, now_s)

            if hold_triggered:
                action = GESTURE_ACTIONS[gesture_name]["action"]
                label  = GESTURE_ACTIONS[gesture_name]["label"]
                dispatch_action(action, idx)
                messages.append((f"{label}!", now_s + 2.5, color))

            if hold_progress > 0.04 and gesture_name in GESTURE_ACTIONS:
                draw_hold_arc(frame, hand_landmarks, hold_progress, color)

            y = 38 + idx * 85
            cv2.putText(frame, f"Hand {idx+1}: {gesture_name} ({gesture_score:.2f})",
                        (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2, cv2.LINE_AA)

            if gesture_name in GESTURE_ACTIONS and hold_progress > 0.04:
                pct = int(hold_progress * 100)
                lbl = GESTURE_ACTIONS[gesture_name]["label"]
                cv2.putText(frame, f"Hold: {lbl} {pct}%",
                            (10, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)

    draw_legend(frame)

    # ── Inactivity countdown ────────────────────────────────────────────
    idle_s = now_s - last_hand_seen_t
    if idle_s >= INACTIVITY_TIMEOUT_S:
        print("[MiMi] No hand detected — closing camera. Say 'Hey Mycroft' to reactivate.")
        break
    elif idle_s >= INACTIVITY_TIMEOUT_S - 3:
        remaining = int(INACTIVITY_TIMEOUT_S - idle_s) + 1
        cv2.putText(frame, f"No hand detected — closing in {remaining}s",
                    (10, frame.shape[0] - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 100, 255), 2, cv2.LINE_AA)

    messages = [(t, u, c) for t, u, c in messages if now_s < u]
    for i, (txt, _, col) in enumerate(messages[-3:]):
        cv2.putText(frame, txt,
                    (30, frame.shape[0] - 40 - i * 42),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, col, 2, cv2.LINE_AA)

    cv2.imshow("MiMi Assistant - Gesture Control", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
recognizer.close()
