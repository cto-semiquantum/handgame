"""
test_runner.py - Unit tests for Endless Runner physics, lane shifting, and collision boxes.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from player import Player
from obstacles import ObstacleManager
from collectibles import CollectibleManager


class TestRunner(unittest.TestCase):
    def test_player_lanes(self):
        p = Player()
        self.assertEqual(p.lane, 1)

        p.move_left()
        self.assertEqual(p.lane, 0)
        p.move_left()  # Clamped
        self.assertEqual(p.lane, 0)

        p.move_right()
        self.assertEqual(p.lane, 1)
        p.move_right()
        self.assertEqual(p.lane, 2)
        p.move_right()  # Clamped
        self.assertEqual(p.lane, 2)

    def test_player_jump_and_slide(self):
        p = Player()
        self.assertEqual(p.state, 'running')

        p.jump()
        self.assertEqual(p.state, 'jumping')
        rect_jump = p.get_rect(config.CANVAS_WIDTH, config.CANVAS_HEIGHT)

        p.reset()
        p.slide()
        self.assertEqual(p.state, 'sliding')
        rect_slide = p.get_rect(config.CANVAS_WIDTH, config.CANVAS_HEIGHT)

        # Slide height should be half of normal
        self.assertEqual(rect_slide[3], config.PLAYER_H // 2)

    def test_skateboard_invincibility(self):
        p = Player()
        self.assertFalse(p.skateboard)
        p.activate_skateboard()
        self.assertTrue(p.skateboard)


if __name__ == '__main__':
    unittest.main()
