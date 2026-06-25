from __future__ import annotations

import json
import os
from dataclasses import asdict
from typing import Dict

from settings import SAVE_FILE
from models import LevelData, LevelRecord, SettingsData
from helpers import calculate_saved_stars

class SaveManager:

    def __init__(self) -> None:
        self.settings = SettingsData()
        self.records: Dict[str, LevelRecord] = {}
        self.load()

    def load(self) -> None:
        if not os.path.exists(SAVE_FILE):
            return
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as file:
                raw = json.load(file)
            settings = raw.get("settings", {})
            self.settings = SettingsData(
                volume=float(settings.get("volume", self.settings.volume)),
                scanlines=bool(settings.get("scanlines", self.settings.scanlines)),
                screen_shake=bool(settings.get("screen_shake", self.settings.screen_shake)),
            )
            self.records.clear()
            for name, data in raw.get("records", {}).items():
                self.records[name] = LevelRecord(
                    best_time=data.get("best_time"),
                    best_ghosts=data.get("best_ghosts"),
                    best_coins=int(data.get("best_coins", 0)),
                    best_stars=int(data.get("best_stars", 0)),
                )
        except (OSError, ValueError, TypeError):
            # Повреждённое сохранение не должно ломать игру.
            self.settings = SettingsData()
            self.records = {}

    def save(self) -> None:
        raw = {
            "settings": asdict(self.settings),
            "records": {name: asdict(record) for name, record in self.records.items()},
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as file:
            json.dump(raw, file, ensure_ascii=False, indent=2)

    def get_record(self, level_name: str) -> LevelRecord:
        return self.records.setdefault(level_name, LevelRecord())

    def update_record(self, level: LevelData, time_value: float, ghosts_used: int, coins: int, stars: int) -> bool:
        record = self.get_record(level.name)
        improved = False
        if record.best_time is None or time_value < record.best_time:
            record.best_time = time_value
            improved = True
        if record.best_ghosts is None or ghosts_used < record.best_ghosts:
            record.best_ghosts = ghosts_used
            improved = True
        if coins > record.best_coins:
            record.best_coins = coins
            improved = True
        # best_stars — не просто результат последнего прохождения.
        # Он пересчитывается по лучшим сохранённым метрикам: время, монеты, эхо.
        aggregate_stars = max(stars, calculate_saved_stars(level, record))
        if aggregate_stars > record.best_stars:
            record.best_stars = aggregate_stars
            improved = True
        self.save()
        return improved

    def reset_records(self) -> None:
        self.records = {}
        self.save()
