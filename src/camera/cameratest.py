import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time

# Initialize MediaPipe Gesture Recognizer
BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

# Create a gesture recognizer instance with the custom model
base_options = BaseOptions(model_asset_path='/Users/youssif/Documents/Projects/MiMi_Assistant/models/gesture_recognizer.task')

options = GestureRecognizerOptions(
    base_options=base_options,
    running_mode=VisionRunningMode.IMAGE,
    num_hands=2,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)

recognizer = GestureRecognizer.create_from_options(options)

# Initialize waving detection variables
hand_positions = [deque(maxlen=20) for _ in range(2)]  # Track positions for 2 hands as (t, x)
last_wave_time = [0.0 for _ in range(2)]
wave_cooldown_s = 1.0

wave_window_s = 0.9
min_wave_amplitude = 0.12  # peak-to-peak normalized wrist-x movement required
hysteresis_band = 0.06  # baseline +/- band to decide left/right (bigger = less false positives)
min_crossings = 2  # number of center crossings in window
min_speed = 0.45  # normalized x per second

hand_last_side = [0, 0]
hand_last_x = [None, None]
hand_last_t = [None, None]
hand_crossing_times = [deque(maxlen=10) for _ in range(2)]

def detect_waving(hand_landmarks, hand_idx, now_s):
    """Detect waving based on repeated centerline crossings with sufficient amplitude and speed."""
    if not hand_landmarks:
        return False, 0.0, 0, 0.0, 0.5, 0

    if now_s - last_wave_time[hand_idx] < wave_cooldown_s:
        return False, 0.0, 0, 0.0, 0.5, 0

    # Use wrist landmark (landmark 0) for tracking
    wrist = hand_landmarks[0]
    current_x = float(wrist.x)
    hand_positions[hand_idx].append((now_s, current_x))

    # Compute amplitude over recent window
    recent = [(t, x) for (t, x) in hand_positions[hand_idx] if now_s - t <= wave_window_s]
    if len(recent) < 6:
        return False, 0.0, len(hand_crossing_times[hand_idx]), 0.0, 0.5, 0

    xs = np.array([x for (_, x) in recent], dtype=np.float32)
    amplitude = float(np.max(xs) - np.min(xs))

    # Instantaneous speed estimate
    speed = 0.0
    if hand_last_x[hand_idx] is not None and hand_last_t[hand_idx] is not None:
        dt = now_s - hand_last_t[hand_idx]
        if dt > 1e-3:
            speed = abs(current_x - hand_last_x[hand_idx]) / dt
    hand_last_x[hand_idx] = current_x
    hand_last_t[hand_idx] = now_s

    # Adaptive baseline (works anywhere on screen)
    baseline = float(np.median(xs))

    # Side of baseline with hysteresis
    if current_x > baseline + hysteresis_band:
        side = 1
    elif current_x < baseline - hysteresis_band:
        side = -1
    else:
        side = 0

    prev_side = hand_last_side[hand_idx]

    # Initialize side as soon as we get a confident (non-zero) side
    if prev_side == 0 and side != 0:
        hand_last_side[hand_idx] = side
    elif side != 0 and prev_side != 0 and side != prev_side:
        # Count crossing on any left<->right change; speed will be used only for final wave decision.
        hand_crossing_times[hand_idx].append(now_s)
        hand_last_side[hand_idx] = side

    # prune old crossings
    while hand_crossing_times[hand_idx] and now_s - hand_crossing_times[hand_idx][0] > wave_window_s:
        hand_crossing_times[hand_idx].popleft()

    crossings = len(hand_crossing_times[hand_idx])
    is_waving = amplitude >= min_wave_amplitude and crossings >= min_crossings and speed >= min_speed
    if is_waving:
        last_wave_time[hand_idx] = now_s
        hand_crossing_times[hand_idx].clear()
        return True, amplitude, crossings, speed, baseline, side

    return False, amplitude, crossings, speed, baseline, side

def trigger_waving_action(hand_idx):
    """Execute action when waving is detected"""
    print(f"Waving detected from hand {hand_idx + 1}! 👋")

cap = cv2.VideoCapture(0)

message_until_s = 0.0

while True:
    ret, frame = cap.read()
    if not ret:
        print("camera failed")
        break

    # Flip the frame horizontally for selfie-view display
    frame = cv2.flip(frame, 1)
    
    # Convert frame to RGB for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Convert frame to MediaPipe image format
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    
    # Process the frame for gesture recognition
    recognition_result = recognizer.recognize(mp_image)
    now_s = time.time()
    
    # Draw hand landmarks and display gestures
    if recognition_result.hand_landmarks:
        for idx, hand_landmarks in enumerate(recognition_result.hand_landmarks):
            # Draw circles at landmark positions
            for landmark in hand_landmarks:
                x = int(landmark.x * frame.shape[1])
                y = int(landmark.y * frame.shape[0])
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
            
            # Check for waving
            is_waving, wave_amp, wave_cross, wave_speed, wave_base, wave_side = detect_waving(hand_landmarks, idx, now_s)
            
            # Trigger action if waving detected
            if is_waving:
                trigger_waving_action(idx)
                message_until_s = max(message_until_s, now_s + 1.0)
            
            # Display results
            y_offset = 30 + idx * 80
            
            if is_waving:
                cv2.putText(frame, f"Hand {idx+1}: WAVING! 👋", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 255, 255), 2, cv2.LINE_AA)
            elif recognition_result.gestures and idx < len(recognition_result.gestures):
                gesture = recognition_result.gestures[idx][0]
                cv2.putText(frame, f"Hand {idx+1}: {gesture.category_name} ({gesture.score:.2f})", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 255, 0), 2, cv2.LINE_AA)
            else:
                cv2.putText(frame, f"Hand {idx+1}: No gesture detected", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (128, 128, 128), 2, cv2.LINE_AA)

            cv2.putText(frame, f"amp={wave_amp:.2f} cross={wave_cross} spd={wave_speed:.2f} base={wave_base:.2f} side={wave_side}",
                        (10, y_offset + 35), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (255, 255, 255), 2, cv2.LINE_AA)

    if now_s < message_until_s:
        cv2.putText(frame, "Hello! Wave detected!", 
                   (30, frame.shape[0] - 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 0), 3, cv2.LINE_AA)

    cv2.imshow("Hand Gesture Detection", frame)

    if cv2.waitKey(1) == 27:
        break

# Release the capture and destroy all windows
cap.release()
cv2.destroyAllWindows()
recognizer.close()