from __future__ import annotations

import heapq
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pygame

from settings import *
from helpers import mix_color, tile_to_rect

class TileMap:
#1-стена 0-пол
    def __init__(self, matrix: Sequence[str]) -> None:
        if len(matrix) != MAP_HEIGHT_TILES:
            raise ValueError("Карта должна иметь фиксированную высоту")
        if any(len(row) != MAP_WIDTH_TILES for row in matrix):
            raise ValueError("Все строки карты должны иметь одинаковую ширину")
        self.matrix = list(matrix)
        self.wall_rects: List[pygame.Rect] = []
        for y, row in enumerate(matrix):
            for x, char in enumerate(row):
                if char == "1":
                    self.wall_rects.append(tile_to_rect((x, y)))

    def in_bounds(self, tile: Tile) -> bool:
        x, y = tile
        return 0 <= x < MAP_WIDTH_TILES and 0 <= y < MAP_HEIGHT_TILES

    def is_wall(self, tile: Tile) -> bool:
        x, y = tile
        if not self.in_bounds(tile):
            return True
        return self.matrix[y][x] == "1"

    def get_wall_rects_near(self, rect: pygame.Rect) -> List[pygame.Rect]:
        expanded = rect.inflate(TILE_SIZE * 2, TILE_SIZE * 2)
        return [wall for wall in self.wall_rects if expanded.colliderect(wall)]

    def draw(self, surface: pygame.Surface) -> None:
        for y in range(MAP_HEIGHT_TILES):
            for x in range(MAP_WIDTH_TILES):
                rect = tile_to_rect((x, y))
                if self.matrix[y][x] == "1":
                    shade = 0.18 if (x * 13 + y * 7) % 5 == 0 else 0.0
                    color = mix_color(COLOR_WALL, COLOR_WALL_EDGE, shade)
                    pygame.draw.rect(surface, color, rect)
                    pygame.draw.rect(surface, COLOR_WALL_EDGE, rect, 2)
                    if (x + y) % 4 == 0:
                        pygame.draw.line(surface, (48, 45, 62), (rect.left + 6, rect.top + 10), (rect.right - 8, rect.top + 19), 2)
                else:
                    color = COLOR_FLOOR_A if (x + y) % 2 == 0 else COLOR_FLOOR_B
                    pygame.draw.rect(surface, color, rect)
                    pygame.draw.rect(surface, COLOR_GRID, rect, 1)
                    if (x * 17 + y * 11) % 9 == 0:
                        pygame.draw.circle(surface, (42, 39, 53), (rect.left + 12, rect.top + 27), 2)

#A*
class AStarPathfinder:

    def __init__(self, level: "Level") -> None:
        self.level = level

    def heuristic(self, a: Tile, b: Tile) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def neighbors(self, tile: Tile) -> Iterable[Tile]:
        x, y = tile
        for candidate in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if self.level.tilemap.in_bounds(candidate) and not self.level.is_blocked_tile(candidate):
                yield candidate

    def find_path(self, start: Tile, goal: Tile) -> List[Tile]:
        if self.level.is_blocked_tile(goal):
            return []
        open_heap: List[Tuple[int, Tile]] = []
        heapq.heappush(open_heap, (0, start))
        came_from: Dict[Tile, Optional[Tile]] = {start: None}
        cost_so_far: Dict[Tile, int] = {start: 0}
        while open_heap:
            _, current = heapq.heappop(open_heap)
            if current == goal:
                break
            for next_tile in self.neighbors(current):
                new_cost = cost_so_far[current] + 1
                if next_tile not in cost_so_far or new_cost < cost_so_far[next_tile]:
                    cost_so_far[next_tile] = new_cost
                    priority = new_cost + self.heuristic(next_tile, goal)
                    heapq.heappush(open_heap, (priority, next_tile))
                    came_from[next_tile] = current
        if goal not in came_from:
            return []
        path: List[Tile] = []
        current: Optional[Tile] = goal
        while current is not None:
            path.append(current)
            current = came_from[current]
        path.reverse()
        return path
