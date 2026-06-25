from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Sequence

import pygame

from settings import Tile

class GameState(Enum):
    MAIN_MENU = auto()
    LEVEL_SELECT = auto()
    SETTINGS = auto()
    PLAYING = auto()
    LEVEL_COMPLETE = auto()
    FINAL_SCREEN = auto()


class EnemyMode(Enum):
    PATROL = auto()
    CHASE = auto()


@dataclass(frozen=True)
class InputState:

    move: pygame.Vector2
    shoot_pressed: bool
    restart_pressed: bool
    next_level_pressed: bool
    quit_pressed: bool

#ЗАПИСЬ ДВИЖЕНИЙ
@dataclass(frozen=True)
class ActorFrame:

    time: float
    x: float
    y: float
    dir_x: float
    dir_y: float
    shot: bool

    def position(self) -> pygame.Vector2:
        return pygame.Vector2(self.x, self.y)

    def direction(self) -> pygame.Vector2:
        vec = pygame.Vector2(self.dir_x, self.dir_y)
        if vec.length_squared() == 0:
            return pygame.Vector2(1, 0)
        return vec.normalize()


@dataclass(frozen=True)
class EnemyFrame:

    time: float
    x: float
    y: float
    dir_x: float
    dir_y: float
    alive: bool


@dataclass
class EnemyMemory:

    frames: List[EnemyFrame]
    death_time: float

#КОНФИГУРАЦИЯ УРОВНЯ
@dataclass(frozen=True)
class EnemyConfig:
    start_tile: Tile
    patrol_tiles: Tuple[Tile, ...]


@dataclass(frozen=True)
class ButtonConfig:
    tile: Tile
    link_id: str


@dataclass(frozen=True)
class DoorConfig:
    tile: Tile
    link_id: str


@dataclass(frozen=True)
class LevelData:
    name: str
    matrix: Sequence[str]
    player_start: Tile
    exit_tile: Tile
    buttons: Tuple[ButtonConfig, ...]
    doors: Tuple[DoorConfig, ...]
    enemies: Tuple[EnemyConfig, ...]
    coins: Tuple[Tile, ...]
    duration: float
    target_ghosts: int
    target_time: float
    hint: str

#СОБЫТИЯ
@dataclass
class ShotEvent:
    origin: pygame.Vector2
    direction: pygame.Vector2
    owner: str


@dataclass
class ShotVisual:
    rect: pygame.Rect
    start: pygame.Vector2
    end: pygame.Vector2
    timer: float

#СОХРАНЕНИЯ
@dataclass
class SettingsData:
    volume: float = 0.65
    scanlines: bool = True
    screen_shake: bool = True


@dataclass
class LevelRecord:
    best_time: Optional[float] = None
    best_ghosts: Optional[int] = None
    best_coins: int = 0
    best_stars: int = 0
