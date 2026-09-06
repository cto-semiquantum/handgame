"""
runner_game.py - Road Runner: Protect the Boy! (v2.2)
Controls:
- Hand Left / Right -> Boy steers across lanes
- Fist-to-Open Hand -> Boy Jumps!
- Held Closed Fist -> Game Paused / Stopped
- Avoid Cones & Barricades, Collect Coins & Skateboards
"""

import math
import time
import pygame
import config
from base_game import BaseGame
from player import Player
from obstacles import ObstacleManager
from collectibles import CollectibleManager


def _rects_overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


class RunnerGame(BaseGame):
    STATE_MENU = 'menu'
    STATE_PLAYING = 'playing'
    STATE_PAUSED = 'paused'
    STATE_GAMEOVER = 'gameover'

    def __init__(self, high_score=0):
        self.surface = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT))
        self.font_big = pygame.font.SysFont('arial', 38, bold=True)
        self.font_med = pygame.font.SysFont('arial', 24, bold=True)
        self.font_small = pygame.font.SysFont('arial', 16, bold=True)
        self.font_tiny = pygame.font.SysFont('arial', 13)

        self.player = Player()
        self.obstacle_mgr = ObstacleManager()
        self.collectible_mgr = CollectibleManager()

        self.state = self.STATE_MENU
        self.score = 0
        self.high_score = high_score
        self.coins_collected = 0
        self.distance_m = 0.0
        self.scroll_speed = config.BASE_SCROLL_SPEED
        self.road_scroll = 0.0
        self.hearts = 3

        self._last_update = time.time()
        self.last_gesture = 'run'
        self.hand_detected = False

    def start(self):
        self.reset()
        self.state = self.STATE_PLAYING
        self._last_update = time.time()

    def reset(self):
        self.player.reset()
        self.obstacle_mgr.reset()
        self.collectible_mgr.reset()
        self.score = 0
        self.coins_collected = 0
        self.distance_m = 0.0
        self.scroll_speed = config.BASE_SCROLL_SPEED
        self.road_scroll = 0.0
        self.hearts = 3
        self.last_gesture = 'run'

    def apply_gesture(self, gesture_data):
        self.hand_detected = gesture_data.get('hand_detected', False)
        lane = gesture_data.get('lane')
        gesture = gesture_data.get('gesture')
        jump_triggered = gesture_data.get('jump_triggered', False)
        stop_triggered = gesture_data.get('stop_triggered', False)

        self.last_gesture = gesture or 'run'

        # Closed fist -> Stop / Pause Game
        if stop_triggered:
            if self.state == self.STATE_PLAYING:
                self.state = self.STATE_PAUSED
                return

        # Resume if paused and open hand / jump occurs
        if self.state == self.STATE_PAUSED:
            if jump_triggered or gesture_data.get('is_open_palm', False):
                self.state = self.STATE_PLAYING
            return

        if self.state != self.STATE_PLAYING:
            return

        # Steering: Left / Center / Right
        if lane is not None:
            self.player.set_lane(lane)

        # Fist-to-Open Jump trigger
        if jump_triggered:
            self.player.jump()

    def update(self, dt):
        dt = min(dt, 0.06)

        if self.state != self.STATE_PLAYING:
            return

        self.road_scroll = (self.road_scroll + self.scroll_speed * dt) % 60.0
        self.distance_m += (self.scroll_speed * dt) * 0.05

        self.player.update(dt, self.scroll_speed)

        self.scroll_speed = min(
            config.MAX_SCROLL_SPEED,
            self.scroll_speed + config.SCROLL_SPEED_INCREMENT * dt,
        )

        self.obstacle_mgr.update(dt, self.scroll_speed, config.CANVAS_HEIGHT)
        self.collectible_mgr.update(dt, self.scroll_speed, config.CANVAS_HEIGHT)

        self.score += config.SCORE_PER_SECOND * dt
        if self.score > self.high_score:
            self.high_score = self.score

        player_rect = self.player.get_rect(config.CANVAS_WIDTH, config.CANVAS_HEIGHT)

        # Obstacle collisions
        if not self.player.skateboard:
            for obs in self.obstacle_mgr.obstacles:
                obs_rect = obs.get_rect(config.CANVAS_WIDTH)
                # Successful jump over cones and hurdles
                if self.player.state == 'jumping':
                    continue

                if _rects_overlap(player_rect, obs_rect):
                    self.hearts -= 1
                    if self.hearts <= 0:
                        self.state = self.STATE_GAMEOVER
                    else:
                        # Brief shield immunity after taking a hit
                        self.player.activate_skateboard()
                    break

        # Collectible pickups
        for item in list(self.collectible_mgr.items):
            if _rects_overlap(player_rect, item.get_rect(config.CANVAS_WIDTH)):
                if item.kind == 'coin':
                    self.coins_collected += 1
                    self.score += config.SCORE_PER_COIN
                    if self.score > self.high_score:
                        self.high_score = self.score
                else:
                    self.player.activate_skateboard()
                self.collectible_mgr.remove(item)

    def render(self, surface):
        self._render_environment(surface)

        for obs in self.obstacle_mgr.obstacles:
            obs.render(surface, config.CANVAS_WIDTH)

        for item in self.collectible_mgr.items:
            item.render(surface, config.CANVAS_WIDTH)

        self.player.render(surface, config.CANVAS_WIDTH, config.CANVAS_HEIGHT)
        self._draw_hud(surface)

        if self.state == self.STATE_MENU:
            self._render_menu(surface)
        elif self.state == self.STATE_PAUSED:
            self._render_paused(surface)
        elif self.state == self.STATE_GAMEOVER:
            self._render_gameover(surface)

        return surface

    def _render_environment(self, surface):
        cw = config.CANVAS_WIDTH
        ch = config.CANVAS_HEIGHT

        surface.fill((34, 139, 34))

        road_margin = 28
        road_rect = pygame.Rect(road_margin, 0, cw - road_margin * 2, ch)
        pygame.draw.rect(surface, (45, 48, 62), road_rect)

        curb_h = 24
        curb_offset = int(self.road_scroll) % curb_h
        for y_curb in range(-curb_h, ch + curb_h, curb_h):
            idx = (y_curb + curb_offset) // curb_h
            curb_color = (239, 68, 68) if (idx % 2 == 0) else (248, 250, 252)
            pygame.draw.rect(surface, curb_color, (road_margin - 8, y_curb + curb_offset, 8, curb_h))
            pygame.draw.rect(surface, curb_color, (cw - road_margin, y_curb + curb_offset, 8, curb_h))

        lane_w = cw / config.LANE_COUNT
        stripe_len = 32
        gap_len = 28
        cycle = stripe_len + gap_len
        scroll_offset = int(self.road_scroll) % cycle

        for i in range(1, config.LANE_COUNT):
            lx = int(lane_w * i)
            for y in range(-cycle, ch + cycle, cycle):
                sy = y + scroll_offset
                pygame.draw.line(surface, (230, 235, 245), (lx, sy), (lx, sy + stripe_len), 4)

    def _draw_hud(self, surface):
        plate = pygame.Surface((config.CANVAS_WIDTH - 24, 76), pygame.SRCALPHA)
        pygame.draw.rect(plate, (15, 23, 42, 210), (0, 0, config.CANVAS_WIDTH - 24, 76), border_radius=12)
        surface.blit(plate, (12, 10))

        title = self.font_small.render("ROAD RUNNER", True, (16, 185, 129))
        surface.blit(title, (24, 18))

        dist_txt = self.font_tiny.render(f"Distance: {int(self.distance_m)}m", True, (148, 163, 184))
        surface.blit(dist_txt, (24, 38))

        heart_str = "❤ " * self.hearts
        heart_surf = self.font_small.render(heart_str, True, (239, 68, 68))
        surface.blit(heart_surf, (24, 58))

        score_lbl = self.font_tiny.render("SCORE", True, (148, 163, 184))
        score_val = self.font_big.render(str(int(self.score)), True, (255, 255, 255))
        surface.blit(score_lbl, (180, 16))
        surface.blit(score_val, (180, 32))

        coin_txt = self.font_small.render(f"🪙 {self.coins_collected}", True, (245, 158, 11))
        surface.blit(coin_txt, (280, 20))

        best_txt = self.font_tiny.render(f"BEST: {int(self.high_score)}", True, (255, 215, 0))
        surface.blit(best_txt, (280, 44))

        if self.player.skateboard:
            remaining_s = max(0.0, self.player.skateboard_until - time.time())
            pct = remaining_s / config.SKATEBOARD_DURATION_S
            bar_w = 200
            bar_h = 8
            bar_x = 24
            bar_y = 96

            pygame.draw.rect(surface, (15, 23, 42), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4), border_radius=4)
            pygame.draw.rect(surface, (245, 158, 11), (bar_x, bar_y, int(bar_w * pct), bar_h), border_radius=4)
            sk_txt = self.font_tiny.render("⚡ SKATEBOARD SHIELD ACTIVE!", True, (245, 158, 11))
            surface.blit(sk_txt, (bar_x, bar_y + 12))

    def _render_menu(self, surface):
        overlay = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 220))
        surface.blit(overlay, (0, 0))

        title = self.font_big.render("Road Runner", True, (255, 255, 255))
        surface.blit(title, title.get_rect(center=(config.CANVAS_WIDTH // 2, 200)))

        sub = self.font_med.render("Protect the Boy on the Road!", True, (16, 185, 129))
        surface.blit(sub, sub.get_rect(center=(config.CANVAS_WIDTH // 2, 245)))

        instructions = [
            "👈 Move hand Left   -> Steer Left",
            "👉 Move hand Right  -> Steer Right",
            "✊ Close fist then 🖐 Open hand -> JUMP!",
            "✊ Hold closed fist -> STOP / PAUSE",
        ]
        for i, text in enumerate(instructions):
            txt_surf = self.font_small.render(text, True, (226, 232, 240))
            surface.blit(txt_surf, txt_surf.get_rect(center=(config.CANVAS_WIDTH // 2, 310 + i * 38)))

        hint = self.font_med.render("Click Play Game Below", True, (245, 158, 11))
        surface.blit(hint, hint.get_rect(center=(config.CANVAS_WIDTH // 2, 510)))

    def _render_paused(self, surface):
        overlay = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 210))
        surface.blit(overlay, (0, 0))

        title = self.font_big.render("GAME PAUSED", True, (245, 158, 11))
        surface.blit(title, title.get_rect(center=(config.CANVAS_WIDTH // 2, 280)))

        msg = self.font_small.render("🖐 Show open hand or click Play to Resume", True, (255, 255, 255))
        surface.blit(msg, msg.get_rect(center=(config.CANVAS_WIDTH // 2, 340)))

    def _render_gameover(self, surface):
        overlay = pygame.Surface((config.CANVAS_WIDTH, config.CANVAS_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 23, 42, 230))
        surface.blit(overlay, (0, 0))

        title = self.font_big.render("Crash! Game Over", True, (239, 68, 68))
        surface.blit(title, title.get_rect(center=(config.CANVAS_WIDTH // 2, 250)))

        score_txt = self.font_med.render(f"Final Score: {int(self.score)}", True, (255, 255, 255))
        surface.blit(score_txt, score_txt.get_rect(center=(config.CANVAS_WIDTH // 2, 310)))

        dist_txt = self.font_small.render(f"Distance Survived: {int(self.distance_m)} meters", True, (148, 163, 184))
        surface.blit(dist_txt, dist_txt.get_rect(center=(config.CANVAS_WIDTH // 2, 345)))

        coins_txt = self.font_small.render(f"Coins: {self.coins_collected} | Best: {int(self.high_score)}", True, (245, 158, 11))
        surface.blit(coins_txt, coins_txt.get_rect(center=(config.CANVAS_WIDTH // 2, 375)))

        hint = self.font_small.render("Click Restart to play again!", True, (16, 185, 129))
        surface.blit(hint, hint.get_rect(center=(config.CANVAS_WIDTH // 2, 435)))

    def get_state(self):
        return {
            'state': self.state,
            'score': int(self.score),
            'high_score': int(self.high_score),
            'details': {
                'distance_m': int(self.distance_m),
                'coins': self.coins_collected,
                'hearts': self.hearts,
                'skateboard': self.player.skateboard,
                'last_gesture': self.last_gesture,
            },
        }
