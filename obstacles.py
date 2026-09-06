"""
obstacles.py - Road Hazards & Construction Barriers
Draws authentic road obstacles:
- Traffic Safety Cones with reflective stripes
- Road Construction Barricades with yellow/black hazard stripes
- Low Hurdle Barriers (jump over)
- Elevated Clearance Hazard Beams (slide under)
"""

import random
import pygame
import config


class Obstacle:
    def __init__(self, lane, y, kind='barrier'):
        self.lane = lane
        self.y = y
        self.kind = kind  # 'cone' | 'barrier' | 'hurdle'
        self.w = config.OBSTACLE_W
        self.h = config.OBSTACLE_H

    def get_rect(self, canvas_width):
        lane_width = canvas_width / config.LANE_COUNT
        cx = int(lane_width * self.lane + lane_width / 2)
        x = cx - self.w // 2
        return (x, int(self.y), self.w, self.h)

    def render(self, surface, canvas_width):
        x, y, w, h = self.get_rect(canvas_width)
        cx = x + w // 2

        if self.kind == 'cone':
            # Traffic Safety Cone
            # Black base
            base_rect = pygame.Rect(x + 10, y + h - 16, w - 20, 14)
            pygame.draw.rect(surface, (25, 25, 35), base_rect, border_radius=4)
            # Orange Cone Body (Polygon)
            pts = [(cx, y + 6), (x + 14, y + h - 14), (x + w - 14, y + h - 14)]
            pygame.draw.polygon(surface, (255, 107, 0), pts)
            # White reflective band
            band_pts = [
                (cx - 9, y + 26),
                (cx + 9, y + 26),
                (cx + 13, y + 42),
                (cx - 13, y + 42),
            ]
            pygame.draw.polygon(surface, (255, 255, 255), band_pts)
            # Cone tip rounded
            pygame.draw.circle(surface, (255, 107, 0), (cx, y + 8), 6)

        elif self.kind == 'hurdle':
            # Low Road Hurdle (jumpable)
            leg_color = (160, 165, 185)
            board_y = y + h - 38
            # Legs
            pygame.draw.line(surface, leg_color, (x + 8, y + h - 6), (x + 8, board_y), 4)
            pygame.draw.line(surface, leg_color, (x + w - 8, y + h - 6), (x + w - 8, board_y), 4)
            pygame.draw.line(surface, leg_color, (x + 2, y + h - 4), (x + 14, y + h - 4), 4)
            pygame.draw.line(surface, leg_color, (x + w - 14, y + h - 4), (x + w - 2, y + h - 4), 4)
            # Crossboard with red/white hazard stripes
            board_rect = pygame.Rect(x + 4, board_y, w - 8, 22)
            pygame.draw.rect(surface, (240, 240, 245), board_rect, border_radius=4)
            # Red warning diagonal stripes
            for i in range(4):
                stripe_x = x + 8 + i * 14
                pygame.draw.line(surface, (239, 68, 68), (stripe_x, board_y + 20), (stripe_x + 10, board_y + 2), 4)
            pygame.draw.rect(surface, (80, 85, 105), board_rect, width=2, border_radius=4)

        else:
            # Construction Barricade with yellow/black hazard stripes
            frame_color = (200, 75, 45)
            # Metal A-frame legs
            pygame.draw.line(surface, frame_color, (x + 6, y + h - 4), (x + 12, y + 10), 4)
            pygame.draw.line(surface, frame_color, (x + w - 6, y + h - 4), (x + w - 12, y + 10), 4)
            # Top barricade board
            board_rect = pygame.Rect(x + 2, y + 12, w - 4, 34)
            pygame.draw.rect(surface, (255, 205, 10), board_rect, border_radius=4)
            # Black diagonal hazard stripes
            for i in range(-1, 5):
                sx = x + 6 + i * 16
                pygame.draw.polygon(surface, (25, 25, 30), [
                    (sx, y + 12),
                    (sx + 10, y + 12),
                    (sx + 2, y + 46),
                    (sx - 8, y + 46),
                ])
            # Outer stroke
            pygame.draw.rect(surface, (50, 50, 60), board_rect, width=2, border_radius=4)


class ObstacleManager:
    def __init__(self):
        self.obstacles = []
        self.spawn_timer = 0.0

    def update(self, dt, scroll_speed, canvas_height):
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn()
            # Gradually speed up spawn slightly as player speeds up
            self.spawn_timer = max(0.85, config.OBSTACLE_SPAWN_INTERVAL_S - (scroll_speed - 260) * 0.0008)

        for obs in self.obstacles:
            obs.y += scroll_speed * dt

        self.obstacles = [o for o in self.obstacles if o.y < canvas_height + 100]

    def _spawn(self):
        lane = random.randint(0, config.LANE_COUNT - 1)
        kind = random.choice(['cone', 'barrier', 'hurdle'])
        self.obstacles.append(Obstacle(lane, -config.OBSTACLE_H, kind))

    def reset(self):
        self.obstacles = []
        self.spawn_timer = config.OBSTACLE_SPAWN_INTERVAL_S
