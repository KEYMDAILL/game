from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Tuple

import pygame

from settings import *
from helpers import clamp

@dataclass
class Particle:
    pos: pygame.Vector2
    vel: pygame.Vector2
    lifetime: float
    max_lifetime: float
    color: Color
    size: float


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: List[Particle] = []

    def clear(self) -> None:
        self.particles.clear()
#взрыв частиц
    def spawn_burst(self, center: Tuple[float, float], color: Color, count: int, speed: float, lifetime: float) -> None:
        if len(self.particles) > MAX_PARTICLES:
            self.particles = self.particles[-MAX_PARTICLES // 2 :]
        for _ in range(count):
            angle = random.uniform(0.0, math.tau)
            velocity = pygame.Vector2(math.cos(angle), math.sin(angle)) * random.uniform(speed * 0.25, speed)
            self.particles.append(Particle(pygame.Vector2(center), velocity, lifetime * random.uniform(0.55, 1.15), lifetime, color, random.uniform(2, 5)))
#огонь при выстреле
    def spawn_muzzle(self, start: pygame.Vector2, end: pygame.Vector2) -> None:
        direction = end - start
        if direction.length_squared() == 0:
            direction = pygame.Vector2(1, 0)
        direction = direction.normalize()
        perp = pygame.Vector2(-direction.y, direction.x)
        for _ in range(24):
            base = start + direction * random.uniform(8, SHOTGUN_RANGE)
            jitter = perp * random.uniform(-SHOTGUN_WIDTH * 0.55, SHOTGUN_WIDTH * 0.55)
            velocity = direction * random.uniform(120, 280) + perp * random.uniform(-80, 80)
            self.particles.append(Particle(base + jitter, velocity, 0.16, 0.16, COLOR_SHOT, random.uniform(2, 4)))

    def update(self, dt: float) -> None:
        alive: List[Particle] = []
        for p in self.particles:
            p.lifetime -= dt
            if p.lifetime <= 0:
                continue
            p.pos += p.vel * dt
            p.vel *= max(0.0, 1.0 - 5.0 * dt)
            alive.append(p)
        self.particles = alive

    def draw(self, surface: pygame.Surface) -> None:
        for p in self.particles:
            alpha = int(255 * clamp(p.lifetime / p.max_lifetime, 0.0, 1.0))
            color = (*p.color, alpha)
            pygame.draw.circle(surface, color, (round(p.pos.x), round(p.pos.y)), max(1, round(p.size)))
