# -*- coding: utf-8 -*-
"""Простые частицы: искры, пыль, щепки, брызги."""
from __future__ import annotations

import math
import random

from .assets import draw_particle


class Particle:
    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size", "kind", "gravity")

    def __init__(self, x, y, vx, vy, life, color, size=2, kind="dot", gravity=260.0):
        self.x = float(x)
        self.y = float(y)
        self.vx = float(vx)
        self.vy = float(vy)
        self.life = float(life)
        self.max_life = float(life)
        self.color = color
        self.size = int(size)
        self.kind = kind
        self.gravity = gravity

    def update(self, dt):
        self.life -= dt
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        return self.life > 0


class Particles:
    def __init__(self):
        self.items: list[Particle] = []

    def add(self, p: Particle):
        if len(self.items) < 320:
            self.items.append(p)

    def burst(self, x, y, color, count=8, spread=80, up=110, size=2,
              kind="dot", gravity=260.0, life=0.7):
        for _ in range(count):
            a = random.uniform(-math.pi, 0) if up else random.uniform(0, math.tau)
            speed = random.uniform(spread * 0.25, spread)
            self.add(Particle(x, y, math.cos(a) * speed, math.sin(a) * speed - up * 0.2,
                              random.uniform(life * 0.5, life), color, size, kind, gravity))

    def sparks(self, x, y, color=(255, 220, 120), count=12):
        self.burst(x, y, color, count=count, spread=150, up=160, size=1,
                   kind="spark", gravity=420, life=0.45)

    def splash(self, x, y, color=(150, 220, 255), count=14):
        self.burst(x, y, color, count=count, spread=120, up=170, size=2,
                   kind="dot", gravity=520, life=0.6)

    def update(self, dt):
        self.items = [p for p in self.items if p.update(dt)]

    def draw(self, canvas, cam_x, cam_y):
        for p in self.items:
            draw_particle(canvas, p, cam_x, cam_y)
