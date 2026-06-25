from __future__ import annotations

from typing import List, Optional, Sequence

import pygame

from settings import *
from models import ActorFrame, EnemyConfig, EnemyFrame, EnemyMemory, EnemyMode, InputState, ShotEvent
from helpers import cardinal_direction, draw_glow, mix_color, tile_center, world_to_tile
#движущиеся объекты
class Actor:
    def __init__(self, center: pygame.Vector2, size: int) -> None:
        self.pos = pygame.Vector2(center)
        self.size = size
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = (round(self.pos.x), round(self.pos.y))
        self.facing = pygame.Vector2(1, 0)

    def sync_rect(self) -> None:
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    def center_tile(self) -> Tile:
        return world_to_tile(self.pos)

    def move_with_collisions(self, delta: pygame.Vector2, solid_rects_getter) -> None:
# X
        self.pos.x += delta.x
        self.sync_rect()
        for solid in solid_rects_getter(self.rect):
            if self.rect.colliderect(solid):
                if delta.x > 0:
                    self.rect.right = solid.left
                elif delta.x < 0:
                    self.rect.left = solid.right
                self.pos.x = self.rect.centerx
# Y
        self.pos.y += delta.y
        self.sync_rect()
        for solid in solid_rects_getter(self.rect):
            if self.rect.colliderect(solid):
                if delta.y > 0:
                    self.rect.bottom = solid.top
                elif delta.y < 0:
                    self.rect.top = solid.bottom
                self.pos.y = self.rect.centery
        self.sync_rect()


class Player(Actor):

    def __init__(self, center: pygame.Vector2) -> None:
        super().__init__(center, PLAYER_SIZE)
        self.shells = 1
        self.shot_cooldown = 0.0
        self.flash_timer = 0.0
        self.fired_this_frame = False

    def update(self, dt: float, input_state: InputState, level: "Level") -> Optional[ShotEvent]:
        self.fired_this_frame = False
        move = pygame.Vector2(input_state.move)
        if move.length_squared() > 0:
            move = move.normalize()
            self.facing = pygame.Vector2(move)
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        self.flash_timer = max(0.0, self.flash_timer - dt)

        shot_event: Optional[ShotEvent] = None
        if input_state.shoot_pressed and self.shells > 0 and self.shot_cooldown <= 0.0:
            self.shells = 0
            self.shot_cooldown = SHOTGUN_COOLDOWN
            self.flash_timer = SHOTGUN_FLASH_TIME
            self.fired_this_frame = True
            shot_event = ShotEvent(pygame.Vector2(self.pos), cardinal_direction(self.facing), "player")

        self.move_with_collisions(move * PLAYER_SPEED * dt, level.get_solid_rects_near)
        return shot_event

    def snapshot(self, time_value: float) -> ActorFrame:
        return ActorFrame(time_value, self.pos.x, self.pos.y, self.facing.x, self.facing.y, self.fired_this_frame)

    def draw(self, surface: pygame.Surface) -> None:
        direction = cardinal_direction(self.facing)
        draw_glow(surface, self.rect.center, 18, COLOR_PLAYER, 18)
        shadow = pygame.Surface((self.rect.w + 18, self.rect.h + 12), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), shadow.get_rect().inflate(-5, -6).move(0, 5))
        surface.blit(shadow, (self.rect.x - 9, self.rect.y - 2))

        pygame.draw.rect(surface, COLOR_PLAYER_DARK, self.rect.move(3, 3), border_radius=7)
        pygame.draw.rect(surface, COLOR_PLAYER, self.rect, border_radius=7)
        pygame.draw.rect(surface, (255, 246, 170), self.rect, 2, border_radius=7)
        head = self.rect.inflate(-10, -15)
        head.centery -= 7
        pygame.draw.rect(surface, (255, 238, 154), head, border_radius=4)

        draw_shotgun(surface, self.rect, direction, self.flash_timer > 0.0, COLOR_PLAYER_DARK)

