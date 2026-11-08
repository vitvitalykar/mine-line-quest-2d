# -*- coding: utf-8 -*-
"""Вся пиксельная графика рисуется процедурно: без внешних ассетов."""
from __future__ import annotations

import math
import random
from functools import lru_cache

import pygame

from .config import C, SCREEN_H, SCREEN_W, TILE

# ---------------------------------------------------------------------------
# Базовые помощники
# ---------------------------------------------------------------------------


def rect(surf: pygame.Surface, x, y, w, h, color):
    pygame.draw.rect(surf, color, (int(x), int(y), max(0, int(w)), max(0, int(h))))


def outline(surf, x, y, w, h, color, width=1):
    pygame.draw.rect(surf, color, (int(x), int(y), max(0, int(w)), max(0, int(h))), int(width))


def poly(surf, points, color):
    pygame.draw.polygon(surf, color, [(int(px), int(py)) for px, py in points])


def line(surf, a, b, color, width=1):
    pygame.draw.line(surf, color, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), int(width))


def circle(surf, x, y, r, color):
    pygame.draw.circle(surf, color, (int(x), int(y)), max(0, int(r)))


def shade(color, factor: float):
    if factor >= 0:
        return tuple(min(255, int(c + (255 - c) * factor)) for c in color[:3])
    return tuple(max(0, int(c * (1 + factor))) for c in color[:3])


def alpha_surface(size):
    return pygame.Surface((int(size[0]), int(size[1])), pygame.SRCALPHA)


def noise(col: int, row: int, seed: int = 0) -> float:
    n = (col * 73856093) ^ (row * 19349663) ^ (seed * 83492791)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


# ---------------------------------------------------------------------------
# Шрифты
# ---------------------------------------------------------------------------

_FONT_NAMES = "consolas,tahoma,dejavusans,arial"


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    f = pygame.font.SysFont(_FONT_NAMES, size, bold=bold)
    return f


# ---------------------------------------------------------------------------
# Фоны
# ---------------------------------------------------------------------------

_GRADIENT_CACHE: dict[str, pygame.Surface] = {}


def _gradient(top, bottom) -> pygame.Surface:
    key = f"{top}-{bottom}"
    if key in _GRADIENT_CACHE:
        return _GRADIENT_CACHE[key]
    strip = pygame.Surface((1, SCREEN_H))
    for y in range(SCREEN_H):
        k = y / max(1, SCREEN_H - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3))
        strip.set_at((0, y), color)
    surf = pygame.transform.scale(strip, (SCREEN_W, SCREEN_H))
    _GRADIENT_CACHE[key] = surf
    return surf


def _cloud(surf, x, y, scale, color, t):
    s = scale
    circle(surf, x, y, 9 * s, color)
    circle(surf, x + 11 * s, y - 3 * s, 12 * s, color)
    circle(surf, x + 24 * s, y, 8 * s, color)
    rect(surf, x - 4 * s, y, 32 * s, 8 * s, color)
    # лёгкая тень снизу
    dark = shade(color, -0.10)
    rect(surf, x - 2 * s, y + 6 * s, 28 * s, 2 * s, dark)


def _stars(surf, t, color=(220, 230, 255)):
    rnd = random.Random(1337)
    for _ in range(70):
        x = rnd.randrange(0, SCREEN_W)
        y = rnd.randrange(0, 150)
        twinkle = 0.55 + 0.45 * math.sin(t * 2 + x * 0.3)
        c = tuple(int(v * twinkle) for v in color)
        surf.set_at((x, y), c)
        if rnd.random() < 0.08:
            surf.set_at((x + 1, y), c)
            surf.set_at((x, y - 1), c)


def _hills(surf, cam_x, base_y, color, amp=26, step=90, factor=0.18, seed=0):
    offset = -cam_x * factor
    points = [(-40, SCREEN_H)]
    x = -40
    idx = 0
    while x <= SCREEN_W + 60:
        h = amp + 12 * math.sin((x + offset) * 0.011 + seed) + 6 * math.sin((x + offset) * 0.031 + idx)
        points.append((x, base_y - h))
        x += step
        idx += 1
    points.append((SCREEN_W + 60, SCREEN_H))
    poly(surf, points, color)


def _tree_silhouette(surf, x, ground_y, h, color):
    rect(surf, x + h * 0.18, ground_y - h * 0.45, max(2, h * 0.08), h * 0.45, shade(color, -0.2))
    for i in range(3):
        w = h * (0.55 - i * 0.13)
        y = ground_y - h * (0.45 + i * 0.18)
        poly(surf, [(x + h * 0.18, y), (x + h * 0.18 - w, y + h * 0.35), (x + h * 0.18 + w, y + h * 0.35)], color)


