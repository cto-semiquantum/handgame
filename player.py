"""
player.py - Animated Boy Runner Character (v2.2)
Features:
- Instant snappy horizontal lane gliding (lerp speed 26.0)
- High-energy running sprint cycle
- Realistic asphalt shadow during leaps
- Skateboard riding posture with glowing aura
"""

import math
import time
import pygame
import config


class Player:
    def __init__(self):
        self.lane = 1
        self.state = 'running'
        self.state_until = 0.0
        self.skateboard = False
        self.skateboard_until = 0.0

        self.current_x = float(self.lane_center_x(config.CANVAS_WIDTH))
        self.target_x = float(self.current_x)
        self.run_anim_phase = 0.0

    def lane_center_x(self, canvas_width):
        lane_width = canvas_width / config.LANE_COUNT
        return int(lane_width * self.lane + lane_width / 2)

    def set_lane(self, lane):
        self.lane = max(0, min(config.LANE_COUNT - 1, lane))
        self.target_x = float(self.lane_center_x(config.CANVAS_WIDTH))

    def move_left(self):
        if self.lane > 0:
            self.set_lane(self.lane - 1)

    def move_right(self):
        if self.lane < config.LANE_COUNT - 1:
            self.set_lane(self.lane + 1)

    def jump(self):
        if self.state == 'running':
            self.state = 'jumping'
            self.state_until = time.time() + (config.JUMP_DURATION_MS / 1000)

    def slide(self):
        if self.state == 'running':
            self.state = 'sliding'
            self.state_until = time.time() + (config.SLIDE_DURATION_MS / 1000)

    def activate_skateboard(self):
        self.skateboard = True
        self.skateboard_until = time.time() + config.SKATEBOARD_DURATION_S

    def update(self, dt=0.033, scroll_speed=260.0):
        now = time.time()
        if self.state in ('jumping', 'sliding') and now >= self.state_until:
            self.state = 'running'
        if self.skateboard and now >= self.skateboard_until:
            self.skateboard = False

        self.target_x = float(self.lane_center_x(config.CANVAS_WIDTH))
        # Snappy, responsive horizontal interpolation
        lerp_speed = 26.0 * dt
        self.current_x += (self.target_x - self.current_x) * min(1.0, lerp_speed)

        speed_factor = max(1.0, scroll_speed / 240.0)
        self.run_anim_phase += dt * 14.0 * speed_factor

    def get_rect(self, canvas_width, canvas_height):
        cx = int(self.current_x)
        base_y = canvas_height - 165

        w = config.PLAYER_W
        h = config.PLAYER_H

        if self.state == 'jumping':
            jump_progress = 0.5
            if self.state_until > 0:
                total_duration = config.JUMP_DURATION_MS / 1000.0
                remaining = max(0.0, self.state_until - time.time())
                jump_progress = 1.0 - (remaining / total_duration)

            jump_offset = math.sin(jump_progress * math.pi) * 85.0
            y = int(base_y - jump_offset)
        elif self.state == 'sliding':
            h = config.PLAYER_H // 2
            y = base_y + config.PLAYER_H - h
        else:
            y = base_y

        x = cx - w // 2
        return (x, y, w, h)

    def reset(self):
        self.lane = 1
        self.state = 'running'
        self.state_until = 0.0
        self.skateboard = False
        self.skateboard_until = 0.0
        self.current_x = float(self.lane_center_x(config.CANVAS_WIDTH))
        self.target_x = float(self.current_x)
        self.run_anim_phase = 0.0

    def render(self, surface, canvas_width, canvas_height):
        cx = int(self.current_x)
        base_ground_y = canvas_height - 65

        # 1. Road Shadow
        shadow_w = 46
        shadow_h = 14
        if self.state == 'jumping':
            jump_progress = 0.5
            if self.state_until > 0:
                total_duration = config.JUMP_DURATION_MS / 1000.0
                remaining = max(0.0, self.state_until - time.time())
                jump_progress = 1.0 - (remaining / total_duration)
            jump_y_offset = math.sin(jump_progress * math.pi) * 85.0
            shadow_w = int(46 * (1.0 - 0.3 * (jump_y_offset / 85.0)))
            shadow_h = int(14 * (1.0 - 0.3 * (jump_y_offset / 85.0)))
        else:
            jump_y_offset = 0.0

        shadow_surf = pygame.Surface((shadow_w, shadow_h), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (15, 18, 28, 140), (0, 0, shadow_w, shadow_h))
        surface.blit(shadow_surf, (cx - shadow_w // 2, base_ground_y - shadow_h // 2))

        char_y = base_ground_y - jump_y_offset

        # 2. Skateboard
        if self.skateboard:
            deck_w = 54
            deck_h = 10
            deck_y = char_y - 10
            deck_rect = pygame.Rect(cx - deck_w // 2, deck_y, deck_w, deck_h)
            pygame.draw.rect(surface, (235, 150, 45), deck_rect, border_radius=4)
            pygame.draw.rect(surface, (255, 220, 80), deck_rect, width=2, border_radius=4)
            pygame.draw.circle(surface, (255, 80, 50), (cx - 18, deck_y + deck_h), 5)
            pygame.draw.circle(surface, (255, 80, 50), (cx + 18, deck_y + deck_h), 5)

            aura_surf = pygame.Surface((70, 110), pygame.SRCALPHA)
            pygame.draw.ellipse(aura_surf, (255, 200, 50, 60), (0, 0, 70, 110))
            surface.blit(aura_surf, (cx - 35, char_y - 100))

        # 3. Boy Pose
        swing = math.sin(self.run_anim_phase)
        cos_swing = math.cos(self.run_anim_phase)

        skin_color = (255, 205, 175)
        hair_color = (65, 40, 25)
        shirt_color = (16, 185, 129) if not self.skateboard else (245, 158, 11)
        shorts_color = (30, 58, 138)
        shoe_color = (239, 68, 68)
        headband_color = (255, 255, 255)

        if self.state == 'sliding':
            slide_y = char_y - 30
            pygame.draw.rect(surface, shirt_color, (cx - 20, slide_y - 12, 34, 24), border_radius=6)
            pygame.draw.circle(surface, skin_color, (cx + 12, slide_y - 16), 11)
            pygame.draw.circle(surface, hair_color, (cx + 12, slide_y - 20), 10)
            pygame.draw.line(surface, shorts_color, (cx - 15, slide_y + 8), (cx - 28, slide_y + 16), 6)
            pygame.draw.line(surface, skin_color, (cx - 28, slide_y + 16), (cx - 38, slide_y + 18), 5)
            pygame.draw.rect(surface, shoe_color, (cx - 44, slide_y + 14, 12, 7), border_radius=3)
            pygame.draw.circle(surface, (200, 205, 215), (cx - 36, slide_y + 18), 4)
            pygame.draw.circle(surface, (220, 225, 235), (cx - 44, slide_y + 16), 5)

        elif self.state == 'jumping':
            body_center_y = char_y - 50
            pygame.draw.line(surface, shorts_color, (cx - 8, body_center_y + 15), (cx - 14, body_center_y + 28), 6)
            pygame.draw.line(surface, shorts_color, (cx + 8, body_center_y + 15), (cx + 14, body_center_y + 28), 6)
            pygame.draw.line(surface, skin_color, (cx - 14, body_center_y + 28), (cx - 8, body_center_y + 36), 5)
            pygame.draw.line(surface, skin_color, (cx + 14, body_center_y + 28), (cx + 8, body_center_y + 36), 5)
            pygame.draw.rect(surface, shoe_color, (cx - 13, body_center_y + 34, 11, 7), border_radius=3)
            pygame.draw.rect(surface, shoe_color, (cx + 3, body_center_y + 34, 11, 7), border_radius=3)

            pygame.draw.rect(surface, shirt_color, (cx - 14, body_center_y - 12, 28, 28), border_radius=6)
            pygame.draw.line(surface, shirt_color, (cx - 12, body_center_y - 6), (cx - 20, body_center_y - 24), 5)
            pygame.draw.line(surface, shirt_color, (cx + 12, body_center_y - 6), (cx + 20, body_center_y - 24), 5)
            pygame.draw.circle(surface, skin_color, (cx - 21, body_center_y - 26), 4)
            pygame.draw.circle(surface, skin_color, (cx + 21, body_center_y - 26), 4)

            head_y = body_center_y - 26
            pygame.draw.circle(surface, skin_color, (cx, head_y), 13)
            pygame.draw.circle(surface, hair_color, (cx, head_y - 4), 13)
            pygame.draw.rect(surface, headband_color, (cx - 12, head_y - 6, 24, 4), border_radius=2)

        else:
            body_center_y = char_y - 50

            leg_l_angle = swing * 18.0
            leg_l_knee_x = int(cx - 7 + leg_l_angle * 0.4)
            leg_l_knee_y = int(body_center_y + 16 - abs(swing) * 3)
            leg_l_foot_x = int(cx - 8 + leg_l_angle * 0.9)
            leg_l_foot_y = int(char_y - 4 - max(0, -swing * 12))

            pygame.draw.line(surface, shorts_color, (cx - 7, body_center_y + 12), (leg_l_knee_x, leg_l_knee_y), 6)
            pygame.draw.line(surface, skin_color, (leg_l_knee_x, leg_l_knee_y), (leg_l_foot_x, leg_l_foot_y), 5)
            pygame.draw.rect(surface, shoe_color, (leg_l_foot_x - 5, leg_l_foot_y - 4, 11, 7), border_radius=3)

            leg_r_angle = -swing * 18.0
            leg_r_knee_x = int(cx + 7 + leg_r_angle * 0.4)
            leg_r_knee_y = int(body_center_y + 16 - abs(swing) * 3)
            leg_r_foot_x = int(cx + 8 + leg_r_angle * 0.9)
            leg_r_foot_y = int(char_y - 4 - max(0, swing * 12))

            pygame.draw.line(surface, shorts_color, (cx + 7, body_center_y + 12), (leg_r_knee_x, leg_r_knee_y), 6)
            pygame.draw.line(surface, skin_color, (leg_r_knee_x, leg_r_knee_y), (leg_r_foot_x, leg_r_foot_y), 5)
            pygame.draw.rect(surface, shoe_color, (leg_r_foot_x - 5, leg_r_foot_y - 4, 11, 7), border_radius=3)

            bob = abs(cos_swing) * 3.0
            torso_y = body_center_y - 12 + bob
            pygame.draw.rect(surface, shirt_color, (cx - 14, int(torso_y), 28, 27), border_radius=6)
            num_surf = pygame.font.SysFont('arial', 12, bold=True).render("7", True, (255, 255, 255))
            surface.blit(num_surf, (cx - 4, int(torso_y + 6)))

            arm_l_hand_x = int(cx - 18 - swing * 12)
            arm_l_hand_y = int(torso_y + 14 + swing * 8)
            pygame.draw.line(surface, shirt_color, (cx - 12, int(torso_y + 4)), (arm_l_hand_x, arm_l_hand_y), 5)
            pygame.draw.circle(surface, skin_color, (arm_l_hand_x, arm_l_hand_y), 4)

            arm_r_hand_x = int(cx + 18 + swing * 12)
            arm_r_hand_y = int(torso_y + 14 - swing * 8)
            pygame.draw.line(surface, shirt_color, (cx + 12, int(torso_y + 4)), (arm_r_hand_x, arm_r_hand_y), 5)
            pygame.draw.circle(surface, skin_color, (arm_r_hand_x, arm_r_hand_y), 4)

            head_y = int(torso_y - 14)
            pygame.draw.circle(surface, skin_color, (cx, head_y), 13)
            pygame.draw.circle(surface, hair_color, (cx, head_y - 5), 13)
            pygame.draw.rect(surface, headband_color, (cx - 12, head_y - 7, 24, 4), border_radius=2)
