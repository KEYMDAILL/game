from __future__ import annotations

from typing import Iterable, List, Sequence

from settings import *
from models import ButtonConfig, DoorConfig, EnemyConfig, LevelData
#создает карту
def make_matrix(extra_walls: Iterable[Tile]) -> List[str]:
    walls = set(extra_walls)
    rows: List[str] = []
    for y in range(MAP_HEIGHT_TILES):
        row = []
        for x in range(MAP_WIDTH_TILES):
            border = x == 0 or y == 0 or x == MAP_WIDTH_TILES - 1 or y == MAP_HEIGHT_TILES - 1
            row.append("1" if border or (x, y) in walls else "0")
        rows.append("".join(row))
    return rows


def vertical_barrier(x: int, gap_y: int) -> set[Tile]:
    return {(x, y) for y in range(1, MAP_HEIGHT_TILES - 1) if y != gap_y}

#Делает важные клетки проходимыми
def carve_matrix_tiles(matrix: Sequence[str], tiles: Iterable[Tile]) -> List[str]:


    rows = [list(row) for row in matrix]
    for x, y in tiles:
        if 0 <= x < MAP_WIDTH_TILES and 0 <= y < MAP_HEIGHT_TILES:
            rows[y][x] = "0"
    return ["".join(row) for row in rows]

#Проверяет уровень и исправляет ошибки
def sanitize_level(level: LevelData) -> LevelData:
    critical_tiles: List[Tile] = [level.player_start, level.exit_tile]
    critical_tiles.extend(button.tile for button in level.buttons)
    critical_tiles.extend(door.tile for door in level.doors)
    critical_tiles.extend(level.coins)
    for enemy in level.enemies:
        critical_tiles.append(enemy.start_tile)
        critical_tiles.extend(enemy.patrol_tiles)
    return LevelData(
        name=level.name,
        matrix=carve_matrix_tiles(level.matrix, critical_tiles),
        player_start=level.player_start,
        exit_tile=level.exit_tile,
        buttons=level.buttons,
        doors=level.doors,
        enemies=level.enemies,
        coins=level.coins,
        duration=level.duration,
        target_ghosts=level.target_ghosts,
        target_time=level.target_time,
        hint=level.hint,
    )


def sanitize_levels(levels: Sequence[LevelData]) -> List[LevelData]:
    return [sanitize_level(level) for level in levels]


def make_levels() -> List[LevelData]:
    levels: List[LevelData] = []
#УРОВЕНЬ 1
    walls1 = set()
    walls1 |= vertical_barrier(8, 7)
    walls1 |= {(13, y) for y in range(2, 6)} | {(13, y) for y in range(10, 14)}
    levels.append(
        LevelData(
            name="УРОВЕНЬ 1",
            matrix=make_matrix(walls1),
            player_start=(2, 7),
            exit_tile=(21, 7),
            buttons=(ButtonConfig((3, 12), "A"),),
            doors=(DoorConfig((8, 7), "A"),),
            enemies=(EnemyConfig((16, 7), ((16, 4), (20, 4), (20, 10), (16, 10))),),
            coins=((5, 5), (12, 7), (19, 5)),
            duration=13.0,
            target_ghosts=1,
            target_time=10.5,
            hint="УРОВЕНЬ 1",
        )
    )
#УРОВЕНЬ 2
    walls2 = set()
    walls2 |= vertical_barrier(7, 6)
    walls2 |= vertical_barrier(15, 9)
    walls2 |= {(10, y) for y in range(8, 13)} | {(18, y) for y in range(2, 6)}
    levels.append(
        LevelData(
            name="УРОВЕНЬ 2",
            matrix=make_matrix(walls2),
            player_start=(2, 6),
            exit_tile=(21, 9),
            buttons=(ButtonConfig((3, 12), "A"), ButtonConfig((11, 3), "B")),
            doors=(DoorConfig((7, 6), "A"), DoorConfig((15, 9), "B")),
            enemies=(
                EnemyConfig((11, 9), ((9, 9), (13, 9))),
                EnemyConfig((19, 9), ((17, 9), (21, 9))),
            ),
            coins=((4, 3), (10, 12), (13, 4), (20, 12)),
            duration=15.0,
            target_ghosts=2,
            target_time=13.0,
            hint="УРОВЕНЬ 2",
        )
    )
#УРОВЕНЬ 3
    walls3 = set()
    walls3 |= vertical_barrier(6, 8)
    walls3 |= vertical_barrier(12, 5)
    walls3 |= vertical_barrier(18, 10)
    walls3 |= {(3, y) for y in range(2, 5)} | {(9, y) for y in range(10, 14)} | {(15, y) for y in range(2, 5)}
    levels.append(
        LevelData(
            name="УРОВЕНЬ 3",
            matrix=make_matrix(walls3),
            player_start=(2, 8),
            exit_tile=(22, 10),
            buttons=(ButtonConfig((3, 13), "A"), ButtonConfig((9, 2), "B"), ButtonConfig((15, 13), "C")),
            doors=(DoorConfig((6, 8), "A"), DoorConfig((12, 5), "B"), DoorConfig((18, 10), "C")),
            enemies=(
                EnemyConfig((9, 7), ((8, 7), (10, 7), (10, 11), (8, 11))),
                EnemyConfig((15, 5), ((14, 5), (16, 5), (16, 8), (14, 8))),
                EnemyConfig((21, 10), ((20, 8), (22, 8), (22, 12), (20, 12))),
            ),
            coins=((4, 4), (8, 13), (11, 8), (16, 3), (21, 13)),
            duration=18.0,
            target_ghosts=3,
            target_time=16.0,
            hint="УРОВЕНЬ 3",
        )
    )
#УРОВЕНЬ 4
    walls4 = set()
    walls4 |= vertical_barrier(5, 5)
    walls4 |= vertical_barrier(10, 11)
    walls4 |= vertical_barrier(15, 5)
    walls4 |= vertical_barrier(20, 11)
    walls4 |= {(7, y) for y in range(2, 5)} | {(13, y) for y in range(11, 14)} | {(17, y) for y in range(2, 5)}
    levels.append(
        LevelData(
            name="УРОВЕНЬ 4",
            matrix=make_matrix(walls4),
            player_start=(2, 5),
            exit_tile=(22, 11),
            buttons=(ButtonConfig((2, 13), "A"), ButtonConfig((7, 2), "B"), ButtonConfig((12, 13), "C"), ButtonConfig((17, 2), "D")),
            doors=(DoorConfig((5, 5), "A"), DoorConfig((10, 11), "B"), DoorConfig((15, 5), "C"), DoorConfig((20, 11), "D")),
            enemies=(
                EnemyConfig((8, 8), ((7, 8), (9, 8))),
                EnemyConfig((13, 5), ((12, 5), (14, 5))),
                EnemyConfig((18, 10), ((17, 10), (19, 10))),
                EnemyConfig((21, 11), ((21, 8), (22, 8), (22, 12))),
            ),
            coins=((3, 3), (8, 13), (12, 2), (16, 13), (19, 3), (22, 6)),
            duration=22.0,
            target_ghosts=4,
            target_time=20.0,
            hint="УРОВЕНЬ 4",
        )
    )
    return sanitize_levels(levels)
