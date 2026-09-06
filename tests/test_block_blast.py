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

    def test_tray_get_slot_at_pos_with_padding(self):
        tray = TrayManager()
        slot0_rect = tray.get_slot_rect(0)
        # Inside slot 0
        self.assertEqual(tray.get_slot_at_pos(slot0_rect.centerx, slot0_rect.centery), 0)
        # Slightly outside but within padding (10px to the left)
        self.assertEqual(tray.get_slot_at_pos(slot0_rect.left - 10, slot0_rect.centery), 0)
        # Far outside
        self.assertIsNone(tray.get_slot_at_pos(slot0_rect.left - 50, slot0_rect.centery))

    def test_block_blast_game_slot_pick_and_place(self):
        from block_game import BlockBlastGame
        game = BlockBlastGame()
        game.start()

        # Slot 0 pick via slot action
        game.apply_gesture({'slot': 0})
        self.assertIsNotNone(game.held_piece)
        self.assertEqual(game.held_from_slot, 0)
        self.assertIsNone(game.tray.slots[0])

        # Place held piece at (0, 0) on board
        piece_cells = game.held_piece.cell_count
        # Position cursor so ghost calculates row=0, col=0
        piece_w = game.held_piece.cols * config.BLOCK_CELL_PX
        piece_h = game.held_piece.rows * config.BLOCK_CELL_PX
        game.cursor_px = config.BOARD_OFFSET_X + piece_w // 2
        game.cursor_py = config.BOARD_OFFSET_Y + piece_h // 2 + 15

        # Release / drop
        game.apply_gesture({'is_open_palm': True, 'action': 'place'})
        self.assertIsNone(game.held_piece)
        self.assertEqual(game.score, piece_cells * config.SCORE_PER_PLACED_CELL)

    def test_block_blast_game_forgiving_invalid_drop_returns_to_tray(self):
        from block_game import BlockBlastGame
        game = BlockBlastGame()
        game.start()

        # Slot 1 pick
        game.apply_gesture({'slot': 1})
        original_piece = game.held_piece
        self.assertIsNotNone(original_piece)

        # Position cursor at an invalid off-board location (e.g. y = 40)
        game.cursor_px = 100
        game.cursor_py = 40

        # Drop on invalid position -> should safely return to tray slot 1!
        game.apply_gesture({'is_open_palm': True, 'action': 'place'})
        self.assertIsNone(game.held_piece)
        self.assertEqual(game.tray.slots[1], original_piece)
        self.assertIn("Returned to Tray", game.hint_message)

    def test_block_blast_game_move_cursor(self):
        from block_game import BlockBlastGame
        game = BlockBlastGame()
        game.start()

        initial_x = game.cursor_px
        initial_y = game.cursor_py
        game.apply_gesture({'move_cursor': [46, -46]})
        self.assertEqual(game.cursor_px, initial_x + 46)
        self.assertEqual(game.cursor_py, initial_y - 46)


if __name__ == '__main__':
    unittest.main()
