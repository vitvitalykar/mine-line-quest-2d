# -*- coding: utf-8 -*-
"""Генерирует icon.ico для exe-сборки (герой Вадик с киркой)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw

from game import assets

BASE = 64
ICON = ROOT / "icon.ico"
PNG = ROOT / "icon.png"


def lerp(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def build_scene() -> pygame.Surface:
    pygame.init()
    pygame.display.set_mode((1, 1))

    scene = pygame.Surface((BASE, BASE)).convert()
    top, bottom = (64, 142, 196), (176, 224, 244)
    for y in range(BASE):
        pygame.draw.line(scene, lerp(top, bottom, y / (BASE - 1)), (0, y), (BASE, y))

    # солнце и облако
    pygame.draw.circle(scene, (255, 236, 160), (50, 12), 8)
    pygame.draw.circle(scene, (255, 248, 214), (50, 12), 5)
    for cx, cy, r in ((12, 16, 4), (17, 14, 5), (23, 16, 4)):
        pygame.draw.circle(scene, (248, 252, 252), (cx, cy), r)

    # дальние холмы и земля
    pygame.draw.polygon(scene, (86, 140, 116),
                        [(0, 52), (0, 44), (16, 34), (34, 46), (48, 38), (64, 47), (64, 52)])
    pygame.draw.rect(scene, (92, 62, 42), (0, 52, BASE, 12))
    pygame.draw.rect(scene, (74, 148, 74), (0, 52, BASE, 4))
    pygame.draw.rect(scene, (56, 118, 62), (0, 56, BASE, 2))
    for x in (4, 10, 54, 60):
        pygame.draw.line(scene, (56, 118, 62), (x, 52), (x + 1, 48), 1)
        pygame.draw.line(scene, (56, 118, 62), (x + 2, 52), (x + 1, 49), 1)

    # герой с киркой
    hero = pygame.Rect(20, 22, 16, 26)
    assets.draw_shadow(scene, hero.centerx, 53, 18)
    assets.draw_player(scene, hero, 1, "idle", "stone_pick", 0.4)

    # светящийся кристалл руды
    gem = [(52, 30), (56, 36), (52, 42), (48, 36)]
    pygame.draw.polygon(scene, (94, 210, 236), gem)
    pygame.draw.polygon(scene, (200, 250, 255),
                        [(52, 32), (54, 36), (52, 40), (50, 36)])
    pygame.draw.line(scene, (36, 120, 160), (52, 30), (52, 42), 1)
    for sx, sy in ((45, 26), (59, 34), (43, 42)):
        scene.set_at((sx, sy), (255, 245, 190))
    return scene


def rounded_icon(scene: pygame.Surface) -> Image.Image:
    raw = pygame.image.tobytes(scene, "RGB")
    img = Image.frombytes("RGB", (BASE, BASE), raw).convert("RGBA")
    mask = Image.new("L", (BASE, BASE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, BASE - 1, BASE - 1), radius=13, fill=255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((1, 1, BASE - 2, BASE - 2), radius=12,
                           outline=(232, 186, 96, 255), width=2)
    draw.rounded_rectangle((3, 3, BASE - 4, BASE - 4), radius=10,
                           outline=(40, 30, 24, 180), width=1)
    return img


def main() -> None:
    icon = rounded_icon(build_scene())
    big = icon.resize((256, 256), Image.Resampling.NEAREST)
    big.save(PNG)
    big.save(ICON, sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                          (64, 64), (128, 128), (256, 256)])
    print("saved", ICON)
    print("saved", PNG)


if __name__ == "__main__":
    main()
