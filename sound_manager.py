from __future__ import annotations

import os
from typing import Dict

import pygame

from settings import *
from models import SettingsData
from helpers import clamp

class SoundManager:


    def __init__(self, settings: SettingsData) -> None:
        self.enabled = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        self.settings = settings
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=SOUND_SAMPLE_RATE, size=-16, channels=1)
            self.enabled = True
            self.load_sounds()
            self.apply_volume()
        except pygame.error:
            self.enabled = False

    def load_sounds(self) -> None:
        for filename in os.listdir(SFX_DIR):
            if filename.endswith(".wav"):
                name = filename[:-4]
                self.sounds[name] = pygame.mixer.Sound(os.path.join(SFX_DIR, filename))

    def apply_volume(self) -> None:
        if not self.enabled:
            return
        for sound in self.sounds.values():
            sound.set_volume(clamp(self.settings.volume, 0.0, 1.0))

    def play(self, name: str) -> None:
        if self.enabled and name in self.sounds and self.settings.volume > 0:
            self.sounds[name].play()
