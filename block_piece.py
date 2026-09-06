"""
block_piece.py - Block Blast Polyomino Piece Library and Tray Manager
Implements piece shapes, candy-style rendering, tray slot management,
and difficulty-weighted random generation.
"""

import random
import pygame
import config

# Piece Shape Library defined as binary matrices (rows x cols)
SHAPE_LIBRARY = {
    # 1-cell
    'dot': (
        (1,),
    ),
    # 2-cells
    'bar_2_h': (
        (1, 1),
    ),
    'bar_2_v': (
        (1,),
        (1,),
    ),
    # 3-cells
    'bar_3_h': (
        (1, 1, 1),
    ),
    'bar_3_v': (
        (1,),
        (1,),
        (1,),
    ),
    'corner_3_tl': (
        (1, 1),
        (1, 0),
    ),
    'corner_3_tr': (
        (1, 1),
        (0, 1),
    ),
    'corner_3_bl': (
        (1, 0),
        (1, 1),
    ),
    'corner_3_br': (
        (0, 1),
        (1, 1),
    ),
    # 4-cells
    'square_2x2': (
        (1, 1),
        (1, 1),
    ),
    'bar_4_h': (
        (1, 1, 1, 1),
    ),
    'bar_4_v': (
        (1,),
        (1,),
        (1,),
        (1,),
    ),
    'l_4_1': (
        (1, 0),
        (1, 0),
        (1, 1),
    ),
    'l_4_2': (
        (0, 1),
        (0, 1),
        (1, 1),
    ),
    'l_4_3': (
        (1, 1, 1),
        (1, 0, 0),
    ),
    'l_4_4': (
        (1, 1, 1),
        (0, 0, 1),
    ),
    't_4_up': (
        (0, 1, 0),
        (1, 1, 1),
    ),
    't_4_down': (
        (1, 1, 1),
        (0, 1, 0),
    ),
    'z_4': (
        (1, 1, 0),
        (0, 1, 1),
    ),
    's_4': (
        (0, 1, 1),
        (1, 1, 0),
    ),
    # 5-cells
    'bar_5_h': (
        (1, 1, 1, 1, 1),
    ),
    'bar_5_v': (
        (1,),
        (1,),
        (1,),
        (1,),
        (1,),
    ),
    'big_l_5_1': (
        (1, 0, 0),
        (1, 0, 0),
        (1, 1, 1),
    ),
    'big_l_5_2': (
        (0, 0, 1),
        (0, 0, 1),
        (1, 1, 1),
    ),
    'square_3x3': (
        (1, 1, 1),
        (1, 1, 1),
        (1, 1, 1),
    ),
}

# Tiered shape categories for progressive difficulty
TIER_EASY = ['dot', 'bar_2_h', 'bar_2_v', 'bar_3_h', 'bar_3_v', 'square_2x2', 'corner_3_tl', 'corner_3_br']
TIER_MEDIUM = TIER_EASY + ['bar_4_h', 'bar_4_v', 'l_4_1', 'l_4_2', 'l_4_3', 'l_4_4', 't_4_up', 't_4_down']
TIER_HARD = list(SHAPE_LIBRARY.keys())


