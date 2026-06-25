from __future__ import annotations

import math
import random
from typing import Sequence

import pygame

from settings import *
from models import ButtonConfig, DoorConfig
from helpers import draw_glow, tile_to_rect
from entities import Actor

class Button:
    def __init__(self, config: ButtonConfig) -> None:
        self.tile = config.tile
        self.link_id = config.link_id
        self.rect = tile_to_rect(config.tile).inflate(-10, -10)
        self.pressed = False

    def update(self, actors: Sequence[Actor]) -> None:
        self.pressed = any(self.rect.colliderect(actor.rect) for actor in actors)

    def draw(self, surface: pygame.Surface) -> None:
        color = COLOR_BUTTON_PRESSED if self.pressed else COLOR_BUTTON_IDLE
        if self.pressed:
            draw_glow(surface, self.rect.center, 36, COLOR_BUTTON_PRESSED, 50)
        pygame.draw.rect(surface, (38, 28, 34), self.rect.inflate(8, 8), border_radius=9)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, (255, 185, 155), self.rect, 2, border_radius=8)
        cx, cy = self.rect.center
        pygame.draw.circle(surface, (255, 210, 178), (cx, cy), 6 if self.pressed else 4)


class Door:
    def __init__(self, config: DoorConfig) -> None:
        self.tile = config.tile
        self.link_id = config.link_id
        self.rect = tile_to_rect(config.tile)
        self.open = False

    def draw(self, surface: pygame.Surface) -> None:
        if self.open:
            pygame.draw.rect(surface, COLOR_DOOR_OPEN, self.rect.inflate(-6, -6), border_radius=8)
            pygame.draw.rect(surface, (150, 242, 185), self.rect.inflate(-6, -6), 2, border_radius=8)
            return
        pygame.draw.rect(surface, COLOR_DOOR_CLOSED, self.rect, border_radius=3)
        pygame.draw.rect(surface, (255, 180, 100), self.rect, 2)

        cx, cy = self.rect.center
        pygame.draw.circle(surface, (255, 193, 113), (cx, cy), 9, 2)
        pygame.draw.line(surface, (255, 193, 113), (cx - 8, cy), (cx + 8, cy), 2)
        pygame.draw.line(surface, (255, 193, 113), (cx, cy - 8), (cx, cy + 8), 2)


class Coin:
    def __init__(self, tile: Tile) -> None:
        self.tile = tile
        self.rect = tile_to_rect(tile).inflate(-18, -18)
        self.collected = False
        self.phase = random.random() * math.tau

    def update(self, dt: float, actors: Sequence[Actor]) -> bool:
        if not self.collected and any(self.rect.colliderect(actor.rect) for actor in actors):
            self.collected = True
            return True
        self.phase += dt * 4.0
        return False

    def draw(self, surface: pygame.Surface) -> None:
        if self.collected:
            return
        bob = int(math.sin(self.phase) * 3)
        rect = self.rect.move(0, bob)
        draw_glow(surface, rect.center, 24, COLOR_GOLD, 36)
        pygame.draw.ellipse(surface, COLOR_COIN, rect)
        pygame.draw.ellipse(surface, (255, 246, 170), rect, 2)
        pygame.draw.line(surface, (160, 104, 38), rect.center, (rect.centerx, rect.bottom - 3), 2)
