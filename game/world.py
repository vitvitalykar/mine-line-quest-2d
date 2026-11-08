# -*- coding: utf-8 -*-
"""Мир уровня: тайлы, декорации, объекты и коллизии."""
from __future__ import annotations

import math
import random

import pygame

from . import assets, ui
from .config import SCREEN_H, SCREEN_W, TILE, LEVEL_INFO
from .entities import create_entity, EndingSignEntity, SignEntity, WiseOakEntity
from .particles import Particle


class World:
    def __init__(self, game, level):
        self.game = game
        self.level = level
        self.level_id = level.id
        self.entities = [create_entity(game, spec) for spec in level.entities]
        self.entities = [e for e in self.entities if not (e.kind == "wall" and level.id != "8")]
        self.tile_rects = self._build_tile_rects()
        self._ambient = 0.0
        self._veil_rock = assets.alpha_surface((TILE, TILE))
        self._veil_rock.fill((8, 8, 18, 64))
        self._veil_struct = assets.alpha_surface((TILE, TILE))
        self._veil_struct.fill((8, 8, 18, 34))
        self._add_special()

    # ------------------------------------------------------------------
    # Построение
    # ------------------------------------------------------------------
    def _build_tile_rects(self):
        rects = []
        for row in range(self.level.height):
            col = 0
            while col < self.level.width:
                if self.level.solid[row][col]:
                    start = col
                    while col < self.level.width and self.level.solid[row][col]:
                        col += 1
                    rects.append(pygame.Rect(start * TILE, row * TILE,
                                             (col - start) * TILE, TILE))
                else:
                    col += 1
        return rects

    def _add_special(self):
        lid = self.level_id
        ground = self.level.floor_y
        if lid == "2":
            self.entities.append(WiseOakEntity(self.game, 150, ground))
        elif lid == "3":
            self.entities.append(SignEntity(
                self.game, 1460, ground, "ШАХТА",
                ["Вход в старую шахту. Спуск ведёт в пещеру руды."],
            ))
        elif lid == "7":
            # вывеска кузницы
            self.entities.append(SignEntity(
                self.game, 1536, ground, "",
                [LEVEL_INFO["7"]["story"], LEVEL_INFO["7"].get("shortcut", "")],
            ))
        elif lid == "8":
            self.entities.append(SignEntity(
                self.game, 620, ground, "ПИРС",
                ["Старый пирс. Лодка ждёт у края доски."],
            ))
        elif lid == "9":
            self.entities.append(SignEntity(
                self.game, 520, ground, "Табличка",
                ["ЭТО НЕ КОНЕЦ ИГРЫ И ЭТО МОРЕ"], big=True,
            ))
        elif lid == "10":
            self.entities.append(SignEntity(
                self.game, 320, ground, "Это пирс",
                ["Это пирс. Отсюда начинается путь к логову короля-гоблина."],
            ))
            self.entities.append(SignEntity(
                self.game, 34, ground, "← к морю",
                ["Лодка у пирса. Иди налево, чтобы вернуться в море."],
            ))
        elif lid == "11":
            self.entities.append(SignEntity(
                self.game, 60, ground, "АРЕНА",
                ["Арена короля-гоблина. Налево — отступление, направо — только после победы."],
            ))
        elif lid == "12":
            self.entities.append(EndingSignEntity(self.game, 840, ground))

    # ------------------------------------------------------------------
    # Камера
    # ------------------------------------------------------------------
    @property
    def camera_y(self):
        # Пол всегда у нижнего края экрана: так короткие уровни выглядят
        # как настоящие платформенные сцены, а не «висят» в пустоте.
        return self.level.floor_y - (SCREEN_H - TILE)

    def camera_x(self, player):
        target = player.rect.centerx - SCREEN_W / 2
        max_x = max(0, self.level.pixel_width - SCREEN_W)
        return max(0.0, min(float(max_x), target))

    # ------------------------------------------------------------------
    # Коллизии
    # ------------------------------------------------------------------
    def solid_rects(self, area: pygame.Rect):
        expanded = area.inflate(48, 48)
        result = [r for r in self.tile_rects if r.colliderect(expanded)]
        for e in self.entities:
            if getattr(e, "solid", False) and e.solid_rect is not None and not e.used:
                if e.solid_rect.colliderect(expanded):
                    result.append(e.solid_rect)
        return result

    # ------------------------------------------------------------------
    # Взаимодействие
    # ------------------------------------------------------------------
    def find_interactable(self, player):
        best = None
        best_dist = 1e9
        px, py = player.rect.center
        for e in self.entities:
            if not e.prompt():
                continue
            if hasattr(e, "interact") and e.interact.colliderect(player.rect.inflate(28, 28)):
                ex, ey = e.interact.center
                d = (ex - px) ** 2 + (ey - py) ** 2
                if d < best_dist:
                    best_dist = d
                    best = e
        return best

    # ------------------------------------------------------------------
    # Обновление / фон
    # ------------------------------------------------------------------
    def update(self, dt, cam_x, cam_y, player):
        for e in self.entities:
            e.update(dt)
        self._ambient -= dt
        if self._ambient <= 0:
            self._ambient = random.uniform(0.05, 0.16)
            self._spawn_ambient(cam_x, cam_y, player)

    def _spawn_ambient(self, cam_x, cam_y, player):
        theme = self.level.theme
        x = cam_x + random.uniform(-20, SCREEN_W + 20)
        y = cam_y + random.uniform(40, SCREEN_H)
        if theme == "forest":
            self.game.particles.add(Particle(
                x, y, random.uniform(-8, 8), random.uniform(-14, -4),
                random.uniform(1.4, 3.0), (208, 240, 140), 1, "dot", 0))
        elif theme == "cave":
            self.game.particles.add(Particle(
                x, y, random.uniform(-6, 6), random.uniform(-8, 4),
                random.uniform(1.0, 2.6), (120, 150, 190), 1, "dot", 2))
        elif theme == "desert":
            self.game.particles.add(Particle(
                x, y, random.uniform(-22, -6), random.uniform(-4, 4),
                random.uniform(0.8, 1.8), (246, 220, 170), 1, "dot", 0))
        elif theme in ("pier", "sea"):
            self.game.particles.add(Particle(
                x, y, random.uniform(-8, 8), random.uniform(-20, -8),
                random.uniform(0.6, 1.4), (190, 232, 255), 1, "dot", 120))
        elif theme == "arena":
            self.game.particles.add(Particle(
                x, y, random.uniform(-6, 6), random.uniform(-28, -12),
                random.uniform(0.8, 1.8), (240, 110, 60), 1, "dot", -10))

    # ------------------------------------------------------------------
    # Отрисовка
    # ------------------------------------------------------------------
    def draw_background(self, canvas, t, cam_x, cam_y):
        assets.draw_background(canvas, self.level.theme, t, cam_x, cam_y,
                              self.level.pixel_width, self.level.pixel_height)

    def draw_tiles(self, canvas, t, cam_x, cam_y):
        level = self.level
        first_col = max(0, int(cam_x // TILE) - 1)
        last_col = min(level.width, int((cam_x + SCREEN_W) // TILE) + 2)
        first_row = max(0, int(cam_y // TILE) - 1)
        last_row = min(level.height, int((cam_y + SCREEN_H) // TILE) + 2)
        for row in range(first_row, last_row):
            for col in range(first_col, last_col):
                kind = level.tiles[row][col]
                if kind == "empty":
                    continue
                sx = col * TILE - cam_x
                sy = row * TILE - cam_y
                above = level.tiles[row - 1][col] if row > 0 else "empty"
                assets.draw_tile(canvas, kind, level.theme, sx, sy, col, row, t,
                                 top_open=(above != kind))
                if not level.solid[row][col]:
                    # декоративные стены/потолки чуть притемняем — герой
                    # проходит перед ними, как в 2.5D
                    canvas.blit(self._veil_rock if kind == "rock" else self._veil_struct,
                                (int(sx), int(sy)))

        # «юбка» под полом, чтобы короткие уровни не висели в небе
        if level.theme not in ("pier", "sea"):
            floor_screen = level.floor_y - cam_y
            if floor_screen < SCREEN_H:
                for col in range(first_col, last_col):
                    sx = col * TILE - cam_x
                    assets.draw_ground_skirt(canvas, level.theme, sx, floor_screen + TILE,
                                             SCREEN_H)
        else:
            floor_screen = level.floor_y - cam_y
            bottom = min(SCREEN_H, 142)
            if floor_screen + TILE < bottom:
                for col in range(first_col, last_col):
                    sx = col * TILE - cam_x
                    assets.rect(canvas, sx, floor_screen + TILE, TILE,
                                bottom - (floor_screen + TILE), (26, 67, 122))

    def draw_decor(self, canvas, t, cam_x, cam_y):
        lid = self.level_id
        ground = self.level.floor_y - cam_y
        if lid == "3":
            x = 1500 - cam_x
            ui.text(canvas, "↓ ШАХТА", x, ground - 82, (240, 220, 160), 8, True, center=True)
            assets.draw_crystal(canvas, 1350 - cam_x, ground, t)
        elif lid == "4":
            for x in (120, 330, 590, 780, 900):
                assets.draw_torch(canvas, x - cam_x, ground - 8, t)
            for x in (210, 470, 720):
                assets.draw_crystal(canvas, x - cam_x, ground, t)
            for x in (180, 380, 620, 840):
                assets.draw_stalactite(canvas, x - cam_x, ground - 108, 18)
        elif lid == "5":
            for x in (110, 370, 610, 730):
                assets.draw_torch(canvas, x - cam_x, ground - 8, t)
            for x in (250, 520):
                assets.draw_crystal(canvas, x - cam_x, ground, t, (120, 180, 240))
        elif lid == "6":
            for x in (180, 560, 980, 1380, 1560):
                assets.draw_torch(canvas, x - cam_x, ground - 8, t)
            for x in (320, 760, 1200):
                assets.draw_crystal(canvas, x - cam_x, ground, t, (96, 220, 230))
        elif lid == "7":
            self._draw_forge(canvas, t, cam_x, ground)
        elif lid == "8":
            self._draw_pier(canvas, t, cam_x, ground)
        elif lid == "10":
            self._draw_arrival_pier(canvas, t, cam_x, ground)
        elif lid == "11":
            self._draw_arena(canvas, t, cam_x, ground)
        elif lid == "2":
            # пара светлячков у дуба
            for i in range(4):
                ex = 90 + i * 34 - cam_x + math.sin(t + i) * 8
                ey = ground - 40 - (i % 3) * 24
                canvas.set_at((int(ex), int(ey)), (220, 255, 150))

    def _draw_forge(self, canvas, t, cam_x, ground):
        for x in (1240, 1290, 1350):
            assets.draw_barrel(canvas, x - cam_x, ground)
        assets.draw_crate(canvas, 1400 - cam_x, ground)
        assets.draw_anvil(canvas, 1440 - cam_x, ground, t)
        assets.draw_crate(canvas, 1480 - cam_x, ground)
        assets.draw_torch(canvas, 1420 - cam_x, ground - 6, t)
        x = 1536 - cam_x
        ui.panel(canvas, (x - 56, ground - 86, 112, 16), bg=(78, 50, 30),
                 border=(38, 24, 16), alpha=245)
        ui.text(canvas, "КУЗНИЦА ПУСТЫНИ", x, ground - 83, (248, 224, 168), 7, True, center=True)

    def _draw_pier(self, canvas, t, cam_x, ground):
        for x in (180, 230):
            assets.draw_barrel(canvas, x - cam_x, ground)
        assets.draw_crate(canvas, 280 - cam_x, ground)
        # чайки
        for i in range(3):
            bx = 300 + i * 70 - cam_x + math.sin(t * 0.8 + i) * 12
            by = ground - 90 - i * 12
            assets.line(canvas, (bx - 4, by), (bx, by - 3), (60, 70, 90), 1)
            assets.line(canvas, (bx, by - 3), (bx + 4, by), (60, 70, 90), 1)
        # столбик у лодки
        assets.rect(canvas, 1130 - cam_x, ground - 34, 6, 34, (86, 54, 30))
        assets.rect(canvas, 1128 - cam_x, ground - 38, 10, 6, (142, 92, 49))

    def _draw_arrival_pier(self, canvas, t, cam_x, ground):
        assets.draw_barrel(canvas, 120 - cam_x, ground)
        assets.draw_crate(canvas, 160 - cam_x, ground)
        assets.draw_crate(canvas, 380 - cam_x, ground)
        # маленькая лодка у левого края (обратный путь)
        assets.draw_boat(canvas, 26 - cam_x, ground + 6, t)
        for i in range(3):
            bx = 600 + i * 90 - cam_x + math.sin(t * 0.9 + i) * 10
            by = ground - 70 - i * 8
            assets.line(canvas, (bx - 4, by), (bx, by - 3), (60, 70, 90), 1)
            assets.line(canvas, (bx, by - 3), (bx + 4, by), (60, 70, 90), 1)

    def _draw_arena(self, canvas, t, cam_x, ground):
        for x in (110, 270, 430, 600, 760, 920, 1080, 1240):
            assets.draw_torch(canvas, x - cam_x, ground - 8, t)
        # кости на арене
        for x, y in ((190, -6), (250, -4), (420, -7), (560, -5), (1080, -6)):
            bx = x - cam_x
            by = ground + y
            assets.line(canvas, (bx, by), (bx + 14, by - 4), (222, 218, 196), 2)
            assets.line(canvas, (bx + 14, by - 4), (bx + 18, by + 2), (222, 218, 196), 2)
            assets.circle(canvas, bx + 2, by - 1, 2, (232, 228, 208))
        # трон за боссом
        tx = 832 - cam_x
        assets.rect(canvas, tx - 44, ground - 78, 88, 78, (56, 30, 40))
        assets.rect(canvas, tx - 50, ground - 84, 100, 10, (82, 44, 52))
        assets.rect(canvas, tx - 36, ground - 70, 72, 6, (98, 54, 60))

    def draw_entities(self, canvas, t, cam_x, cam_y):
        for e in sorted(self.entities, key=lambda e: getattr(e, "bottom", 0)):
            if e is self.game.world_player_entity:
                continue
            e.draw(canvas, cam_x, cam_y, t)
