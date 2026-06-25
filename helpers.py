from __future__ import annotations

import math
from typing import List, Optional, Tuple

import pygame

from settings import *
from models import LevelData, LevelRecord

def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def tile_to_rect(tile: Tile) -> pygame.Rect:
    return pygame.Rect(tile[0] * TILE_SIZE, tile[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)


def tile_center(tile: Tile) -> pygame.Vector2:
    return pygame.Vector2(tile[0] * TILE_SIZE + TILE_SIZE / 2, tile[1] * TILE_SIZE + TILE_SIZE / 2)


def world_to_tile(pos: pygame.Vector2 | Tuple[float, float]) -> Tile:
    x, y = pos
    return int(x // TILE_SIZE), int(y // TILE_SIZE)


def cardinal_direction(vec: pygame.Vector2) -> pygame.Vector2:

    if vec.length_squared() == 0:
        return pygame.Vector2(1, 0)
    if abs(vec.x) >= abs(vec.y):
        return pygame.Vector2(1 if vec.x >= 0 else -1, 0)
    return pygame.Vector2(0, 1 if vec.y >= 0 else -1)


def mix_color(a: Color, b: Color, t: float) -> Color:
    t = clamp(t, 0.0, 1.0)
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )


def make_font(size: int, bold: bool = False) -> pygame.font.Font:

    return pygame.font.SysFont("arial", size, bold=bold)


def draw_text(surface: pygame.Surface, font: pygame.font.Font, text: str, pos: Tuple[int, int], color: Color = COLOR_TEXT) -> None:
    surface.blit(font.render(text, True, color), pos)


def draw_centered(surface: pygame.Surface, font: pygame.font.Font, text: str, center: Tuple[int, int], color: Color = COLOR_TEXT) -> None:
    image = font.render(text, True, color)
    rect = image.get_rect(center=center)
    surface.blit(image, rect)


def format_time(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"{value:.2f} c"


def star_text(count: int) -> str:
    return "★" * count + "☆" * (3 - count)


def star_points(center: Tuple[int, int], outer_radius: int, inner_radius: int) -> List[Tuple[int, int]]:

    cx, cy = center
    points: List[Tuple[int, int]] = []

    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        radius = outer_radius if i % 2 == 0 else inner_radius
        points.append((round(cx + math.cos(angle) * radius), round(cy + math.sin(angle) * radius)))
    return points


def draw_star_icons(surface: pygame.Surface, center: Tuple[int, int], count: int, size: int = 18) -> None:

    count = max(0, min(3, count))
    spacing = size * 2 + 8
    start_x = center[0] - spacing
    for i in range(3):
        star_center = (start_x + i * spacing, center[1])
        fill = COLOR_GOLD if i < count else (54, 51, 67)
        outline = (255, 238, 150) if i < count else (108, 102, 128)
        pygame.draw.polygon(surface, fill, star_points(star_center, size, max(4, size // 2)))
        pygame.draw.polygon(surface, outline, star_points(star_center, size, max(4, size // 2)), 2)


def calculate_saved_stars(level: "LevelData", record: "LevelRecord") -> int:


    stars = 0
    if record.best_time is not None and record.best_time <= level.target_time:
        stars += 1
    if len(level.coins) == 0 or record.best_coins >= len(level.coins):
        stars += 1
    if record.best_ghosts is not None and record.best_ghosts <= level.target_ghosts:
        stars += 1
    return stars


def draw_glow(surface: pygame.Surface, center: Tuple[int, int], radius: int, color: Color, alpha: int) -> None:
    glow = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    for r in range(radius, 0, -4):
        a = int(alpha * (r / radius) ** 2)
        pygame.draw.circle(glow, (*color, a), (radius, radius), r)
    surface.blit(glow, (center[0] - radius, center[1] - radius), special_flags=pygame.BLEND_PREMULTIPLIED)
