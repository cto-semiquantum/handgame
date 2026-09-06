"""
base_game.py - Abstract Base Class for Game Modes
Enforces a uniform lifecycle and rendering contract so GameManager
and Flask remain mode-agnostic.
"""

from abc import ABC, abstractmethod


class BaseGame(ABC):
    @abstractmethod
    def start(self):
        """Start or restart a gameplay session."""
        pass

    @abstractmethod
    def reset(self):
        """Reset game variables to default initial state."""
        pass

    @abstractmethod
    def apply_gesture(self, gesture_data):
        """
        Receive processed gesture input from GestureRecognizer.
        gesture_data dict contains:
            'lane': int or None (0, 1, 2)
            'gesture': str or None ('jump', 'slide', 'run')
            'cursor_pos': tuple of (x, y) normalized (0.0 to 1.0) or None
            'is_pinching': bool
            'hand_detected': bool
        """
        pass

    @abstractmethod
    def update(self, dt):
        """Advance physics, animations, and game state by dt seconds."""
        pass

    @abstractmethod
    def render(self, surface):
        """Render the game world and HUD onto the provided pygame.Surface."""
        pass

    @abstractmethod
    def get_state(self):
        """
        Return a state dictionary for the web UI:
            'state': 'menu' | 'playing' | 'gameover'
            'score': int
            'high_score': int
            'details': dict with mode-specific stats (e.g., combo, powerups)
        """
        pass
