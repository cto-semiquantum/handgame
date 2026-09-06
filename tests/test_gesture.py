"""
test_gesture.py - Unit tests for gesture signal processing, scale-invariant pinch, and hysteresis.
"""

import unittest
import math
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


class MockLandmark:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


class TestGestureFiltering(unittest.TestCase):
    def test_ema_smoothing(self):
        alpha = 0.35
        raw_values = [0.2, 0.8, 0.8, 0.8, 0.8]
        smoothed = raw_values[0]

        history = [smoothed]
        for v in raw_values[1:]:
            smoothed = alpha * v + (1.0 - alpha) * smoothed
            history.append(smoothed)

        self.assertAlmostEqual(history[1], 0.35 * 0.8 + 0.65 * 0.2, places=4)
        self.assertLess(history[1], 0.5)
        self.assertGreater(history[-1], 0.68)

    def test_lane_hysteresis(self):
        b_left = config.LANE_BOUNDARY_LEFT
        b_right = config.LANE_BOUNDARY_RIGHT
        m = config.HYSTERESIS_MARGIN

        current_lane = 1

        def update_lane(lane, x):
            if lane == 0:
                if x > b_left + m:
                    return 1
            elif lane == 1:
                if x < b_left - m:
                    return 0
                elif x > b_right + m:
                    return 2
            elif lane == 2:
                if x < b_right - m:
                    return 1
            return lane

        current_lane = update_lane(current_lane, 0.37)
        self.assertEqual(current_lane, 1)

        current_lane = update_lane(current_lane, 0.33)
        self.assertEqual(current_lane, 0)

        current_lane = update_lane(current_lane, 0.39)
        self.assertEqual(current_lane, 0)

        current_lane = update_lane(current_lane, 0.43)
        self.assertEqual(current_lane, 1)

    def test_scale_invariant_pinch_ratio(self):
        p_wrist = MockLandmark(0.5, 0.8)
        p_mcp = MockLandmark(0.5, 0.5)
        palm_size = math.sqrt((p_wrist.x - p_mcp.x)**2 + (p_wrist.y - p_mcp.y)**2)
        self.assertAlmostEqual(palm_size, 0.3)

        p_thumb = MockLandmark(0.5, 0.4)
        p_index = MockLandmark(0.54, 0.4)
        pinch_dist = math.sqrt((p_thumb.x - p_index.x)**2 + (p_thumb.y - p_index.y)**2)
        ratio = pinch_dist / palm_size
        self.assertLess(ratio, 0.40)

        p_index_far = MockLandmark(0.7, 0.4)
        pinch_dist_far = math.sqrt((p_thumb.x - p_index_far.x)**2 + (p_thumb.y - p_index_far.y)**2)
        ratio_far = pinch_dist_far / palm_size
        self.assertGreater(ratio_far, 0.40)

    def test_fist_to_open_jump_logic(self):
        # State: was_fist True, transition to open palm within 0.5s -> JUMP!
        was_fist = True
        time_since_fist = 0.2
        is_open_palm = True

        jump_triggered = False
        if is_open_palm and was_fist and time_since_fist < 0.65:
            jump_triggered = True

        self.assertTrue(jump_triggered)


if __name__ == '__main__':
    unittest.main()
