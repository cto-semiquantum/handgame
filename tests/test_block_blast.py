"""
test_block_blast.py - Unit tests for Block Blast board mechanics, placement,
line-clear logic, combo multipliers, and game-over detection.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config
from block_piece import BlockPiece, TrayManager
from block_board import BlockBoard


class TestBlockBlast(unittest.TestCase):
    def setUp(self):
        self.board = BlockBoard()

    def test_piece_instantiation(self):
        piece = BlockPiece('dot', ((1,),), (255, 0, 0))
        self.assertEqual(piece.rows, 1)
        self.assertEqual(piece.cols, 1)
        self.assertEqual(piece.cell_count, 1)

        square = BlockPiece('square_2x2', ((1, 1), (1, 1)), (0, 255, 0))
        self.assertEqual(square.rows, 2)
        self.assertEqual(square.cols, 2)
        self.assertEqual(square.cell_count, 4)

    def test_placement_validity(self):
        piece = BlockPiece('bar_3_h', ((1, 1, 1),), (255, 100, 0))

        # Valid placement at (0, 0)
        self.assertTrue(self.board.can_place(piece, 0, 0))
        placed_count = self.board.place(piece, 0, 0)
        self.assertEqual(placed_count, 3)

        # Overlapping placement should fail
        self.assertFalse(self.board.can_place(piece, 0, 1))

        # Out-of-bounds placements should fail
        self.assertFalse(self.board.can_place(piece, -1, 0))
        self.assertFalse(self.board.can_place(piece, 0, config.BLOCK_GRID_SIZE - 2))  # needs 3 cols, only 2 left

    def test_single_row_clear(self):
        # Fill row 0 completely with 1x1 dots
        dot = BlockPiece('dot', ((1,),), (100, 100, 255))
        for col in range(config.BLOCK_GRID_SIZE):
            self.board.place(dot, 0, col)

        lines, points = self.board.check_and_clear_lines()
        self.assertEqual(lines, 1)
        self.assertEqual(points, config.SCORE_PER_LINE)

        # Verify row 0 is cleared
        for col in range(config.BLOCK_GRID_SIZE):
            self.assertIsNone(self.board.grid[0][col])

    def test_simultaneous_cross_clear_combo(self):
        # Fill row 2 and col 3 completely
        dot = BlockPiece('dot', ((1,),), (255, 200, 50))
        for i in range(config.BLOCK_GRID_SIZE):
            self.board.place(dot, 2, i)
            self.board.place(dot, i, 3)

        lines, points = self.board.check_and_clear_lines()
        self.assertEqual(lines, 2)  # 1 row + 1 col
        # Expected points: 2 * 10 + 1 * 15 = 35
        expected_points = 2 * config.SCORE_PER_LINE + config.SCORE_COMBO_BONUS
        self.assertEqual(points, expected_points)

        # Verify intersection and line cells are cleared
        self.assertIsNone(self.board.grid[2][3])
        self.assertIsNone(self.board.grid[2][0])
        self.assertIsNone(self.board.grid[0][3])

    def test_game_over_detection(self):
        # Fill the entire board except 1 cell at (0, 0)
        dot = BlockPiece('dot', ((1,),), (50, 50, 50))
        for r in range(config.BLOCK_GRID_SIZE):
            for c in range(config.BLOCK_GRID_SIZE):
                if not (r == 0 and c == 0):
                    self.board.grid[r][c] = dot.color

        square = BlockPiece('square_2x2', ((1, 1), (1, 1)), (255, 0, 0))
        # 2x2 cannot fit on a 1-cell empty space
        self.assertFalse(self.board.can_piece_fit_anywhere(square))

        # 1x1 dot CAN fit
        self.assertTrue(self.board.can_piece_fit_anywhere(dot))


if __name__ == '__main__':
    unittest.main()
