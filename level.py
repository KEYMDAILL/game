from __future__ import annotations

import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

import pygame

from settings import *
from models import EnemyFrame, EnemyMemory, LevelData, ShotEvent, ShotVisual
from helpers import cardinal_direction, clamp, draw_glow, tile_center, tile_to_rect, world_to_tile
from map_tools import AStarPathfinder, TileMap
from entities import Actor, Enemy, Ghost, Player, ReplayGuard
from objects import Button, Coin, Door

class Level:
    def __init__(self, data: LevelData) -> None:
        self.data = data
        self.tilemap = TileMap(data.matrix)
        self.buttons = [Button(c) for c in data.buttons]
        self.doors = [Door(c) for c in data.doors]
        self.coins = [Coin(tile) for tile in data.coins]
        self.exit_rect = tile_to_rect(data.exit_tile).inflate(-10, -10)
        self.pathfinder = AStarPathfinder(self)
        self.enemy_memories: List[Optional[EnemyMemory]] = [None for _ in data.enemies]
        self.enemies: List[Enemy] = []
        self.replay_guards: List[ReplayGuard] = []
        self.enemy_recordings: Dict[int, List[EnemyFrame]] = {}
        self.dead_enemy_indices: set[int] = set()
        self.shot_visuals: List[ShotVisual] = []
        self.start_run()

    def hard_reset_level(self) -> None:

        self.enemy_memories = [None for _ in self.data.enemies]
        self.start_run()

    def start_run(self) -> None:
        for button in self.buttons:
            button.pressed = False
        for door in self.doors:
            door.open = False
        for coin in self.coins:
            coin.collected = False
            coin.phase = random.random() * math.tau
        self.enemies = []
        self.replay_guards = []
        self.enemy_recordings = {}
        self.dead_enemy_indices = set()
        self.shot_visuals = []
        for index, config in enumerate(self.data.enemies):
            memory = self.enemy_memories[index]
            if memory is None:
                enemy = Enemy(index, config)
                self.enemies.append(enemy)
                self.enemy_recordings[index] = []
            else:
                self.replay_guards.append(ReplayGuard(index, memory))

    def is_blocked_tile(self, tile: Tile) -> bool:
        if self.tilemap.is_wall(tile):
            return True
        for door in self.doors:
            if not door.open and door.tile == tile:
                return True
        return False

    def get_solid_rects_near(self, rect: pygame.Rect) -> List[pygame.Rect]:
        solids = self.tilemap.get_wall_rects_near(rect)
        expanded = rect.inflate(TILE_SIZE * 2, TILE_SIZE * 2)
        for door in self.doors:
            if not door.open and expanded.colliderect(door.rect):
                solids.append(door.rect)
        return solids

    def has_line_of_sight(self, start: pygame.Vector2, end: pygame.Vector2) -> bool:
        delta = end - start
        distance = delta.length()
        if distance <= 1:
            return True
        direction = delta.normalize()
        step = TILE_SIZE / 3
        for i in range(1, int(distance / step) + 1):
            point = start + direction * (i * step)
            if self.is_blocked_tile(world_to_tile(point)):
                return False
        return True

    def update(self, dt: float, elapsed: float, player: Player, ghosts: Sequence[Ghost]) -> Tuple[int, bool]:

        for replay in self.replay_guards:
            replay.update(elapsed)

        actors_for_buttons: List[Actor] = [player, *ghosts]
        for button in self.buttons:
            button.update(actors_for_buttons)
        old_states = [door.open for door in self.doors]
        for door in self.doors:
            door.open = any(button.link_id == door.link_id and button.pressed for button in self.buttons)
        door_changed = any(old != door.open for old, door in zip(old_states, self.doors))

        targets: List[Actor] = [player, *ghosts]
        for enemy in self.enemies:
            enemy.update(dt, self, targets)
        self.record_enemies(elapsed)

        collected = 0

        for coin in self.coins:
            if coin.update(dt, actors_for_buttons):
                collected += 1

        for visual in self.shot_visuals:
            visual.timer -= dt
        self.shot_visuals = [v for v in self.shot_visuals if v.timer > 0]
        return collected, door_changed

    def record_enemies(self, elapsed: float) -> None:
        for enemy in self.enemies:
            recording = self.enemy_recordings.get(enemy.index)
            if recording is None:
                continue

            if not enemy.alive and enemy.index in self.dead_enemy_indices:
                if not recording or recording[-1].alive:
                    recording.append(enemy.make_frame(elapsed))
                continue
            recording.append(enemy.make_frame(elapsed))

    def apply_shot(self, event: ShotEvent, elapsed: float) -> List[pygame.Vector2]:
        shot_rect, start, end = self.build_shot_rect(event.origin, event.direction)
        if shot_rect.width <= 0 or shot_rect.height <= 0:
            return []
        self.shot_visuals.append(ShotVisual(shot_rect, start, end, SHOTGUN_FLASH_TIME))
        hit_positions: List[pygame.Vector2] = []
        for enemy in self.enemies:
            if enemy.alive and enemy.rect.colliderect(shot_rect):
                enemy.kill()
                self.dead_enemy_indices.add(enemy.index)

                self.enemy_recordings.setdefault(enemy.index, []).append(enemy.make_frame(elapsed))
                hit_positions.append(pygame.Vector2(enemy.rect.center))
        return hit_positions

    def build_shot_rect(self, origin: pygame.Vector2, direction: pygame.Vector2) -> Tuple[pygame.Rect, pygame.Vector2, pygame.Vector2]:
        direction = cardinal_direction(direction)
        origin_tile = world_to_tile(origin)
        allowed_tiles = 0
        for step in range(1, SHOTGUN_RANGE_TILES + 1):
            tile = (origin_tile[0] + int(direction.x) * step, origin_tile[1] + int(direction.y) * step)
            if self.is_blocked_tile(tile):
                break
            allowed_tiles += 1
        length = allowed_tiles * TILE_SIZE
        start = pygame.Vector2(origin)
        end = start + direction * length
        if length <= 0:
            return pygame.Rect(0, 0, 0, 0), start, start
        if direction.x > 0:
            rect = pygame.Rect(int(start.x), int(start.y - SHOTGUN_WIDTH / 2), length, SHOTGUN_WIDTH)
        elif direction.x < 0:
            rect = pygame.Rect(int(start.x - length), int(start.y - SHOTGUN_WIDTH / 2), length, SHOTGUN_WIDTH)
        elif direction.y > 0:
            rect = pygame.Rect(int(start.x - SHOTGUN_WIDTH / 2), int(start.y), SHOTGUN_WIDTH, length)
        else:
            rect = pygame.Rect(int(start.x - SHOTGUN_WIDTH / 2), int(start.y - length), SHOTGUN_WIDTH, length)
        return rect, start, end

    def finalize_run_enemy_memories(self) -> None:
        for index in self.dead_enemy_indices:
            frames = self.enemy_recordings.get(index, [])
            if not frames:
                continue

            death_frame = next((frame for frame in frames if not frame.alive), frames[-1])
            death_time = death_frame.time
            trimmed_frames = [frame for frame in frames if frame.time <= death_time]
            if not trimmed_frames or trimmed_frames[-1].alive:
                trimmed_frames.append(death_frame)
            previous = self.enemy_memories[index]

            if previous is None or death_time < previous.death_time:
                self.enemy_memories[index] = EnemyMemory(frames=list(trimmed_frames), death_time=death_time)

    def player_touched_guard(self, player: Player) -> bool:
        for enemy in self.enemies:
            if enemy.alive and enemy.rect.colliderect(player.rect):
                return True
        for replay in self.replay_guards:
            if replay.alive and replay.rect.colliderect(player.rect):
                return True
        return False

    def all_targets_down(self) -> bool:
        live_normal = any(enemy.alive for enemy in self.enemies)
        live_replay = any(replay.alive for replay in self.replay_guards)
        return not live_normal and not live_replay

    def coins_collected_count(self) -> int:
        return sum(1 for coin in self.coins if coin.collected)

    def draw(self, surface: pygame.Surface) -> None:
        self.tilemap.draw(surface)
        exit_ready = self.all_targets_down()
        outer = (23, 64, 48) if exit_ready else (58, 43, 36)
        inner = COLOR_EXIT_READY if exit_ready else COLOR_EXIT_LOCKED
        border = (182, 255, 204) if exit_ready else (210, 137, 98)
        if exit_ready:
            draw_glow(surface, self.exit_rect.center, 48, COLOR_EXIT_READY, 44)
        pygame.draw.rect(surface, outer, self.exit_rect.inflate(12, 12), border_radius=10)
        pygame.draw.rect(surface, inner, self.exit_rect, border_radius=8)
        pygame.draw.rect(surface, border, self.exit_rect, 2, border_radius=8)
        cx, cy = self.exit_rect.center
        pygame.draw.polygon(surface, border, [(cx, cy - 12), (cx + 12, cy), (cx, cy + 12), (cx - 12, cy)], 2)

        for coin in self.coins:
            coin.draw(surface)
        for button in self.buttons:
            button.draw(surface)
        for door in self.doors:
            door.draw(surface)
        for replay in self.replay_guards:
            replay.draw(surface)
        for enemy in self.enemies:
            enemy.draw(surface)
        for visual in self.shot_visuals:
            alpha = int(190 * clamp(visual.timer / SHOTGUN_FLASH_TIME, 0.0, 1.0))
            layer = pygame.Surface((WORLD_WIDTH, WORLD_HEIGHT), pygame.SRCALPHA)
            pygame.draw.rect(layer, (*COLOR_SHOT, alpha // 3), visual.rect, border_radius=6)
            pygame.draw.line(layer, (*COLOR_SHOT, alpha), visual.start, visual.end, 4)
            pygame.draw.line(layer, (255, 255, 224, alpha), visual.start, visual.end, 2)
            surface.blit(layer, (0, 0))