def draw_background(canvas, theme: str, t: float, cam_x: float, cam_y: float,
                    level_w: int, level_h: int):
    """Фон рисуется в экранных координатах, с параллаксом."""
    if theme == "forest":
        canvas.blit(_gradient((116, 200, 230), (214, 243, 249)), (0, 0))
        # солнце
        circle(canvas, SCREEN_W - 74, 44, 22, (255, 242, 186))
        circle(canvas, SCREEN_W - 74, 44, 16, (255, 250, 220))
        for i, (mx, my, ms, sp) in enumerate(((70, 46, 1, 0.10), (210, 30, 1, 0.16), (350, 62, 1, 0.08))):
            x = (mx - cam_x * sp + t * 3.2 + i * 33) % (SCREEN_W + 70) - 35
            _cloud(canvas, x, my, ms, (250, 252, 250), t)
        _hills(canvas, cam_x, 206, C["hill_dark"], amp=34, step=76, factor=0.12, seed=1.2)
        _hills(canvas, cam_x, 226, C["hill"], amp=24, step=62, factor=0.24, seed=2.5)
        for i in range(9):
            x = (i * 92 - cam_x * 0.42) % (SCREEN_W + 120) - 60
            _tree_silhouette(canvas, x, 252, 54 + (i % 3) * 12, (62, 114, 86))
        return

    if theme == "cave":
        canvas.blit(_gradient((20, 18, 32), (43, 38, 58)), (0, 0))
        # дальние арки
        for i in range(5):
            x = (i * 122 - cam_x * 0.15) % (SCREEN_W + 160) - 80
            w = 96 + (i % 2) * 40
            top = 76 + (i % 3) * 18
            pygame.draw.arc(canvas, (54, 49, 72), (x, top, w, 150), 0.1, math.pi - 0.1, 7)
            pygame.draw.arc(canvas, (67, 61, 88), (x + 6, top + 8, w - 12, 140), 0.1, math.pi - 0.1, 2)
        # кристаллы
        rnd = random.Random(91)
        for i in range(16):
            x = (rnd.randrange(0, SCREEN_W) - cam_x * 0.25) % (SCREEN_W + 40) - 20
            y = rnd.randrange(120, 240)
            glow = 0.5 + 0.5 * math.sin(t * 2 + i)
            color = (int(64 + 34 * glow), int(156 + 60 * glow), int(196 + 40 * glow))
            poly(canvas, [(x, y), (x + 3, y - 9), (x + 6, y)], color)
        # пылинки
        for i in range(26):
            x = (i * 53 + math.sin(t * 0.4 + i) * 8 - cam_x * 0.1) % SCREEN_W
            y = (i * 37 + math.cos(t * 0.3 + i * 2) * 10) % SCREEN_H
            c = 90 + int(30 * math.sin(t * 3 + i))
            canvas.set_at((int(x), int(y)), (c, c + 12, c + 26))
        return

    if theme == "desert":
        canvas.blit(_gradient((236, 154, 88), (250, 220, 160)), (0, 0))
        circle(canvas, 84, 58, 26, (255, 226, 150))
        circle(canvas, 84, 58, 19, (255, 244, 190))
        _hills(canvas, cam_x, 214, (188, 123, 74), amp=38, step=100, factor=0.10, seed=3.1)
        _hills(canvas, cam_x, 232, (218, 154, 92), amp=26, step=84, factor=0.20, seed=4.4)
        # далёкие скалы
        for i in range(4):
            x = (i * 168 - cam_x * 0.14) % (SCREEN_W + 200) - 90
            poly(canvas, [(x, 206), (x + 28, 150), (x + 52, 178), (x + 76, 206)], (166, 111, 76))
        _cloud(canvas, (150 - cam_x * 0.08 + t * 2) % (SCREEN_W + 80) - 40, 48, 1, (252, 230, 200), t)
        return

    if theme in ("pier", "sea"):
        canvas.blit(_gradient((102, 190, 222), (212, 244, 249)), (0, 0))
        circle(canvas, SCREEN_W - 86, 46, 24, (255, 240, 176))
        circle(canvas, SCREEN_W - 86, 46, 17, (255, 250, 222))
        for i, (mx, my) in enumerate(((70, 46), (250, 32))):
            x = (mx - cam_x * 0.12 + t * 4 + i * 20) % (SCREEN_W + 80) - 40
            _cloud(canvas, x, my, 1, (250, 252, 250), t)
        horizon = 142
        rect(canvas, 0, horizon, SCREEN_W, SCREEN_H - horizon, C["water"])
        rect(canvas, 0, horizon, SCREEN_W, 6, C["water_light"])
        # волны
        for row in range(horizon + 18, SCREEN_H, 14):
            for i in range(-1, SCREEN_W // 22 + 2):
                x = i * 22 + math.sin(t * 2 + row * 0.3 + i) * 5 - (cam_x * 0.15) % 22
                line(canvas, (x, row), (x + 9, row), C["water_light"], 1)
        # далёкий остров
        island_x = (220 - cam_x * 0.10) % (SCREEN_W + 120) - 60
        poly(canvas, [(island_x, horizon), (island_x + 26, horizon - 20), (island_x + 54, horizon)], (104, 146, 120))
        # птицы
        for i in range(3):
            bx = (i * 97 + t * 8 - cam_x * 0.05) % (SCREEN_W + 40) - 20
            by = 74 + i * 13 + math.sin(t * 2 + i) * 3
            line(canvas, (bx - 4, by), (bx, by - 3), (60, 70, 90), 1)
            line(canvas, (bx, by - 3), (bx + 4, by), (60, 70, 90), 1)
        return

    if theme == "arena":
        canvas.blit(_gradient((26, 12, 32), (68, 24, 38)), (0, 0))
        circle(canvas, 96, 52, 30, (198, 72, 70))
        circle(canvas, 96, 52, 24, (236, 104, 82))
        for i in range(4):
            x = (i * 142 - cam_x * 0.16) % (SCREEN_W + 180) - 70
            _tree_silhouette(canvas, x, 250, 70 + i * 8, (48, 20, 36))
        # мрачные облака
        for i in range(4):
            x = (i * 130 - cam_x * 0.08 + t * 2) % (SCREEN_W + 100) - 50
            _cloud(canvas, x, 26 + (i % 2) * 20, 1, (78, 30, 48), t)
        # искры
        for i in range(24):
            x = (i * 41 + math.sin(t + i) * 6 - cam_x * 0.2) % SCREEN_W
            y = (SCREEN_H - (i * 23 + t * 18) % (SCREEN_H - 60))
            c = (220, 90 + int(40 * math.sin(t * 4 + i)), 60)
            canvas.set_at((int(x), int(y)), c)
        return

    if theme == "victory":
        canvas.blit(_gradient((255, 196, 120), (255, 122, 102)), (0, 0))
        for i in range(6):
            x = (i * 83 + 20 + math.sin(t * 0.7 + i) * 10) % SCREEN_W
            y = 40 + (i * 31) % 130
            for k in range(8):
                a = k * math.pi / 4 + t * 0.4
                line(canvas, (x, y), (x + math.cos(a) * 13, y + math.sin(a) * 13), (255, 236, 160), 1)
        return

    # title / fallback
    canvas.blit(_gradient((7, 10, 26), (28, 34, 62)), (0, 0))
    _stars(canvas, t)
    circle(canvas, 368, 54, 26, (232, 226, 190))
    circle(canvas, 358, 48, 22, (28, 34, 62))
    _hills(canvas, cam_x, 224, (18, 24, 40), amp=34, step=84, factor=0.08, seed=1.1)
    _hills(canvas, cam_x, 244, (12, 16, 30), amp=22, step=66, factor=0.16, seed=2.2)
    for i in range(7):
        x = (i * 96 - cam_x * 0.3) % (SCREEN_W + 120) - 60
        _tree_silhouette(canvas, x, 258, 44 + (i % 3) * 10, (10, 14, 24))


# ---------------------------------------------------------------------------
# Тайлы
# ---------------------------------------------------------------------------


def _grass_tuft(canvas, x, y, rnd):
    for i in range(3):
        dx = i * 2 - 2
        line(canvas, (x + dx, y), (x + dx + rnd.choice((-1, 1)), y - 3), C["grass_dark"], 1)


def _flower(canvas, x, y, color):
    x, y = int(x), int(y)
    canvas.set_at((x, y), color)
    canvas.set_at((x + 1, y), shade(color, 0.2))
    canvas.set_at((x, y + 1), shade(color, -0.2))


def draw_tile(canvas, kind: str, theme: str, sx: int, sy: int,
              col: int, row: int, t: float, top_open: bool):
    sx, sy = int(sx), int(sy)
    r = noise(col, row)
    if kind == "rock":
        base = C["rock"]
        dark = C["rock_dark"]
        light = C["rock_light"]
        if theme == "desert":
            base, dark, light = (128, 92, 66), (92, 64, 48), (170, 130, 92)
        rect(canvas, sx, sy, TILE, TILE, base)
        outline(canvas, sx, sy, TILE, TILE, dark)
        if top_open:
            rect(canvas, sx, sy, TILE, 3, light)
            rect(canvas, sx, sy + 3, TILE, 1, shade(light, -0.15))
        # трещины/крапины
        if r > 0.55:
            line(canvas, (sx + 4, sy + 5), (sx + 8, sy + 10), dark, 1)
            line(canvas, (sx + 8, sy + 10), (sx + 7, sy + 14), dark, 1)
        if r < 0.25:
            rect(canvas, sx + 10, sy + 4, 2, 2, light)
        if theme == "cave" and r > 0.82:
            circle(canvas, sx + 5, sy + 9, 1, C["cyan"])
        return

    if kind == "ground":
        if theme == "forest":
            top, dirt, dirt_dark = C["grass"], C["dirt"], C["dirt_dark"]
            rect(canvas, sx, sy, TILE, TILE, dirt)
            rect(canvas, sx, sy, TILE, 4, top)
            rect(canvas, sx, sy + 4, TILE, 2, shade(top, -0.18))
            outline(canvas, sx, sy, TILE, TILE, dirt_dark)
            if r > 0.35:
                _grass_tuft(canvas, sx + 4, sy + 1, random.Random(int(r * 1000) + col))
            if r > 0.78:
                _flower(canvas, sx + 11, sy + 1, (240, 210, 90) if r > 0.9 else (230, 110, 150))
            if r < 0.12:
                rect(canvas, sx + 3, sy + 8, 2, 2, shade(dirt, -0.2))
        elif theme == "desert":
            rect(canvas, sx, sy, TILE, TILE, C["sand_dark"])
            rect(canvas, sx, sy, TILE, 5, C["sand"])
            rect(canvas, sx, sy + 5, TILE, 1, shade(C["sand"], -0.15))
            outline(canvas, sx, sy, TILE, TILE, C["sand_dark"])
            if r > 0.6:
                rect(canvas, sx + 3, sy + 2, 3, 1, shade(C["sand"], 0.2))
        elif theme == "pier":
            rect(canvas, sx, sy, TILE, TILE, C["wood"])
            rect(canvas, sx, sy, TILE, 3, C["wood_light"])
            outline(canvas, sx, sy, TILE, TILE, C["wood_dark"])
            line(canvas, (sx, sy + 7), (sx + TILE, sy + 7), C["wood_dark"], 1)
            line(canvas, (sx, sy + 14), (sx + TILE, sy + 14), C["wood_dark"], 1)
            canvas.set_at((sx + 3, sy + 3), C["cream"])
            canvas.set_at((sx + 12, sy + 10), C["cream"])
        elif theme == "arena":
            rect(canvas, sx, sy, TILE, TILE, (45, 38, 44))
            rect(canvas, sx, sy, TILE, 4, (72, 58, 52))
            outline(canvas, sx, sy, TILE, TILE, (28, 22, 28))
            if r > 0.7:
                line(canvas, (sx + 2, sy + 2), (sx + 5, sy - 2), (96, 74, 58), 1)
        else:  # cave
            rect(canvas, sx, sy, TILE, TILE, (58, 54, 70))
            rect(canvas, sx, sy, TILE, 4, (92, 86, 104))
            outline(canvas, sx, sy, TILE, TILE, (34, 31, 44))
            if r > 0.72:
                rect(canvas, sx + 4, sy + 6, 3, 2, (74, 68, 88))
        return

    if kind == "struct":
        if theme in ("pier", "forest"):
            rect(canvas, sx + 2, sy, TILE - 4, TILE, C["wood"])
            rect(canvas, sx + 2, sy, 3, TILE, C["wood_light"])
            rect(canvas, sx + TILE - 5, sy, 3, TILE, C["wood_dark"])
            outline(canvas, sx + 2, sy, TILE - 4, TILE, C["wood_dark"])
            line(canvas, (sx + 3, sy + 5), (sx + TILE - 3, sy + 5), C["wood_dark"], 1)
        else:
            rect(canvas, sx, sy, TILE, TILE, (82, 76, 94))
            outline(canvas, sx, sy, TILE, TILE, (44, 40, 56))
            line(canvas, (sx, sy + 8), (sx + TILE, sy + 8), (60, 56, 72), 1)
            line(canvas, (sx + 8, sy), (sx + 8, sy + 8), (60, 56, 72), 1)
        return

    if kind == "dock":
        rect(canvas, sx, sy, TILE, TILE, C["wood"])
        rect(canvas, sx, sy, TILE, 3, C["wood_light"])
        outline(canvas, sx, sy, TILE, TILE, C["wood_dark"])
        line(canvas, (sx, sy + 6), (sx + TILE, sy + 6), C["wood_dark"], 1)
        line(canvas, (sx, sy + 12), (sx + TILE, sy + 12), C["wood_dark"], 1)
        canvas.set_at((sx + 4, sy + 2), C["cream"])
        return

    if kind == "water":
        wave = math.sin(t * 2.2 + col * 0.7 + row * 0.25)
        depth = shade(C["water"], -0.10 * max(0, row % 3))
        rect(canvas, sx, sy, TILE, TILE, depth)
        if top_open:
            rect(canvas, sx, sy, TILE, 2, C["water_light"])
        for i in range(2):
            yy = sy + 5 + i * 6 + int(wave * 2)
            xx = sx + (int(t * 16 + i * 7 + col * 3) % TILE)
            line(canvas, (xx - 5, yy), (xx + 5, yy), C["water_light"], 1)
        if noise(col, row, 3) > 0.93:
            canvas.set_at((sx + 3, sy + 9), C["water_light"])
        return


def draw_ground_skirt(canvas, theme: str, sx: int, sy: int, bottom: int):
    """Земляной/водный слой под верхним тайлом, чтобы не было «парения»."""
    if theme in ("forest", "desert"):
        color = C["dirt_dark"] if theme == "forest" else C["sand_dark"]
        rect(canvas, sx, sy, TILE, max(0, bottom - sy), color)
        rect(canvas, sx, sy, 1, max(0, bottom - sy), shade(color, -0.15))
    elif theme == "pier":
        rect(canvas, sx, sy, TILE, max(0, bottom - sy), C["water_dark"])
    elif theme == "arena":
        rect(canvas, sx, sy, TILE, max(0, bottom - sy), (28, 22, 28))


# ---------------------------------------------------------------------------
# Спрайты
# ---------------------------------------------------------------------------


def draw_shadow(canvas, cx, feet_y, w=18):
    shadow = alpha_surface((w + 8, 8))
    pygame.draw.ellipse(shadow, (0, 0, 0, 90), (0, 0, w + 8, 8))
    canvas.blit(shadow, (int(cx - (w + 8) / 2), int(feet_y - 4)))


def _tool(canvas, ox, oy, kind, phase, facing):
    """Рисует кирку/меч в руке. phase: 0..1 — замах."""
    if kind is None:
        return
    hand = (ox + (12 if facing > 0 else 4), oy + 14)
    if kind in ("stone_pick", "iron_pick"):
        head_color = C["iron"] if kind == "iron_pick" else (150, 150, 150)
        dark = C["iron_dark"] if kind == "iron_pick" else (96, 96, 96)
        # угол замаха
        ang = -0.9 + phase * 1.9
        dx, dy = math.cos(ang) * (8 if facing > 0 else -8), math.sin(ang) * 8
        tip = (hand[0] + dx, hand[1] + dy)
        line(canvas, hand, tip, C["wood_dark"], 2)
        # голова кирки
        perp = (-dy * 0.5, dx * 0.5)
        line(canvas, (tip[0] - perp[0], tip[1] - perp[1]),
             (tip[0] + perp[0], tip[1] + perp[1]), head_color, 3)
        line(canvas, (tip[0] - perp[0], tip[1] - perp[1] - 1),
             (tip[0] + perp[0], tip[1] + perp[1] - 1), dark, 1)
    else:
        blade = C["iron"] if kind == "iron_sword" else (160, 160, 160)
        dark = C["iron_dark"] if kind == "iron_sword" else (96, 96, 96)
        ang = -1.2 + phase * 2.1
        dx, dy = math.cos(ang) * (10 if facing > 0 else -10), math.sin(ang) * 10
        tip = (hand[0] + dx, hand[1] + dy)
        line(canvas, hand, tip, blade, 2)
        line(canvas, (hand[0] - 2, hand[1] - 2), (hand[0] + 2, hand[1] + 2), C["gold"], 1)
        line(canvas, (tip[0] - 1, tip[1]), (tip[0] + 1, tip[1]), dark, 1)


def draw_player(canvas, rect_: pygame.Rect, facing: int, state: str,
                equipment: str | None, t: float, attack: float = 0.0,
                defend: float = 0.0, hurt: float = 0.0, riding_boat: bool = False):
    """Герой Вадик. Размер спрайта чуть больше хитбокса — так красивее."""
    w, h = rect_.width, rect_.height
    ox, oy = rect_.x, rect_.y

    if riding_boat:
        draw_boat(canvas, ox + w / 2, oy + h - 6, t, riding=True)
        # видимая верхняя часть героя
        top = alpha_surface((24, 24))
        rect(top, 8, 8, 8, 8, C["tunic"])
        rect(top, 9, 9, 6, 6, C["skin"])
        rect(top, 9, 9, 6, 2, C["hair"])
        top.set_at((10, 12), C["outline"])
        top.set_at((13, 12), C["outline"])
        rect(top, 11, 16, 2, 4, C["tunic_dark"])
        if facing < 0:
            top = pygame.transform.flip(top, True, False)
        canvas.blit(top, (int(ox - 4), int(oy + 1)))
        return

    surf = alpha_surface((28, 34))
    bx, by = 6, 4
    run_phase = int(t * 11) % 4
    moving = state in ("run", "walk")
    bob = 0
    if moving:
        bob = (0, -1, 0, 1)[run_phase]

    # тень
    # (рисуется отдельно в мире)

    # ноги
    leg_off = (0, 2, 0, -2)[run_phase] if moving else 0
    if state == "jump":
        rect(surf, bx + 3, by + 18, 4, 8, C["pants"])
        rect(surf, bx + 9, by + 18, 4, 7, C["pants"])
        rect(surf, bx + 2, by + 25, 5, 3, C["boots"])
        rect(surf, bx + 9, by + 24, 5, 3, C["boots"])
    else:
        rect(surf, bx + 4, by + 17 + bob, 3, 8 + leg_off, C["pants"])
        rect(surf, bx + 9, by + 17 + bob, 3, 8 - leg_off, C["pants"])
        rect(surf, bx + 3, by + 24 + bob + leg_off, 4, 3, C["boots"])
        rect(surf, bx + 9, by + 24 + bob - leg_off, 4, 3, C["boots"])

    # туловище
    rect(surf, bx + 4, by + 8 + bob, 8, 10, C["tunic"])
    rect(surf, bx + 4, by + 8 + bob, 8, 2, shade(C["tunic"], 0.15))
    rect(surf, bx + 4, by + 14 + bob, 8, 2, C["tunic_dark"])
    rect(surf, bx + 5, by + 15 + bob, 6, 1, C["gold"])
    # руки
    rect(surf, bx + 2, by + 10 + bob, 2, 6, C["skin"])
    rect(surf, bx + 12, by + 10 + bob, 2, 6, C["skin"])
    # голова
    rect(surf, bx + 4, by + 0 + bob, 8, 8, C["skin"])
    rect(surf, bx + 3, by + 0 + bob, 10, 3, C["hair"])
    rect(surf, bx + 4, by + 2 + bob, 2, 3, C["hair"])
    # глаза и нос
    surf.set_at((bx + 7, by + 4 + bob), C["outline"])
    surf.set_at((bx + 10, by + 4 + bob), C["outline"])
    rect(surf, bx + 8, by + 5 + bob, 1, 1, C["skin_dark"])
    # улыбка
    surf.set_at((bx + 8, by + 7 + bob), C["skin_dark"])
    surf.set_at((bx + 9, by + 7 + bob), C["skin_dark"])

    # снаряжение
    if defend > 0:
        # меч вертикально перед героем
        col = C["iron"] if equipment == "iron_sword" else (160, 160, 160)
        line(surf, (bx + 15, by + 4), (bx + 15, by + 18), col, 2)
        line(surf, (bx + 13, by + 12), (bx + 17, by + 12), C["gold"], 1)
        line(surf, (bx + 15, by + 18), (bx + 15, by + 21), C["wood_dark"], 2)
    else:
        phase = 0.0
        if attack > 0:
            phase = 1.0 - max(0.0, min(1.0, attack / 0.22))
        _tool(surf, bx, by + bob, equipment, phase, facing)

    if hurt > 0:
        overlay = alpha_surface(surf.get_size())
        overlay.fill((255, 80, 80, 110))
        surf.blit(overlay, (0, 0))

    if facing < 0:
        surf = pygame.transform.flip(surf, True, False)

    canvas.blit(surf, (int(ox - 6), int(oy - 2)))


def draw_dragon(canvas, x, y, t: float, facing: int = 1, scale: float = 1.0):
    """Дракон Джек."""
    w, h = int(40 * scale), int(32 * scale)
    surf = alpha_surface((w, h))
    flap = math.sin(t * 7) * 4
    bx, by = 4, 6
    # крылья
    poly(surf, [(14, 14), (2, 8 + flap), (6, 20)], (62, 138, 96))
    poly(surf, [(22, 14), (36, 7 - flap), (32, 21)], (62, 138, 96))
    poly(surf, [(14, 14), (4, 10 + flap), (8, 18)], (96, 180, 126))
    poly(surf, [(22, 14), (34, 9 - flap), (31, 19)], (96, 180, 126))
    # тело
    pygame.draw.ellipse(surf, (74, 158, 104), (10, 12, 18, 12))
    pygame.draw.ellipse(surf, (104, 196, 132), (12, 13, 14, 7))
    # хвост
    line(surf, (11, 21), (2, 27), (74, 158, 104), 3)
    poly(surf, [(1, 25), (5, 27), (2, 30)], (62, 138, 96))
    # лапы
    rect(surf, 14, 22, 3, 5, (54, 118, 82))
    rect(surf, 23, 22, 3, 5, (54, 118, 82))
    # голова
    rect(surf, 25, 6, 10, 9, (86, 172, 112))
    rect(surf, 28, 9, 7, 4, (112, 204, 136))
    rect(surf, 31, 5, 1, 4, (238, 222, 170))  # рог
    rect(surf, 28, 5, 1, 4, (238, 222, 170))
    surf.set_at((31, 10), C["outline"])
    surf.set_at((31, 11), C["outline"])
    # зубы
    surf.set_at((34, 13), (245, 245, 230))
    surf.set_at((36, 13), (245, 245, 230))
    # блик
    surf.set_at((29, 12), (190, 240, 200))
    if facing < 0:
        surf = pygame.transform.flip(surf, True, False)
    canvas.blit(surf, (int(x - w / 2), int(y - h)))


def draw_boss(canvas, x, y, t: float, hp: int, max_hp: int,
              defeated: bool = False, windup: bool = False, flash: float = 0.0):
    """Король-гоблин. Огромный, но помещается в кадр."""
    w, h = 110, 136
    surf = alpha_surface((w, h))
    if defeated:
        # тушка на земле
        pygame.draw.ellipse(surf, (78, 92, 62), (10, 88, 90, 40))
        pygame.draw.ellipse(surf, (98, 116, 74), (16, 92, 74, 26))
        rect(surf, 30, 116, 12, 6, (60, 72, 50))
        rect(surf, 66, 116, 12, 6, (60, 72, 50))
        # корона
        poly(surf, [(36, 88), (40, 76), (48, 86), (54, 74), (60, 86), (68, 76), (72, 88)], C["gold"])
        canvas.blit(surf, (int(x - w / 2), int(y - h)))
        return

    breath = math.sin(t * 2.2) * 2
    bx, by = 8, 8 + breath * 0.5
    # ноги
    rect(surf, bx + 20, by + 94, 22, 34, (70, 84, 56))
    rect(surf, bx + 62, by + 94, 22, 34, (70, 84, 56))
    rect(surf, bx + 14, by + 122, 32, 10, (48, 56, 40))
    rect(surf, bx + 60, by + 122, 32, 10, (48, 56, 40))
    # тело
    pygame.draw.ellipse(surf, (88, 108, 66), (bx + 14, by + 44, 78, 64))
    pygame.draw.ellipse(surf, (108, 132, 78), (bx + 22, by + 50, 60, 42))
    # живот
    pygame.draw.ellipse(surf, (154, 160, 96), (bx + 30, by + 62, 46, 36))
    # руки
    rect(surf, bx + 2, by + 50, 18, 44, (78, 96, 60))
    rect(surf, bx + 90, by + 46, 18, 44, (78, 96, 60))
    # кулаки
    circle(surf, bx + 10, by + 96, 12, (88, 108, 66))
    circle(surf, bx + 98, by + 94, 12, (88, 108, 66))
    # дубина
    club_angle = -0.9 if windup else 0.55
    hand = (bx + 98, by + 90)
    tip = (hand[0] + math.cos(club_angle) * 34, hand[1] + math.sin(club_angle) * 34)
    line(surf, hand, tip, (112, 76, 42), 10)
    circle(surf, tip[0], tip[1], 13, (128, 88, 50))
    circle(surf, tip[0] - 3, tip[1] - 3, 5, (156, 112, 66))
    for i in range(4):
        a = i * 1.4
        circle(surf, tip[0] + math.cos(a) * 9, tip[1] + math.sin(a) * 9, 2, (80, 52, 32))
    # голова
    pygame.draw.ellipse(surf, (96, 120, 70), (bx + 22, by + 2, 54, 52))
    pygame.draw.ellipse(surf, (120, 146, 84), (bx + 28, by + 8, 42, 38))
    # уши
    poly(surf, [(bx + 22, by + 22), (bx - 2, by + 8), (bx + 24, by + 10)], (96, 120, 70))
    poly(surf, [(bx + 76, by + 22), (bx + 100, by + 8), (bx + 74, by + 10)], (96, 120, 70))
    # глаза
    rect(surf, bx + 34, by + 20, 10, 5, (245, 220, 120))
    rect(surf, bx + 58, by + 20, 10, 5, (245, 220, 120))
    rect(surf, bx + 36, by + 21, 4, 3, (40, 24, 24))
    rect(surf, bx + 62, by + 21, 4, 3, (40, 24, 24))
    # брови
    line(surf, (bx + 31, by + 15), (bx + 45, by + 18), (58, 74, 44), 3)
    line(surf, (bx + 58, by + 18), (bx + 72, by + 15), (58, 74, 44), 3)
    # рот и клыки
    rect(surf, bx + 38, by + 38, 24, 8, (54, 32, 32))
    rect(surf, bx + 40, by + 38, 20, 3, (220, 210, 180))
    poly(surf, [(bx + 41, by + 45), (bx + 44, by + 52), (bx + 47, by + 45)], (240, 232, 200))
    poly(surf, [(bx + 58, by + 45), (bx + 61, by + 52), (bx + 64, by + 45)], (240, 232, 200))
    # корона
    poly(surf, [(bx + 26, by + 2), (bx + 30, by - 12), (bx + 38, by + 0),
                (bx + 46, by - 15), (bx + 54, by + 0), (bx + 62, by - 12),
                (bx + 66, by + 2)], C["gold"])
    rect(surf, bx + 26, by + 2, 42, 4, shade(C["gold"], -0.2))
    circle(surf, bx + 46, by - 6, 2, C["red"])

    if flash > 0:
        over = alpha_surface((w, h))
        over.fill((255, 240, 240, int(150 * min(1.0, flash / 0.16))))
        surf.blit(over, (0, 0))

    canvas.blit(surf, (int(x - w / 2), int(y - h)))

    # полоска HP
    if not defeated:
        bar_w = 84
        bar_x = int(x - bar_w / 2)
        bar_y = int(y - h - 16)
        rect(canvas, bar_x - 2, bar_y - 2, bar_w + 4, 10, (20, 16, 24))
        rect(canvas, bar_x, bar_y, bar_w, 6, (60, 28, 34))
        for i in range(max_hp):
            if i < hp:
                rect(canvas, bar_x + i * (bar_w // max_hp) + 2, bar_y + 1,
                     bar_w // max_hp - 3, 4, (224, 72, 72))
        for i in range(max_hp):
            hx = bar_x + i * (bar_w // max_hp) + bar_w // (2 * max_hp)
            # сердечко-иконка
            canvas.set_at((int(hx) - 1, bar_y + 2), (255, 180, 180))
            canvas.set_at((int(hx), bar_y + 2), (255, 180, 180))
            canvas.set_at((int(hx) + 1, bar_y + 2), (255, 180, 180))
            canvas.set_at((int(hx), bar_y + 3), (255, 120, 120))


def draw_tree(canvas, x, y, t: float, broken: bool = False,
              wise: bool = False, cave: bool = False):
    if wise:
        w, h = 150, 176
        surf = alpha_surface((w, h))
        # корни
        poly(surf, [(52, h - 8), (30, h - 26), (46, h - 22), (58, h - 34),
                    (64, h - 18), (72, h - 34), (82, h - 22), (98, h - 28),
                    (78, h - 6)], (92, 62, 38))
        # ствол
        poly(surf, [(58, h - 30), (62, 66), (88, 62), (96, h - 28)], (116, 78, 44))
        poly(surf, [(64, h - 32), (68, 70), (80, 68), (82, h - 30)], (146, 100, 58))
        # ветви
        line(surf, (70, 92), (28, 46), (116, 78, 44), 9)
        line(surf, (84, 88), (126, 38), (116, 78, 44), 9)
        line(surf, (34, 48), (18, 26), (116, 78, 44), 5)
        line(surf, (120, 40), (140, 20), (116, 78, 44), 5)
        # крона
        clusters = [(24, 34, 30), (54, 18, 36), (92, 22, 34), (124, 34, 28),
                    (44, 56, 32), (82, 56, 34), (112, 62, 26), (66, 40, 30)]
        for i, (cx, cy, r) in enumerate(clusters):
            base = (52, 126, 68) if not cave else (52, 112, 92)
            circle(surf, cx, cy, r, base)
            circle(surf, cx - 4, cy - 5, r - 5, shade(base, 0.16))
        # лицо
        circle(surf, 70, 118, 3, (40, 30, 24))
        circle(surf, 86, 118, 3, (40, 30, 24))
        pygame.draw.arc(surf, (40, 30, 24), (70, 124, 20, 14), 0.2, math.pi - 0.2, 2)
        # светлячки
        for i in range(6):
            fx = 26 + (i * 23) % 110
            fy = 30 + (i * 31) % 80
            glow = 0.5 + 0.5 * math.sin(t * 3 + i)
            circle(surf, fx, fy, 1, (220, 255, int(150 + 80 * glow)))
        canvas.blit(surf, (int(x), int(y - h)))
        return

    w, h = 46, 70
    surf = alpha_surface((w, h))
    if broken:
        rect(surf, 18, h - 18, 12, 16, (110, 74, 44))
        rect(surf, 16, h - 6, 16, 6, (86, 56, 34))
        poly(surf, [(30, h - 18), (42, h - 24), (36, h - 14)], (110, 74, 44))
        line(surf, (20, h - 16), (14, h - 24), (86, 56, 34), 2)
        canvas.blit(surf, (int(x - w / 2), int(y - h)))
        return
    canopy = (48, 130, 76) if not cave else (52, 112, 104)
    rect(surf, 20, h - 30, 8, 30, (110, 74, 44))
    rect(surf, 22, h - 30, 3, 30, (142, 98, 58))
    circle(surf, 23, 24, 17, canopy)
    circle(surf, 12, 34, 12, canopy)
    circle(surf, 34, 34, 12, canopy)
    circle(surf, 23, 14, 12, shade(canopy, 0.16))
    circle(surf, 17, 22, 9, shade(canopy, 0.24))
    circle(surf, 31, 24, 8, shade(canopy, 0.10))
    # ствол поверх кроны
    rect(surf, 20, 34, 8, h - 34, (110, 74, 44))
    rect(surf, 22, 34, 3, h - 34, (142, 98, 58))
    if cave:
        for i in range(3):
            circle(surf, 16 + i * 7, 20 + i * 5, 1, (140, 240, 220))
    canvas.blit(surf, (int(x - w / 2), int(y - h)))


def draw_ore(canvas, x, y, t: float):
    w, h = 32, 28
    surf = alpha_surface((w, h))
    pygame.draw.ellipse(surf, (86, 88, 104), (2, 8, 28, 20))
    pygame.draw.ellipse(surf, (118, 120, 136), (5, 10, 22, 15))
    for i, (cx, cy, r) in enumerate(((10, 14, 3), (18, 11, 4), (23, 17, 3), (14, 20, 2), (20, 22, 2))):
        glow = 0.5 + 0.5 * math.sin(t * 2.5 + i)
        col = (int(72 + 40 * glow), int(170 + 60 * glow), int(220 + 30 * glow))
        poly(surf, [(cx - r, cy + r), (cx, cy - r), (cx + r, cy + r)], col)
        surf.set_at((cx, cy), (220, 255, 255))
    canvas.blit(surf, (int(x - w / 2), int(y - h)))


def draw_stone(canvas, x, y, t: float):
    w, h = 30, 34
    surf = alpha_surface((w, h))
    pygame.draw.ellipse(surf, (100, 102, 118), (2, 6, 26, 26))
    pygame.draw.ellipse(surf, (136, 138, 154), (4, 8, 20, 18))
    line(surf, (8, 14), (13, 20), (74, 76, 92), 1)
    line(surf, (13, 20), (11, 27), (74, 76, 92), 1)
    line(surf, (20, 10), (23, 17), (74, 76, 92), 1)
    rect(surf, 7, 9, 4, 2, (180, 182, 196))
    if math.sin(t * 2.8) > 0.8:
        canvas.set_at((int(x + 13), int(y - h + 2)), (255, 255, 220))
    canvas.blit(surf, (int(x - w / 2), int(y - h)))


def draw_boat(canvas, x, y, t: float, riding: bool = False):
    w, h = 54, 26
    surf = alpha_surface((w, h))
    bob = math.sin(t * 3) * 1.5
    y0 = 6 + bob
    poly(surf, [(3, y0 + 4), (51, y0 + 4), (44, y0 + 18), (10, y0 + 18)], (124, 80, 42))
    poly(surf, [(5, y0 + 5), (49, y0 + 5), (43, y0 + 12), (11, y0 + 12)], (166, 112, 60))
    line(surf, (3, y0 + 4), (51, y0 + 4), (88, 54, 30), 2)
    line(surf, (10, y0 + 18), (44, y0 + 18), (88, 54, 30), 2)
    # весло
    if not riding:
        line(surf, (8, y0 + 2), (0, y0 + 16), (98, 61, 35), 2)
        line(surf, (49, y0 + 2), (57, y0 + 16), (98, 61, 35), 2)
    # сиденье
    rect(surf, 20, y0 + 2, 14, 3, (104, 66, 38))
    canvas.blit(surf, (int(x - w / 2), int(y - h + 2)))


def draw_trader(canvas, x, y, t: float):
    w, h = 30, 38
    surf = alpha_surface((w, h))
    # ноги
    rect(surf, 10, h - 10, 4, 10, (54, 58, 82))
    rect(surf, 17, h - 10, 4, 10, (54, 58, 82))
    # фартук
    rect(surf, 8, 16, 14, 14, (98, 61, 35))
    rect(surf, 10, 18, 10, 10, (142, 92, 49))
    # тело
    rect(surf, 7, 10, 16, 12, (150, 70, 60))
    rect(surf, 10, 12, 10, 8, (190, 170, 120))
    # руки
    rect(surf, 4, 14, 4, 10, C["skin"])
    rect(surf, 22, 14, 4, 10, C["skin"])
    # голова
    rect(surf, 9, 2, 12, 10, C["skin"])
    rect(surf, 8, 1, 14, 4, (86, 58, 34))
    rect(surf, 10, 9, 10, 4, (110, 74, 44))  # борода
    surf.set_at((12, 7), C["outline"])
    surf.set_at((18, 7), C["outline"])
    # молот
    line(surf, (24, 16), (28, 6), C["wood_dark"], 2)
    rect(surf, 24, 3, 8, 5, C["iron"])
    rect(surf, 24, 3, 8, 1, C["iron_dark"])
    # искры
    if math.sin(t * 6) > 0.6:
        canvas.set_at((int(x + 10), int(y - h + 4)), (255, 220, 120))
    canvas.blit(surf, (int(x - w / 2), int(y - h)))


def draw_mine(canvas, x, y, t: float):
    w, h = 76, 64
    surf = alpha_surface((w, h))
    # скала
    pygame.draw.ellipse(surf, (78, 70, 66), (0, 8, w, h - 4))
    # проём
    pygame.draw.ellipse(surf, (16, 14, 20), (18, 18, 40, 42))
    rect(surf, 22, 40, 32, 20, (12, 10, 16))
    # опоры
    rect(surf, 10, 14, 6, 46, (110, 74, 44))
    rect(surf, 60, 14, 6, 46, (110, 74, 44))
    rect(surf, 8, 12, 60, 6, (142, 98, 58))
    line(surf, (12, 18), (24, 30), (142, 98, 58), 3)
    line(surf, (64, 18), (52, 30), (142, 98, 58), 3)
    # рельсы
    line(surf, (26, 58), (36, 50), (100, 100, 110), 2)
    line(surf, (50, 58), (40, 50), (100, 100, 110), 2)
    # фонарь
    circle(surf, 38, 22, 3, (255, 220, 120))
    circle(surf, 38, 22, 5, (180, 140, 60))
    canvas.blit(surf, (int(x - w / 2), int(y - h)))


def draw_sign(canvas, x, y, t: float, color=(142, 92, 49)):
    w, h = 30, 36
    surf = alpha_surface((w, h))
    rect(surf, 13, h - 18, 4, 18, C["wood_dark"])
    rect(surf, 2, 6, 26, 16, color)
    outline(surf, 2, 6, 26, 16, C["wood_dark"])
    rect(surf, 4, 8, 22, 2, shade(color, 0.2))
    line(surf, (6, 13), (24, 13), shade(color, -0.25), 1)
    line(surf, (6, 17), (20, 17), shade(color, -0.25), 1)
    canvas.blit(surf, (int(x - w / 2), int(y - h)))


def draw_torch(canvas, x, y, t: float):
    rect(canvas, x - 1, y - 18, 2, 18, C["wood_dark"])
    flame = 1 + 0.5 * math.sin(t * 9)
    circle(canvas, x, y - 21, 3 + flame, (235, 120, 40))
    circle(canvas, x, y - 22, 2, (255, 220, 100))
    canvas.set_at((int(x), int(y - 25)), (255, 240, 160))


def draw_anvil(canvas, x, y, t: float):
    rect(canvas, x - 7, y - 8, 14, 5, C["iron_dark"])
    rect(canvas, x - 9, y - 11, 18, 4, C["iron"])
    rect(canvas, x - 4, y - 3, 8, 3, C["iron_dark"])
    if math.sin(t * 8) > 0.7:
        canvas.set_at((int(x + 2), int(y - 14)), (255, 230, 140))
        canvas.set_at((int(x - 3), int(y - 16)), (255, 200, 100))


def draw_barrel(canvas, x, y):
    rect(canvas, x - 6, y - 14, 12, 14, C["wood"])
    rect(canvas, x - 6, y - 14, 12, 2, C["wood_light"])
    rect(canvas, x - 6, y - 9, 12, 1, C["wood_dark"])
    rect(canvas, x - 6, y - 3, 12, 1, C["wood_dark"])


def draw_crate(canvas, x, y):
    rect(canvas, x - 7, y - 14, 14, 14, C["wood"])
    outline(canvas, x - 7, y - 14, 14, 14, C["wood_dark"])
    line(canvas, (x - 6, y - 13), (x + 6, y - 1), C["wood_dark"], 1)
    line(canvas, (x + 6, y - 13), (x - 6, y - 1), C["wood_dark"], 1)


def draw_crystal(canvas, x, y, t: float, color=(96, 220, 230)):
    glow = 0.5 + 0.5 * math.sin(t * 2 + x)
    c = tuple(int(v * (0.7 + 0.3 * glow)) for v in color)
    poly(canvas, [(x, y), (x + 3, y - 10), (x + 6, y)], c)
    poly(canvas, [(x + 3, y), (x + 6, y - 7), (x + 9, y)], shade(c, -0.2))
    canvas.set_at((int(x + 3), int(y - 6)), (230, 255, 255))


def draw_stalactite(canvas, x, y, length, color=(70, 64, 84)):
    poly(canvas, [(x - 3, y), (x + 3, y), (x, y + length)], color)


def draw_particle(canvas, p, cam_x, cam_y):
    x = p.x - cam_x
    y = p.y - cam_y
    if -8 <= x <= SCREEN_W + 8 and -8 <= y <= SCREEN_H + 8:
        a = max(0, min(255, int(255 * p.life / p.max_life)))
        if p.kind == "spark":
            line(canvas, (x, y), (x - p.vx * 0.02, y - p.vy * 0.02), p.color, p.size)
        else:
            surf = alpha_surface((p.size + 2, p.size + 2))
            surf.fill((*p.color, a))
            canvas.blit(surf, (int(x), int(y)))
