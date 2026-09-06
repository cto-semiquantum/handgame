"""
block_game.py - Block Blast Game Controller (v2.1)
Features:
- Dual-control grabbing: Pinch (thumb+index) OR Closed Fist over tray slot
- Dual-control dropping: Release pinch OR Open Palm over valid grid cells
- Forgiving placement: Pieces NEVER cancel or disappear on invalid drop;
  they remain held with clear visual feedback until placed or returned to tray
- Precise grid snapping with bright green (valid) and soft red (invalid) preview
- Simultaneous row/col clears, combo multipliers, and game-over detection
"""

import time
import pygame
import config
from base_game import BaseGame
from block_piece import TrayManager
from block_board import BlockBoard


class BlockBlastGame(BaseGame):
    STATE_MENU = 'menu'
    STATE_PLAYING = 'playing'
    STATE_GAMEOVER = 'gameover'

    def __init__(self, high_score=0):
        self.surface = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT))
        self.font_big = pygame.font.SysFont('arial', 38, bold=True)
        self.font_med = pygame.font.SysFont('arial', 24, bold=True)
        self.font_small = pygame.font.SysFont('arial', 16, bold=True)
        self.font_tiny = pygame.font.SysFont('arial', 13)

        self.board = BlockBoard()
        self.tray = TrayManager()

        self.state = self.STATE_MENU
        self.score = 0
        self.high_score = high_score
        self.combo_streak = 0

        self.cursor_px = config.CANVAS_WIDTH // 2
        self.cursor_py = config.CANVAS_HEIGHT // 2
        self.hand_detected = False
        self.is_pinching = False
        self.was_pinching = False
        self.is_fist = False
        self.is_open_palm = False

        self.held_piece = None
        self.held_from_slot = None

        # Visual feedback banners
        self.clear_banner_text = ""
        self.clear_banner_time = 0.0

        self.hint_message = ""
        self.hint_time = 0.0

        self._last_update = time.time()

    def start(self):
        self.reset()
        self.state = self.STATE_PLAYING
        self._last_update = time.time()

    def reset(self):
        self.board.reset()
        self.tray.refill(score=0)
        self.score = 0
        self.combo_streak = 0
        self.held_piece = None
        self.held_from_slot = None
        self.clear_banner_text = ""
        self.hint_message = ""

    def apply_gesture(self, gesture_data):
        self.hand_detected = gesture_data.get('hand_detected', False)
        cursor_pos = gesture_data.get('cursor_pos')
        pinching = gesture_data.get('is_pinching', False)
        fist = gesture_data.get('is_fist', False)
        open_palm = gesture_data.get('is_open_palm', False)

        if cursor_pos is not None:
            target_x = int(cursor_pos[0] * config.CANVAS_WIDTH)
            target_y = int(cursor_pos[1] * config.CANVAS_HEIGHT)

            # Responsive smooth cursor interpolation
            self.cursor_px = int(0.75 * target_x + 0.25 * self.cursor_px)
            self.cursor_py = int(0.75 * target_y + 0.25 * self.cursor_py)

        self.was_pinching = self.is_pinching
        self.is_pinching = pinching
        self.is_fist = fist
        self.is_open_palm = open_palm

        if self.state != self.STATE_PLAYING:
            return

        is_grabbing = self.is_pinching or self.is_fist

        # 1. Grabbing piece from tray
        if self.held_piece is None:
            if is_grabbing:
                slot_idx = self.tray.get_slot_at_pos(self.cursor_px, self.cursor_py)
                if slot_idx is not None:
                    piece = self.tray.take_piece(slot_idx)
                    if piece is not None:
                        self.held_piece = piece
                        self.held_from_slot = slot_idx
                        self.hint_message = "Piece Grabbed! Drag to Grid & Open Hand"
                        self.hint_time = time.time()

        # 2. Holding and putting piece
        elif self.held_piece is not None:
            # Drop triggers when user opens palm OR releases pinch/fist
            is_releasing = self.is_open_palm or (self.was_pinching and not self.is_pinching and not self.is_fist)

            if is_releasing:
                row, col = self._calculate_ghost_grid_pos()

                # Check if hovering over tray to cancel
                tray_slot = self.tray.get_slot_at_pos(self.cursor_px, self.cursor_py)
                if self.cursor_py >= config.TRAY_OFFSET_Y - 20:
                    # Return safely to tray
                    self.tray.return_piece(self.held_from_slot, self.held_piece)
                    self.held_piece = None
                    self.held_from_slot = None
                    self.hint_message = "Returned to Tray"
                    self.hint_time = time.time()

                elif row is not None and col is not None and self.board.can_place(self.held_piece, row, col):
                    # Valid placement!
                    placed = self.board.place(self.held_piece, row, col)
                    self.score += placed * config.SCORE_PER_PLACED_CELL

                    lines, line_points = self.board.check_and_clear_lines()
                    if lines > 0:
                        self.combo_streak += 1
                        self.score += line_points
                        self.clear_banner_text = f"+{line_points} ({lines} Lines!) Combo x{self.combo_streak}"
                        self.clear_banner_time = time.time()
                    else:
                        self.combo_streak = 0

                    if self.score > self.high_score:
                        self.high_score = self.score

                    self.held_piece = None
                    self.held_from_slot = None

                    self.tray.refill_if_empty(self.score)

                    if not self.tray.has_valid_move(self.board):
                        self.state = self.STATE_GAMEOVER
                else:
                    # Forgiving drop: do NOT lose the piece! Keep it attached so user can adjust
                    self.hint_message = "Place on green empty cells or drop on tray to cancel"
                    self.hint_time = time.time()

    def _calculate_ghost_grid_pos(self):
        if self.held_piece is None:
            return None, None

        piece_w = self.held_piece.cols * config.BLOCK_CELL_PX
        piece_h = self.held_piece.rows * config.BLOCK_CELL_PX

        # Offset slightly above cursor so hand doesn't block the view of target cells
        left_px = self.cursor_px - piece_w // 2
        top_px = self.cursor_py - piece_h // 2 - 15

        col = round((left_px - config.BOARD_OFFSET_X) / config.BLOCK_CELL_PX)
        row = round((top_px - config.BOARD_OFFSET_Y) / config.BLOCK_CELL_PX)
        return row, col

    def update(self, dt):
        self.board.update_animations()

    def render(self, surface):
        surface.fill((241, 245, 249))  # Clean light theme background

        # 1. Header & Scores
        self._render_header(surface)

        # 2. Board with ghost piece preview
        ghost_r, ghost_c = None, None
        if self.held_piece is not None:
            ghost_r, ghost_c = self._calculate_ghost_grid_pos()

        self.board.render(surface, ghost_piece=self.held_piece, ghost_row=ghost_r, ghost_col=ghost_c)

        # 3. Tray slots & remaining pieces
        self.tray.render(surface)

        # 4. Held piece floating with hand cursor
        if self.held_piece is not None:
            cell_px = config.BLOCK_CELL_PX
            piece_w = self.held_piece.cols * cell_px
            piece_h = self.held_piece.rows * cell_px
            px = self.cursor_px - piece_w // 2
            py = self.cursor_py - piece_h // 2 - 15

            # Floating shadow
            shadow_surf = pygame.Surface((piece_w + 12, piece_h + 12), pygame.SRCALPHA)
            pygame.draw.rect(shadow_surf, (0, 0, 0, 60), (0, 0, piece_w + 12, piece_h + 12), border_radius=8)
            surface.blit(shadow_surf, (px - 2, py + 8))

            self.held_piece.render(surface, px, py, cell_px, alpha=240)

        # 5. Visual notifications
        self._render_banners(surface)

        # 6. Hand Cursor
        self._render_cursor(surface)

        # 7. Menu / GameOver overlays
        if self.state == self.STATE_MENU:
            self._render_menu(surface)
        elif self.state == self.STATE_GAMEOVER:
            self._render_gameover(surface)

        return surface

    def _render_header(self, surface):
        plate = pygame.Surface((config.CANVAS_WIDTH - 24, 76), pygame.SRCALPHA)
        pygame.draw.rect(plate, (255, 255, 255), (0, 0, config.CANVAS_WIDTH - 24, 76), border_radius=14)
        pygame.draw.rect(plate, (226, 232, 240), (0, 0, config.CANVAS_WIDTH - 24, 76), width=2, border_radius=14)
        surface.blit(plate, (12, 10))

        title = self.font_med.render("BLOCK BLAST", True, (37, 99, 235))
        surface.blit(title, (24, 18))

        score_lbl = self.font_tiny.render("SCORE", True, (100, 116, 139))
        score_val = self.font_big.render(str(int(self.score)), True, (15, 23, 42))
        surface.blit(score_lbl, (200, 16))
        surface.blit(score_val, (200, 32))

        best_lbl = self.font_tiny.render("BEST", True, (100, 116, 139))
        best_val = self.font_big.render(str(int(self.high_score)), True, (245, 158, 11))
        surface.blit(best_lbl, (300, 16))
        surface.blit(best_val, (300, 32))

        status_color = (16, 185, 129) if self.hand_detected else (239, 68, 68)
        status_text = "🟢 Tracking OK" if self.hand_detected else "🔴 Hand Lost"
        surface.blit(self.font_tiny.render(status_text, True, status_color), (24, 52))

    def _render_banners(self, surface):
        now = time.time()
        if now - self.clear_banner_time < 1.5:
            banner = self.font_med.render(self.clear_banner_text, True, (245, 158, 11))
            rect = banner.get_rect(center=(config.CANVAS_WIDTH // 2, config.BOARD_OFFSET_Y - 16))
            surface.blit(banner, rect)

        if now - self.hint_time < 2.0:
            hint = self.font_small.render(self.hint_message, True, (37, 99, 235))
            rect = hint.get_rect(center=(config.CANVAS_WIDTH // 2, config.TRAY_OFFSET_Y - 14))
            surface.blit(hint, rect)

    def _render_cursor(self, surface):
        if not self.hand_detected:
            return

        is_active = self.is_pinching or self.is_fist
        radius = 14 if is_active else 18
        ring_color = (245, 158, 11) if is_active else (37, 99, 235)

        pygame.draw.circle(surface, ring_color, (self.cursor_px, self.cursor_py), radius, 3)
        pygame.draw.circle(surface, (255, 255, 255), (self.cursor_px, self.cursor_py), 5)
        pygame.draw.circle(surface, ring_color, (self.cursor_px, self.cursor_py), 3)

    def _render_menu(self, surface):
        overlay = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 210))
        surface.blit(overlay, (0, 0))

        title = self.font_big.render("Block Blast", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(config.CANVAS_WIDTH // 2, 210)))

        sub = self.font_med.render("Gesture Block Puzzle", True, (37, 99, 235))
        surface.blit(sub, sub.get_rect(center=(config.CANVAS_WIDTH // 2, 255)))

        instructions = [
            "1. Move hand to guide on-screen cursor",
            "2. Hover piece + PINCH or MAKE FIST to grab",
            "3. Drag onto grid & OPEN PALM to place",
            "4. Fill complete rows & columns to clear!",
        ]
        for i, text in enumerate(instructions):
            txt_surf = self.font_small.render(text, True, (226, 232, 240))
            surface.blit(txt_surf, txt_surf.get_rect(center=(config.CANVAS_WIDTH // 2, 320 + i * 36)))

        hint = self.font_med.render("Click Start Below to Play", True, (245, 158, 11))
        surface.blit(hint, hint.get_rect(center=(config.CANVAS_WIDTH // 2, 510)))

    def _render_gameover(self, surface):
        overlay = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 225))
        surface.blit(overlay, (0, 0))

        title = self.font_big.render("No Moves Left!", True, (239, 68, 68))
        surface.blit(title, title.get_rect(center=(config.CANVAS_WIDTH // 2, 250)))

        score_txt = self.font_med.render(f"Final Score: {int(self.score)}", True, (255, 255, 255))
        surface.blit(score_txt, score_txt.get_rect(center=(config.CANVAS_WIDTH // 2, 310)))

        best_txt = self.font_small.render(f"Best Score: {int(self.high_score)}", True, (245, 158, 11))
        surface.blit(best_txt, best_txt.get_rect(center=(config.CANVAS_WIDTH // 2, 350)))

        hint = self.font_small.render("Click Restart to play again", True, (16, 185, 129))
        surface.blit(hint, hint.get_rect(center=(config.CANVAS_WIDTH // 2, 410)))

    def get_state(self):
        return {
            'state': self.state,
            'score': int(self.score),
            'high_score': int(self.high_score),
            'details': {
                'combo_streak': self.combo_streak,
                'held_piece': self.held_piece.name if self.held_piece else None,
            },
        }
