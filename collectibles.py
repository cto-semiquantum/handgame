"""
collectibles.py - Golden Coins & Skateboard Pickups
Provides detailed rendering of spinning gold coins and energetic skateboards.
"""

import math
import random
import time
import pygame
import config


class Collectible:
    def __init__(self, lane, y, kind='coin'):
        self.lane = lane
        self.y = y
        self.kind = kind  # 'coin' | 'skateboard'
        self.w = config.COLLECTIBLE_W
        self.h = config.COLLECTIBLE_H
        self.spawn_time = time.time()

    def get_rect(self, canvas_width):
        lane_width = canvas_width / config.LANE_COUNT
        cx = int(lane_width * self.lane + lane_width / 2)
        x = cx - self.w // 2
        return (x, int(self.y), self.w, self.h)

    def render(self, surface, canvas_width):
        x, y, w, h = self.get_rect(canvas_width)
        cx = x + w // 2
        cy = y + h // 2

        now = time.time()
        spin_phase = (now - self.spawn_time) * 6.0

        if self.kind == 'coin':
            # Spinning Golden Coin
            radius = w // 2
            # Horizontal squeeze to simulate 3D rotation
            scale_x = abs(math.cos(spin_phase))
            coin_w = max(4, int(radius * 2 * scale_x))

            # Outer gold rim
            coin_rect = pygame.Rect(cx - coin_w // 2, cy - radius, coin_w, radius * 2)
            pygame.draw.ellipse(surface, (255, 180, 0), coin_rect)
            # Inner bright gold face
            inner_rect = pygame.Rect(cx - max(2, coin_w // 2 - 3), cy - radius + 3, max(2, coin_w - 6), (radius - 3) * 2)
            pygame.draw.ellipse(surface, (255, 225, 50), inner_rect)
            # Specular shine glint
            glint_surf = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
            pygame.draw.circle(glint_surf, (255, 255, 255, 120), ((w + 8) // 2, (h + 8) // 2), 4)
            surface.blit(glint_surf, (cx - (w + 8) // 2, cy - (h + 8) // 2))

        else:
            # Skateboard Power-Up
            deck_w = 40
            deck_h = 14
            bob = math.sin(now * 5.0) * 4.0
            deck_y = cy - deck_h // 2 + int(bob)

            # Energy glow halo
            glow = pygame.Surface((56, 32), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 200, 40, 90), (0, 0, 56, 32))
            surface.blit(glow, (cx - 28, deck_y - 8))

            # Deck
            pygame.draw.rect(surface, (245, 158, 11), (cx - deck_w // 2, deck_y, deck_w, deck_h), border_radius=5)
            pygame.draw.rect(surface, (255, 230, 100), (cx - deck_w // 2, deck_y, deck_w, deck_h), width=2, border_radius=5)
            # Wheels
            pygame.draw.circle(surface, (239, 68, 68), (cx - 12, deck_y + deck_h + 2), 4)
            pygame.draw.circle(surface, (239, 68, 68), (cx + 12, deck_y + deck_h + 2), 4)


class CollectibleManager:
    def __init__(self):
        self.items = []
        self.spawn_timer = 0.0

    def update(self, dt, scroll_speed, canvas_height):
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            self._spawn()
            self.spawn_timer = config.COLLECTIBLE_SPAWN_INTERVAL_S

        for item in self.items:
            item.y += scroll_speed * dt

        self.items = [c for c in self.items if c.y < canvas_height + 100]

    def _spawn(self):
        lane = random.randint(0, config.LANE_COUNT - 1)
        kind = 'skateboard' if random.random() < config.SKATEBOARD_SPAWN_CHANCE else 'coin'
        self.items.append(Collectible(lane, -config.COLLECTIBLE_H, kind))

    def remove(self, item):
        if item in self.items:
            self.items.remove(item)

    def reset(self):
        self.items = []
        self.spawn_timer = config.COLLECTIBLE_SPAWN_INTERVAL_S
