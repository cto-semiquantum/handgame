"""
gesture.py - Hand Tracker with Fist-to-Open Jump, Left/Right Steering, and Stop Controls (v2.2)
Features:
- "First close fist, then just open -> boy jumps": Detects fist-to-open explosion gesture for jump
- Held closed fist (>0.6s) -> Stop / Pause the game
- Natural Left / Right steering with hysteresis
- Scale-invariant pinch metric for Block Blast
- CLAHE lighting normalization & downscaled inference for high FPS
"""

import collections
import math
import time
import cv2
import mediapipe as mp
import config

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

_FINGER_TIPS = [8, 12, 16, 20]      # index, middle, ring, pinky
_FINGER_PIPS = [6, 10, 14, 18]
_THUMB_TIP = 4
_THUMB_IP = 3
_INDEX_TIP = 8
_WRIST = 0
_MIDDLE_MCP = 9


class GestureRecognizer:
    def __init__(self):
        try:
            self.hands = mp_hands.Hands(
                max_num_hands=1,
                min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
                model_complexity=0,
            )
        except TypeError:
            self.hands = mp_hands.Hands(
                max_num_hands=1,
                min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE,
            )

        self.smoothed_x = None
        self.smoothed_y = None
        self.current_lane = 1

        # Fist state tracking for "close fist then open -> jump"
        self.was_fist = False
        self.last_fist_time = 0.0
        self.fist_held_start = 0.0

        self.is_pinching = False
        self.pinch_release_counter = 0

        self.last_seen_time = 0.0
        self.has_active_tracking = False

        self.calibration_offset_x = 0.0
        self.is_calibrating = False
        self.calibration_samples = []
        self.calibration_end_time = 0.0

    def start_calibration(self, duration_s=1.5):
        self.is_calibrating = True
        self.calibration_samples = []
        self.calibration_end_time = time.time() + duration_s

    def _update_calibration(self, raw_wrist_x):
        if not self.is_calibrating:
            return
        self.calibration_samples.append(raw_wrist_x)
        if time.time() >= self.calibration_end_time:
            self.is_calibrating = False
            if self.calibration_samples:
                avg_neutral = sum(self.calibration_samples) / len(self.calibration_samples)
                self.calibration_offset_x = max(-0.15, min(0.15, avg_neutral - 0.50))
            self.calibration_samples.clear()

    def _normalize_lighting(self, frame_bgr):
        try:
            lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l_eq = clahe.apply(l_channel)
            lab_eq = cv2.merge((l_eq, a_channel, b_channel))
            return cv2.cvtColor(lab_eq, cv2.COLOR_LAB2BGR)
        except Exception:
            return frame_bgr

    def _count_fingers_up(self, landmarks, handedness_label):
        count = 0
        for tip, pip in zip(_FINGER_TIPS, _FINGER_PIPS):
            if landmarks[tip].y < landmarks[pip].y:
                count += 1

        if handedness_label == 'Right':
            if landmarks[_THUMB_TIP].x < landmarks[_THUMB_IP].x:
                count += 1
        else:
            if landmarks[_THUMB_TIP].x > landmarks[_THUMB_IP].x:
                count += 1
        return count

    def _calculate_scale_invariant_pinch(self, landmarks):
        p_thumb = landmarks[_THUMB_TIP]
        p_index = landmarks[_INDEX_TIP]
        p_wrist = landmarks[_WRIST]
        p_mid_mcp = landmarks[_MIDDLE_MCP]

        dx = p_thumb.x - p_index.x
        dy = p_thumb.y - p_index.y
        pinch_dist = math.sqrt(dx * dx + dy * dy)

        pdx = p_wrist.x - p_mid_mcp.x
        pdy = p_wrist.y - p_mid_mcp.y
        palm_size = math.sqrt(pdx * pdx + pdy * pdy)

        ratio = pinch_dist / max(0.02, palm_size)
        return ratio < 0.40, ratio

    def _update_lane_with_hysteresis(self, wrist_x):
        b_left = config.LANE_BOUNDARY_LEFT + self.calibration_offset_x
        b_right = config.LANE_BOUNDARY_RIGHT + self.calibration_offset_x
        m = config.HYSTERESIS_MARGIN

        lane = self.current_lane
        if lane == 0:
            if wrist_x > b_left + m:
                lane = 1
        elif lane == 1:
            if wrist_x < b_left - m:
                lane = 0
            elif wrist_x > b_right + m:
                lane = 2
        elif lane == 2:
            if wrist_x < b_right - m:
                lane = 1

        self.current_lane = lane
        return lane

    def process(self, frame_bgr):
        now = time.time()
        h, w = frame_bgr.shape[:2]

        norm_frame = self._normalize_lighting(frame_bgr)

        if (w, h) == (config.INFERENCE_WIDTH, config.INFERENCE_HEIGHT):
            # Client already captures at the inference resolution (see
            # templates/index.html) - skip the redundant resize/copy.
            small_frame = norm_frame
        else:
            small_frame = cv2.resize(
                norm_frame,
                (config.INFERENCE_WIDTH, config.INFERENCE_HEIGHT),
                interpolation=cv2.INTER_LINEAR,
            )
        small_rgb = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(small_rgb)

        landmarks_found = bool(results.multi_hand_landmarks)

        output = {
            'lane': self.current_lane if self.has_active_tracking else None,
            'gesture': 'run',
            'jump_triggered': False,
            'stop_triggered': False,
            'cursor_pos': (self.smoothed_x, self.smoothed_y) if (self.has_active_tracking and self.smoothed_x is not None) else None,
            'is_pinching': self.is_pinching if self.has_active_tracking else False,
            'is_fist': False,
            'is_open_palm': False,
            'hand_detected': False,
            'in_grace_period': False,
            'is_calibrating': self.is_calibrating,
            'pip_frame': None,
        }

        pip_src = frame_bgr.copy()

        if landmarks_found:
            self.last_seen_time = now
            self.has_active_tracking = True
            output['hand_detected'] = True

            hand_landmarks = results.multi_hand_landmarks[0]
            landmarks = hand_landmarks.landmark

            handedness_label = 'Right'
            if results.multi_handedness:
                handedness_label = results.multi_handedness[0].classification[0].label

            raw_wrist_x = 1.0 - landmarks[_WRIST].x
            raw_center_x = 1.0 - landmarks[_MIDDLE_MCP].x
            raw_center_y = landmarks[_MIDDLE_MCP].y

            if self.is_calibrating:
                self._update_calibration(raw_wrist_x)

            # Coordinate EMA smoothing
            alpha = config.EMA_ALPHA
            if self.smoothed_x is None:
                self.smoothed_x = raw_center_x
                self.smoothed_y = raw_center_y
            else:
                self.smoothed_x = alpha * raw_center_x + (1.0 - alpha) * self.smoothed_x
                self.smoothed_y = alpha * raw_center_y + (1.0 - alpha) * self.smoothed_y

            output['lane'] = self._update_lane_with_hysteresis(raw_wrist_x)

            # Finger counts
            fingers_up = self._count_fingers_up(landmarks, handedness_label)
            is_open_palm = (fingers_up >= 4)
            is_fist = (fingers_up == 0)

            output['is_fist'] = is_fist
            output['is_open_palm'] = is_open_palm

            # Track fist duration
            if is_fist:
                if not self.was_fist:
                    self.fist_held_start = now
                self.last_fist_time = now
                self.was_fist = True

                # Held closed fist > 0.6s triggers STOP / PAUSE
                if now - self.fist_held_start >= 0.6:
                    output['stop_triggered'] = True
                    output['gesture'] = 'stop'
                else:
                    output['gesture'] = 'fist'

            elif is_open_palm:
                # "First close fist, and just open then boy jump!"
                time_since_fist = now - self.last_fist_time
                if self.was_fist and time_since_fist < 0.65:
                    output['jump_triggered'] = True
                    output['gesture'] = 'jump'
                elif fingers_up == 5:
                    # Also allow direct open palm jump
                    output['jump_triggered'] = True
                    output['gesture'] = 'jump'
                else:
                    output['gesture'] = 'run'

                self.was_fist = False

            else:
                output['gesture'] = 'run'
                # Do not immediately clear was_fist to give user 0.3s transition time
                if now - self.last_fist_time > 0.45:
                    self.was_fist = False

            # Pinch detection
            raw_pinch, pinch_ratio = self._calculate_scale_invariant_pinch(landmarks)
            if raw_pinch:
                self.is_pinching = True
                self.pinch_release_counter = 0
            else:
                if self.is_pinching:
                    self.pinch_release_counter += 1
                    if self.pinch_release_counter >= 3:
                        self.is_pinching = False
                else:
                    self.is_pinching = False

            output['is_pinching'] = self.is_pinching

            cur_x = max(0.0, min(1.0, self.smoothed_x))
            cur_y = max(0.0, min(1.0, self.smoothed_y))
            output['cursor_pos'] = (cur_x, cur_y)

            if config.CAMERA_MIRROR:
                pip_src = cv2.flip(pip_src, 1)

            pip_border = (46, 213, 115)  # Green
            if output['jump_triggered']:
                pip_border = (255, 215, 0)  # Gold jump flash
            elif is_fist:
                pip_border = (239, 68, 68)  # Red stop/fist

            cv2.rectangle(pip_src, (0, 0), (w - 1, h - 1), pip_border, 6)

        else:
            elapsed_since_seen = now - self.last_seen_time
            if self.has_active_tracking and elapsed_since_seen < config.HAND_LOST_GRACE_PERIOD_S:
                output['hand_detected'] = True
                output['in_grace_period'] = True
                output['lane'] = self.current_lane
                output['gesture'] = 'run'
                if self.smoothed_x is not None:
                    output['cursor_pos'] = (self.smoothed_x, self.smoothed_y)
                output['is_pinching'] = self.is_pinching

                if config.CAMERA_MIRROR:
                    pip_src = cv2.flip(pip_src, 1)
                cv2.rectangle(pip_src, (0, 0), (w - 1, h - 1), (0, 165, 255), 6)
            else:
                self.has_active_tracking = False
                output['hand_detected'] = False
                output['lane'] = None
                output['gesture'] = 'none'
                output['cursor_pos'] = None
                output['is_pinching'] = False
                self.was_fist = False
                self.smoothed_x = None
                self.smoothed_y = None

                if config.CAMERA_MIRROR:
                    pip_src = cv2.flip(pip_src, 1)
                cv2.rectangle(pip_src, (0, 0), (w - 1, h - 1), (75, 75, 255), 6)

        output['pip_frame'] = cv2.resize(
            pip_src,
            (config.PIP_WIDTH, config.PIP_HEIGHT),
            interpolation=cv2.INTER_AREA,
        )

        return output

    def close(self):
        self.hands.close()