class BlockPiece:
    def __init__(self, name, shape, color):
        self.name = name
        self.shape = shape
        self.color = color
        self.rows = len(shape)
        self.cols = len(shape[0])
        self.cell_count = sum(row.count(1) for row in shape)

    @classmethod
    def random_piece(cls, score=0):
        """Generates a piece weighted by player score."""
        if score < 120:
            pool = TIER_EASY
        elif score < 350:
            pool = TIER_MEDIUM
        else:
            pool = TIER_HARD

        name = random.choice(pool)
        shape = SHAPE_LIBRARY[name]
        color = random.choice(config.BLOCK_COLORS)
        return cls(name, shape, color)

    def render(self, surface, top_left_x, top_left_y, cell_size, alpha=255, preview=False):
        """
        Renders the polyomino piece with rounded glossy block styling.
        If alpha < 255, renders onto a transparent surface for ghost preview.
        """
        w = self.cols * cell_size
        h = self.rows * cell_size

        target_surface = surface
        offset_x = top_left_x
        offset_y = top_left_y

        if alpha < 255:
            temp_surface = pygame.Surface((w, h), pygame.SRCALPHA)
            target_surface = temp_surface
            offset_x = 0
            offset_y = 0

        r, g, b = self.color
        base_color = (r, g, b, alpha) if alpha < 255 else (r, g, b)
        highlight_color = (
            min(255, r + 45),
            min(255, g + 45),
            min(255, b + 45),
            alpha if alpha < 255 else 255,
        )
        shadow_color = (
            max(0, r - 45),
            max(0, g - 45),
            max(0, b - 45),
            alpha if alpha < 255 else 255,
        )

        for row_idx, row in enumerate(self.shape):
            for col_idx, val in enumerate(row):
                if not val:
                    continue

                cell_x = offset_x + col_idx * cell_size
                cell_y = offset_y + row_idx * cell_size
                cell_rect = pygame.Rect(cell_x + 2, cell_y + 2, cell_size - 4, cell_size - 4)

                # Draw main rounded block
                pygame.draw.rect(target_surface, base_color, cell_rect, border_radius=6)

                # Top-left glossy highlight
                inner_rect = pygame.Rect(cell_x + 4, cell_y + 4, cell_size - 8, (cell_size - 8) // 2)
                pygame.draw.rect(target_surface, highlight_color, inner_rect, border_radius=4)

                # Border stroke
                if not preview:
                    pygame.draw.rect(target_surface, shadow_color, cell_rect, width=1, border_radius=6)

        if alpha < 255:
            surface.blit(temp_surface, (top_left_x, top_left_y))


class TrayManager:
    """Manages the 3 piece slots beneath the board."""
    def __init__(self):
        self.slots = [None, None, None]
        self.refill(score=0)

    def refill(self, score=0):
        """Generates 3 new pieces for all slots."""
        for i in range(config.TRAY_SLOT_COUNT):
            self.slots[i] = BlockPiece.random_piece(score)

    def refill_if_empty(self, score=0):
        """If all 3 slots have been placed, refills the tray."""
        if all(slot is None for slot in self.slots):
            self.refill(score)
            return True
        return False

    def get_slot_rect(self, slot_index):
        """Calculates pixel bounding rectangle for a tray slot."""
        spacing = (config.CANVAS_WIDTH - config.TRAY_SLOT_COUNT * config.TRAY_SLOT_WIDTH) // (config.TRAY_SLOT_COUNT + 1)
        x = spacing + slot_index * (config.TRAY_SLOT_WIDTH + spacing)
        y = config.TRAY_OFFSET_Y
        return pygame.Rect(x, y, config.TRAY_SLOT_WIDTH, config.TRAY_SLOT_HEIGHT)

    def get_slot_at_pos(self, px, py):
        """Returns slot index (0, 1, 2) if (px, py) is inside a populated slot, else None."""
        for i in range(config.TRAY_SLOT_COUNT):
            if self.slots[i] is not None:
                rect = self.get_slot_rect(i)
                if rect.collidepoint(px, py):
                    return i
        return None

    def take_piece(self, slot_index):
        """Removes and returns piece from slot."""
        if 0 <= slot_index < config.TRAY_SLOT_COUNT:
            piece = self.slots[slot_index]
            self.slots[slot_index] = None
            return piece
        return None

    def return_piece(self, slot_index, piece):
        """Puts piece back into its tray slot if dropped illegally."""
        if 0 <= slot_index < config.TRAY_SLOT_COUNT:
            self.slots[slot_index] = piece

    def has_valid_move(self, board):
        """Checks if at least one remaining piece in tray can fit on the board."""
        for piece in self.slots:
            if piece is not None and board.can_piece_fit_anywhere(piece):
                return True
        return False

    def render(self, surface, hovered_slot=None):
        """Renders the tray background plates and current piece contents."""
        for i in range(config.TRAY_SLOT_COUNT):
            rect = self.get_slot_rect(i)

            # Slot background dish
            is_hovered = (i == hovered_slot)
            bg_color = (48, 52, 78) if is_hovered else (32, 35, 54)
            border_color = config.COLOR_ACCENT if is_hovered else (50, 56, 84)

            pygame.draw.rect(surface, bg_color, rect, border_radius=10)
            pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)

            piece = self.slots[i]
            if piece is not None:
                # Scale piece down if larger than 3x3 to comfortably fit inside slot
                max_dim = max(piece.rows, piece.cols)
                slot_cell_size = min(26, (rect.width - 24) // max_dim)

                piece_pixel_w = piece.cols * slot_cell_size
                piece_pixel_h = piece.rows * slot_cell_size

                px = rect.x + (rect.width - piece_pixel_w) // 2
                py = rect.y + (rect.height - piece_pixel_h) // 2

                piece.render(surface, px, py, slot_cell_size)