#запись игрока
class Ghost(Actor):


    def __init__(self, frames: Sequence[ActorFrame], index: int) -> None:
        first = frames[0]
        super().__init__(pygame.Vector2(first.x, first.y), GHOST_SIZE)
        self.frames = list(frames)
        self.index = index
        self.frame_cursor = 0
        self.flash_timer = 0.0
        self.finished = False
        self.reset()

    def reset(self) -> None:


        self.frame_cursor = 0
        self.flash_timer = 0.0
        self.finished = False
        first = self.frames[0]
        self.pos = first.position()
        self.facing = first.direction()
        self.sync_rect()

    def update(self, dt: float, elapsed: float) -> List[ShotEvent]:
        self.flash_timer = max(0.0, self.flash_timer - dt)
        events: List[ShotEvent] = []
        while self.frame_cursor + 1 < len(self.frames) and self.frames[self.frame_cursor + 1].time <= elapsed:
            self.frame_cursor += 1
            frame = self.frames[self.frame_cursor]
            if frame.shot:
                self.flash_timer = SHOTGUN_FLASH_TIME
                events.append(ShotEvent(frame.position(), cardinal_direction(frame.direction()), f"ghost_{self.index}"))
        frame = self.frames[min(self.frame_cursor, len(self.frames) - 1)]
        self.pos = frame.position()
        self.facing = frame.direction()
        self.sync_rect()
        self.finished = self.frame_cursor >= len(self.frames) - 1 and elapsed > self.frames[-1].time
        return events

    def draw(self, surface: pygame.Surface) -> None:
        direction = cardinal_direction(self.facing)
        alpha_surface = pygame.Surface((self.rect.w + 34, self.rect.h + 34), pygame.SRCALPHA)
        local_rect = pygame.Rect(17, 17, self.rect.w, self.rect.h)
        pygame.draw.rect(alpha_surface, (*COLOR_GHOST_DARK, 112), local_rect.move(3, 3), border_radius=7)
        pygame.draw.rect(alpha_surface, (*COLOR_GHOST, 145), local_rect, border_radius=7)
        pygame.draw.rect(alpha_surface, (180, 230, 255, 160), local_rect, 2, border_radius=7)
        for y in range(local_rect.top + 4, local_rect.bottom, 7):
            pygame.draw.line(alpha_surface, (185, 230, 255, 70), (local_rect.left + 2, y), (local_rect.right - 2, y), 1)
        draw_shotgun(alpha_surface, local_rect, direction, self.flash_timer > 0.0, COLOR_GHOST)
        surface.blit(alpha_surface, (self.rect.x - 17, self.rect.y - 17))


class Enemy(Actor):

    def __init__(self, index: int, config: EnemyConfig) -> None:
        super().__init__(tile_center(config.start_tile), ENEMY_SIZE)
        self.index = index
        self.config = config
        self.patrol_tiles = list(config.patrol_tiles) or [config.start_tile]
        self.patrol_index = 0
        self.mode = EnemyMode.PATROL
        self.alive = True
        self.path: List[Tile] = []
        self.repath_timer = 0.0
        self.alert_timer = 0.0

    def update(self, dt: float, level: "Level", targets: Sequence[Actor]) -> None:
        if not self.alive:
            return
        self.alert_timer = max(0.0, self.alert_timer - dt)
        self.repath_timer = max(0.0, self.repath_timer - dt)

        visible = self.choose_visible_target(level, targets)
        if visible is not None:
            self.mode = EnemyMode.CHASE
            self.alert_timer = 0.25
            goal_tile = visible.center_tile()
            speed = ENEMY_CHASE_SPEED
        else:
            self.mode = EnemyMode.PATROL
            goal_tile = self.patrol_tiles[self.patrol_index]
            speed = ENEMY_SPEED

        if self.repath_timer <= 0.0 or not self.path:
            self.path = level.pathfinder.find_path(self.center_tile(), goal_tile)
            self.repath_timer = ENEMY_REPATH_TIME
        self.follow_path(dt, level, speed)

        if self.mode == EnemyMode.PATROL:
            target_center = tile_center(self.patrol_tiles[self.patrol_index])
            if self.pos.distance_to(target_center) < 7:
                self.patrol_index = (self.patrol_index + 1) % len(self.patrol_tiles)
                self.path.clear()

    def choose_visible_target(self, level: "Level", targets: Sequence[Actor]) -> Optional[Actor]:
        best: Optional[Actor] = None
        best_distance = float("inf")
        for target in targets:
            distance = self.pos.distance_to(target.pos)
            if distance > ENEMY_VISION_RANGE:
                continue
            if distance < best_distance and level.has_line_of_sight(self.pos, target.pos):
                best = target
                best_distance = distance
        return best

    def follow_path(self, dt: float, level: "Level", speed: float) -> None:
        if len(self.path) < 2:
            return
        next_tile = self.path[1]
        target = tile_center(next_tile)
        direction = target - self.pos
        distance = direction.length()
        if distance < 3:
            self.path.pop(0)
            return
        direction = direction.normalize()
        self.facing = pygame.Vector2(direction)
        delta = direction * speed * dt
        if delta.length() > distance:
            delta.scale_to_length(distance)
        self.move_with_collisions(delta, level.get_solid_rects_near)

    def kill(self) -> None:
        self.alive = False

    def make_frame(self, time_value: float) -> EnemyFrame:
        return EnemyFrame(time_value, self.pos.x, self.pos.y, self.facing.x, self.facing.y, self.alive)

    def draw(self, surface: pygame.Surface) -> None:
        draw_guard(surface, self.rect, self.facing, self.alive, self.mode == EnemyMode.CHASE)

