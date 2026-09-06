"""
config.py - Unified Configuration for Gesture-Controlled Web Game Platform (v2)
Single source of truth for both game modes, gesture processing, and rendering.
"""

import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HIGHSCORES_FILE = os.path.join(BASE_DIR, 'highscores.json')

# ---- Canvas & Video Streaming ----
CANVAS_WIDTH = 480
CANVAS_HEIGHT = 720
FPS = 30
JPEG_QUALITY = 78

# ---- Camera & Vision Pipeline ----
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
INFERENCE_WIDTH = 320
INFERENCE_HEIGHT = 240
MIN_DETECTION_CONFIDENCE = 0.6
MIN_TRACKING_CONFIDENCE = 0.5
CAMERA_MIRROR = True

# Picture-in-Picture (PiP) Skeleton Camera Preview
SHOW_CAMERA_PIP = True
PIP_WIDTH = 130
PIP_HEIGHT = 98
PIP_MARGIN = 10

# ---- Signal Smoothing & Gesture Reliability ----
EMA_ALPHA = 0.50                       # Snappier tracking response without jitter
HYSTERESIS_MARGIN = 0.04               # Deadband around lane boundaries (prevents jitter)
GESTURE_CONFIRM_FRAMES = 3             # Consecutive frames needed to confirm discrete gestures
HAND_LOST_GRACE_PERIOD_S = 0.45        # Seconds to preserve tracking during brief drops
PINCH_DISTANCE_THRESHOLD = 0.058       # Normalized Euclidean distance (thumb tip to index tip)
PINCH_RELEASE_THRESHOLD = 0.085        # Hysteresis threshold to release pinch

# Lane boundaries (normalized 0-1, mirrored)
LANE_BOUNDARY_LEFT = 0.38
LANE_BOUNDARY_RIGHT = 0.62

# ---- Endless Runner Settings ----
LANE_COUNT = 3
PLAYER_W = 60
PLAYER_H = 100
JUMP_DURATION_MS = 500
SLIDE_DURATION_MS = 500

OBSTACLE_W = 70
OBSTACLE_H = 70
OBSTACLE_SPAWN_INTERVAL_S = 1.2

COLLECTIBLE_W = 32
COLLECTIBLE_H = 32
COLLECTIBLE_SPAWN_INTERVAL_S = 0.8
SCORE_PER_COIN = 10

BASE_SCROLL_SPEED = 260
SCROLL_SPEED_INCREMENT = 6
MAX_SCROLL_SPEED = 700
SCORE_PER_SECOND = 5

SKATEBOARD_DURATION_S = 6.0
SKATEBOARD_SPAWN_CHANCE = 0.06

# ---- Block Blast Settings ----
BLOCK_GRID_SIZE = 8                    # 8x8 grid
BLOCK_CELL_PX = 46                     # Grid cell size in pixels (8 * 46 = 368px)
BOARD_OFFSET_X = (CANVAS_WIDTH - BLOCK_GRID_SIZE * BLOCK_CELL_PX) // 2   # 56px
BOARD_OFFSET_Y = 120                   # Vertical position of the board
TRAY_OFFSET_Y = 530                    # Vertical position of the piece tray
TRAY_SLOT_COUNT = 3
TRAY_SLOT_WIDTH = 130
TRAY_SLOT_HEIGHT = 120
TRAY_SPACING = (CANVAS_WIDTH - TRAY_SLOT_COUNT * TRAY_SLOT_WIDTH) // (TRAY_SLOT_COUNT + 1)

# Block Blast Scoring
SCORE_PER_PLACED_CELL = 1
SCORE_PER_LINE = 10
SCORE_COMBO_BONUS = 15                 # Multiplied by combo multiplier

# ---- Color Palette (Vibrant Arcade/Candy Theme) ----
COLOR_BG = (22, 22, 34)
COLOR_CARD_BG = (32, 34, 52)
COLOR_TEXT = (245, 245, 255)
COLOR_TEXT_MUTED = (160, 165, 185)
COLOR_ACCENT = (75, 215, 165)
COLOR_GAMEOVER = (255, 75, 110)

# Runner Colors
COLOR_LANE_LINE = (45, 48, 70)
COLOR_PLAYER = (46, 213, 115)
COLOR_PLAYER_SKATEBOARD = (255, 200, 60)
COLOR_OBSTACLE = (255, 75, 110)
COLOR_COIN = (255, 215, 0)

# Block Blast Board & Cell Colors
COLOR_GRID_BG = (28, 30, 46)
COLOR_GRID_EMPTY = (38, 42, 64)
COLOR_GRID_BORDER = (52, 58, 86)
COLOR_GHOST_VALID = (100, 240, 160)
COLOR_GHOST_INVALID = (255, 90, 110)
COLOR_CURSOR = (255, 255, 255)
COLOR_CURSOR_PINCH = (255, 215, 0)

# Block Piece Colors (Saturated, Distinct)
BLOCK_COLORS = [
    (255, 94, 87),    # Coral Red
    (255, 165, 2),    # Bright Orange
    (255, 211, 42),   # Golden Yellow
    (46, 213, 115),   # Emerald Green
    (24, 220, 255),   # Cyan
    (112, 111, 211),  # Violet
    (255, 82, 82),    # Candy Pink
    (52, 152, 219),   # Sky Blue
]

# PiP Status Indicator Colors
COLOR_PIP_TRACKED = (46, 213, 115)
COLOR_PIP_LOST = (255, 75, 75)
