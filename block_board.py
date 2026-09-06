"""
block_board.py - 8x8 Grid Puzzle Board State and Mechanics
Handles placement validation, cell grid management, simultaneous multi-line
clearing (rows & columns), combo scoring, and game-over detection.
"""

import time
import pygame
import config


class BlockBoard:
    def __init__(self):
        self.size = config.BLOCK_GRID_SIZE
        self.grid = [[None for _ in range(self.size)] for _ in range(self.size)]
        # List of active flash animations: {'cells': [(r, c)...], 'start_time': t, 'duration': 0.35}
        self.clear_animations = []

    def reset(self):
        """Clears all grid cells and animation states."""
        self.grid = [[None for _ in range(self.size)] for _ in range(self.size)]
        self.clear_animations.clear()

    def can_place(self, piece, start_row, start_col):
        """Returns True if piece fits fully inside the board and overlaps zero occupied cells."""
        if start_row < 0 or start_row + piece.rows > self.size:
            return False
        if start_col < 0 or start_col + piece.cols > self.size:
            return False

        for r in range(piece.rows):
            for c in range(piece.cols):
                if piece.shape[r][c] == 1:
                    if self.grid[start_row + r][start_col + c] is not None:
                        return False
        return True

    def place(self, piece, start_row, start_col):
        """
        Commits piece onto the grid.
        Returns the number of cells placed.
        """
        if not self.can_place(piece, start_row, start_col):
            return 0

        for r in range(piece.rows):
            for c in range(piece.cols):
                if piece.shape[r][c] == 1:
                    self.grid[start_row + r][start_col + c] = piece.color

        return piece.cell_count

    def check_and_clear_lines(self):
        """
        Detects all simultaneously filled rows and columns.
        Clears them, triggers visual flash animation, and calculates combo points.
        Returns: (lines_cleared_count, bonus_points)
        """
        full_rows = [
            r for r in range(self.size)
            if all(self.grid[r][c] is not None for c in range(self.size))
        ]
        full_cols = [
            c for c in range(self.size)
            if all(self.grid[r][c] is not None for r in range(self.size))
        ]

        total_lines = len(full_rows) + len(full_cols)
        if total_lines == 0:
            return 0, 0

        cleared_cells = set()
        for r in full_rows:
            for c in range(self.size):
                cleared_cells.add((r, c))

        for c in full_cols:
            for r in range(self.size):
                cleared_cells.add((r, c))

        # Clear grid cells
        for r, c in cleared_cells:
            self.grid[r][c] = None

        # Add flash animation
        self.clear_animations.append({
            'cells': list(cleared_cells),
            'start_time': time.time(),
            'duration': 0.35,
        })

        # Calculate score: base points per line + combo bonus for simultaneous clears
        base_points = total_lines * config.SCORE_PER_LINE
        combo_bonus = (total_lines - 1) * config.SCORE_COMBO_BONUS if total_lines > 1 else 0
        total_points = base_points + combo_bonus

        return total_lines, total_points

    def can_piece_fit_anywhere(self, piece):
        """Checks if there is at least one legal position on the entire board for this piece."""
        for r in range(self.size - piece.rows + 1):
            for c in range(self.size - piece.cols + 1):
                if self.can_place(piece, r, c):
                    return True
        return False

    def get_cell_screen_coords(self, row, col):
        """Converts grid (row, col) to screen top-left (x, y)."""
        x = config.BOARD_OFFSET_X + col * config.BLOCK_CELL_PX
        y = config.BOARD_OFFSET_Y + row * config.BLOCK_CELL_PX
        return x, y

    def screen_to_grid(self, px, py):
        """Converts screen pixel (px, py) to nearest grid (row, col)."""
        col = int((px - config.BOARD_OFFSET_X) // config.BLOCK_CELL_PX)
        row = int((py - config.BOARD_OFFSET_Y) // config.BLOCK_CELL_PX)
        return row, col

    def update_animations(self):
        """Prunes expired line clear animations."""
        now = time.time()
        self.clear_animations = [
            anim for anim in self.clear_animations
            if now - anim['start_time'] < anim['duration']
        ]

    def render(self, surface, ghost_piece=None, ghost_row=None, ghost_col=None):
        """Renders board background, empty slots, occupied cells, and ghost preview."""
        board_w = self.size * config.BLOCK_CELL_PX
        board_h = self.size * config.BLOCK_CELL_PX
        board_rect = pygame.Rect(
            config.BOARD_OFFSET_X - 6,
            config.BOARD_OFFSET_Y - 6,
            board_w + 12,
            board_h + 12,
        )

        # Outer board plate
        pygame.draw.rect(surface, config.COLOR_GRID_BG, board_rect, border_radius=14)
        pygame.draw.rect(surface, config.COLOR_GRID_BORDER, board_rect, width=2, border_radius=14)

        cell_px = config.BLOCK_CELL_PX

        # 1. Render cells (empty or filled)
        for r in range(self.size):
            for c in range(self.size):
                cx, cy = self.get_cell_screen_coords(r, c)
                cell_rect = pygame.Rect(cx + 2, cy + 2, cell_px - 4, cell_px - 4)

                cell_val = self.grid[r][c]
                if cell_val is None:
                    # Empty cell well
                    pygame.draw.rect(surface, config.COLOR_GRID_EMPTY, cell_rect, border_radius=6)
                else:
                    # Filled cell with candy styling
                    r_val, g_val, b_val = cell_val
                    pygame.draw.rect(surface, (r_val, g_val, b_val), cell_rect, border_radius=6)
                    # Glossy top highlight
                    inner_rect = pygame.Rect(cx + 4, cy + 4, cell_px - 8, (cell_px - 8) // 2)
                    pygame.draw.rect(
                        surface,
                        (min(255, r_val + 50), min(255, g_val + 50), min(255, b_val + 50)),
                        inner_rect,
                        border_radius=4,
                    )

        # 2. Render line-clear flash animations
        now = time.time()
        for anim in self.clear_animations:
            elapsed = now - anim['start_time']
            progress = min(1.0, elapsed / anim['duration'])
            flash_alpha = int(255 * (1.0 - progress))
            flash_color = (255, 255, 255, flash_alpha)

            flash_surface = pygame.Surface((cell_px - 4, cell_px - 4), pygame.SRCALPHA)
            flash_surface.fill(flash_color)

            for r, c in anim['cells']:
                cx, cy = self.get_cell_screen_coords(r, c)
                surface.blit(flash_surface, (cx + 2, cy + 2))

        # 3. Render ghost piece if actively hovered
        if ghost_piece is not None and ghost_row is not None and ghost_col is not None:
            is_valid = self.can_place(ghost_piece, ghost_row, ghost_col)
            alpha = 180 if is_valid else 90

            for r in range(ghost_piece.rows):
                for c in range(ghost_piece.cols):
                    if ghost_piece.shape[r][c] == 1:
                        target_r = ghost_row + r
                        target_c = ghost_col + c
                        if 0 <= target_r < self.size and 0 <= target_c < self.size:
                            cx, cy = self.get_cell_screen_coords(target_r, target_c)
                            ghost_rect = pygame.Rect(cx + 2, cy + 2, cell_px - 4, cell_px - 4)

                            if is_valid:
                                color = config.COLOR_GHOST_VALID
                            else:
                                color = config.COLOR_GHOST_INVALID

                            ghost_surf = pygame.Surface((cell_px - 4, cell_px - 4), pygame.SRCALPHA)
                            ghost_surf.fill((*color, alpha))
                            surface.blit(ghost_surf, (cx + 2, cy + 2))