#запись врага
class ReplayGuard(Actor):

    def __init__(self, index: int, memory: EnemyMemory) -> None:
        first = memory.frames[0]
        super().__init__(pygame.Vector2(first.x, first.y), ENEMY_SIZE)
        self.index = index
        self.memory = memory
        self.cursor = 0
        self.alive = True

    def update(self, elapsed: float) -> None:
        while self.cursor + 1 < len(self.memory.frames) and self.memory.frames[self.cursor + 1].time <= elapsed:
            self.cursor += 1
        frame = self.memory.frames[min(self.cursor, len(self.memory.frames) - 1)]
        self.pos = pygame.Vector2(frame.x, frame.y)
        self.facing = pygame.Vector2(frame.dir_x, frame.dir_y)
        if self.facing.length_squared() == 0:
            self.facing = pygame.Vector2(1, 0)
        self.sync_rect()
        self.alive = frame.alive and elapsed < self.memory.death_time

    def draw(self, surface: pygame.Surface) -> None:
        draw_guard(surface, self.rect, self.facing, self.alive, False, replay=True)



def draw_shotgun(surface: pygame.Surface, actor_rect: pygame.Rect, direction: pygame.Vector2, flash: bool, base_color: Color) -> None:
    direction = cardinal_direction(direction)
    perp = pygame.Vector2(-direction.y, direction.x)
    center = pygame.Vector2(actor_rect.center)
    grip = center - direction * 2 + perp * 4
    barrel_start = center + direction * 6
    barrel_end = center + direction * 27

    stock_start = center - direction * 12 - perp * 5
    stock_end = center - direction * 2 + perp * 2
    pygame.draw.line(surface, (82, 51, 33), stock_start, stock_end, 6)
    pygame.draw.line(surface, (99, 61, 38), grip, grip + perp * 7 - direction * 3, 5)
    pygame.draw.line(surface, (44, 43, 48), barrel_start + perp * 2, barrel_end + perp * 2, 5)
    pygame.draw.line(surface, (32, 32, 36), barrel_start - perp * 3, barrel_end - perp * 3, 5)
    pygame.draw.line(surface, (190, 188, 170), barrel_start + perp * 2, barrel_end + perp * 2, 2)
    pygame.draw.circle(surface, (18, 18, 21), barrel_end + perp * 2, 3)
    pygame.draw.circle(surface, (18, 18, 21), barrel_end - perp * 3, 3)

    if flash:
        tip = barrel_end + direction * 7
        points = [
            tip + direction * 13,
            tip + perp * 8,
            tip - direction * 5,
            tip - perp * 8,
        ]
        pygame.draw.polygon(surface, (255, 237, 126), points)
        pygame.draw.polygon(surface, (255, 155, 86), points, 2)


def draw_guard(surface: pygame.Surface, rect: pygame.Rect, facing: pygame.Vector2, alive: bool, alert: bool, replay: bool = False) -> None:
    if not alive:
        dead_rect = rect.inflate(8, -8)
        pygame.draw.ellipse(surface, (0, 0, 0, 90), dead_rect.move(3, 7))
        pygame.draw.rect(surface, COLOR_CORPSE, dead_rect, border_radius=7)
        pygame.draw.line(surface, (160, 55, 64), dead_rect.topleft, dead_rect.bottomright, 2)
        pygame.draw.line(surface, (160, 55, 64), dead_rect.bottomleft, dead_rect.topright, 2)
        return

    color = COLOR_ENEMY if not replay else mix_color(COLOR_ENEMY, COLOR_GHOST, 0.45)
    if alert:
        color = (255, 128, 92)
    pygame.draw.ellipse(surface, (0, 0, 0, 92), rect.move(3, 6))
    pygame.draw.rect(surface, COLOR_ENEMY_DARK, rect.move(3, 3), border_radius=7)
    pygame.draw.rect(surface, color, rect, border_radius=7)
    pygame.draw.rect(surface, (255, 180, 160), rect, 2, border_radius=7)
    helmet = rect.inflate(-8, -14)
    helmet.centery -= 6
    pygame.draw.rect(surface, (82, 35, 44), helmet, border_radius=4)
    pygame.draw.line(surface, (252, 193, 165), helmet.midleft, helmet.midright, 2)
    d = cardinal_direction(facing)
    start = pygame.Vector2(rect.center) + d * 5
    end = pygame.Vector2(rect.center) + d * 27
    pygame.draw.line(surface, (70, 39, 31), start - d * 8, end, 4)
    pygame.draw.line(surface, (215, 212, 190), start, end, 2)
    pygame.draw.circle(surface, (245, 218, 170), end, 3)
    if alert:
        top = (rect.centerx, rect.top - 9)
        pygame.draw.polygon(surface, COLOR_WARN, [(top[0], top[1] - 6), (top[0] + 6, top[1]), (top[0], top[1] + 6), (top[0] - 6, top[1])])
