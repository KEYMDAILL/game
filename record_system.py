from __future__ import annotations

from typing import List

from models import ActorFrame
from entities import Player
from settings import RECORD_INTERVAL

class RecordSystem:

    def __init__(self) -> None:
        self.frames: List[ActorFrame] = []
        self.last_sample_time = -999.0

    def clear(self) -> None:
        self.frames.clear()
        self.last_sample_time = -999.0

    def update(self, elapsed: float, player: Player) -> None:

        if player.fired_this_frame or elapsed - self.last_sample_time >= RECORD_INTERVAL:
            self.frames.append(player.snapshot(elapsed))
            self.last_sample_time = elapsed

    def export(self) -> List[ActorFrame]:
        return list(self.frames)
