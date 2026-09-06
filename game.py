"""
game.py - Unified GameManager for Multi-Game Platform
Owns RunnerGame and BlockBlastGame, routes gestures, composites the camera
picture-in-picture (PiP) feed, and persists high scores across sessions.
"""

import json
import os
import cv2
import numpy as np
import pygame
import config
from runner_game import RunnerGame
from block_game import BlockBlastGame


class GameManager:
    MODE_RUNNER = 'runner'
    MODE_BLOCK_BLAST = 'block_blast'

    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.surface = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT))
        self.font_pip = pygame.font.SysFont('arial', 12, bold=True)
        self.font_calib = pygame.font.SysFont('arial', 20, bold=True)

        # Load persisted high scores
        self.high_scores = self._load_high_scores()

        # Initialize game instances
        self.games = {
            self.MODE_RUNNER: RunnerGame(high_score=self.high_scores.get(self.MODE_RUNNER, 0)),
            self.MODE_BLOCK_BLAST: BlockBlastGame(high_score=self.high_scores.get(self.MODE_BLOCK_BLAST, 0)),
        }
        self.active_mode = self.MODE_RUNNER

        # PiP cache
        self.cached_pip_surface = None
        self.is_calibrating = False

        # Settings
        self.show_camera_pip = config.SHOW_CAMERA_PIP

    @property
    def active_game(self):
        return self.games[self.active_mode]

    @property
    def state(self):
        return self.active_game.state

    @property
    def score(self):
        return self.active_game.score

    def set_mode(self, mode):
        """Switches active game mode."""
        if mode in self.games and mode != self.active_mode:
            self._save_high_scores()
            self.active_mode = mode

    def start(self):
        """Starts current active game."""
        self.active_game.start()

    def reset(self):
        """Resets current active game."""
        self.active_game.reset()

    def apply_gesture(self, gesture_data):
        """Passes gesture recognition output to active game and caches PiP preview."""
        self.is_calibrating = gesture_data.get('is_calibrating', False)

        # Update PiP texture
        pip_frame = gesture_data.get('pip_frame')
        if pip_frame is not None:
            # OpenCV BGR -> RGB
            pip_rgb = cv2.cvtColor(pip_frame, cv2.COLOR_BGR2RGB)
            # Transpose to (W, H, 3) for pygame.surfarray
            transposed = np.transpose(pip_rgb, (1, 0, 2))
            self.cached_pip_surface = pygame.surfarray.make_surface(transposed)

        self.active_game.apply_gesture(gesture_data)

    def update(self, dt=1.0 / config.FPS):
        """Updates active game simulation and persists high scores."""
        self.active_game.update(dt)

        # Check and update persistent high scores
        current_score = self.active_game.score
        if current_score > self.high_scores.get(self.active_mode, 0):
            self.high_scores[self.active_mode] = int(current_score)
            self._save_high_scores()

    def render(self):
        """Composites game surface, PiP camera preview, and calibration overlay."""
        s = self.active_game.render(self.surface)

        # Render Camera PiP in top-right corner if enabled
        if self.show_camera_pip and self.cached_pip_surface is not None:
            pip_w, pip_h = config.PIP_WIDTH, config.PIP_HEIGHT
            pip_x = config.CANVAS_WIDTH - pip_w - config.PIP_MARGIN
            pip_y = config.PIP_MARGIN

            # Background shadow box
            shadow_rect = pygame.Rect(pip_x - 2, pip_y - 2, pip_w + 4, pip_h + 4)
            pygame.draw.rect(s, (15, 15, 25), shadow_rect, border_radius=8)

            s.blit(self.cached_pip_surface, (pip_x, pip_y))

            # Camera label
            lbl_surf = self.font_pip.render("WEBCAM", True, (255, 255, 255))
            s.blit(lbl_surf, (pip_x + 6, pip_y + 4))

        # Render Calibration Overlay if active
        if self.is_calibrating:
            calib_rect = pygame.Rect(40, config.CANVAS_HEIGHT // 2 - 40, config.CANVAS_WIDTH - 80, 80)
            pygame.draw.rect(s, (15, 20, 35), calib_rect, border_radius=12)
            pygame.draw.rect(s, (0, 210, 255), calib_rect, width=2, border_radius=12)

            t1 = self.font_calib.render("Calibrating Neutral Hand...", True, (0, 210, 255))
            t2 = self.font_pip.render("Hold hand centered in front of camera", True, (200, 210, 230))
            s.blit(t1, t1.get_rect(center=(config.CANVAS_WIDTH // 2, config.CANVAS_HEIGHT // 2 - 15)))
            s.blit(t2, t2.get_rect(center=(config.CANVAS_WIDTH // 2, config.CANVAS_HEIGHT // 2 + 15)))

        return s

    def get_jpeg_bytes(self):
        """Renders current frame and encodes to JPEG bytes."""
        surface = self.render()
        arr = pygame.surfarray.array3d(surface)
        arr = np.transpose(arr, (1, 0, 2))
        frame_bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        ok, buf = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY])
        if not ok:
            return None
        return buf.tobytes()

    def get_state(self):
        """Returns comprehensive state for the web interface."""
        game_state = self.active_game.get_state()
        return {
            'mode': self.active_mode,
            'state': game_state['state'],
            'score': game_state['score'],
            'high_score': self.high_scores.get(self.active_mode, 0),
            'show_camera_pip': self.show_camera_pip,
            'details': game_state.get('details', {}),
        }

    def _load_high_scores(self):
        try:
            if os.path.exists(config.HIGHSCORES_FILE):
                with open(config.HIGHSCORES_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {self.MODE_RUNNER: 0, self.MODE_BLOCK_BLAST: 0}

    def _save_high_scores(self):
        try:
            with open(config.HIGHSCORES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.high_scores, f, indent=2)
        except Exception:
            pass
