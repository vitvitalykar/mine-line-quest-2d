# -*- coding: utf-8 -*-
"""Кузница-магазин: те же цены и реплики, что в оригинале."""
from __future__ import annotations

import pygame

from . import ui
from .config import SHOP_ITEMS, SCREEN_W

ITEM_EFFECT = {
    "1": ("pickaxe_type", "stone"),
    "2": ("sword_type", "stone"),
    "3": ("pickaxe_type", "iron"),
    "4": ("sword_type", "iron"),
}

RES_NAMES = {"wood": "дерево", "stones": "камни", "iron": "железо"}


class Shop:
    def __init__(self, game):
        self.game = game
        self.index = 0
        self.message = "Что тебе нужно, путник?"
        self.color = (236, 224, 190)

    # ------------------------------------------------------------------
    def _item(self, index=None):
        return SHOP_ITEMS[self.index if index is None else index]

    def _owned(self, item_key):
        field, value = ITEM_EFFECT[item_key]
        return getattr(self.game.player, field) == value

    def _cost_text(self, item):
        parts = []
        for key, value in item["cost"].items():
            parts.append(f"{value} {RES_NAMES.get(key, key)}")
        return " + ".join(parts)

    def _can_afford(self, item):
        p = self.game.player
        return all(getattr(p, key, 0) >= value for key, value in item["cost"].items())

    def buy(self, index=None):
        item = self._item(index)
        if self._owned(item["key"]):
            self.message = "У тебя уже есть эта вещь."
            self.color = (200, 190, 150)
            self.game.sfx("deny")
            return
        if not self._can_afford(item):
            self.message = item["fail"]
            self.color = (238, 122, 110)
            self.game.sfx("deny")
            return
        p = self.game.player
        for key, value in item["cost"].items():
            setattr(p, key, getattr(p, key, 0) - value)
        field, value = ITEM_EFFECT[item["key"]]
        setattr(p, field, value)
        self.message = item["ok"]
        self.color = (150, 236, 156)
        self.game.sfx("forge")
        self.game.particles.sparks(SCREEN_W // 2, 120, (255, 210, 110), count=20)

    # ------------------------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_ESCAPE:
            self.game.close_shop()
            return True
        if event.key in (pygame.K_UP, pygame.K_w, pygame.K_a, pygame.K_LEFT):
            self.index = (self.index - 1) % len(SHOP_ITEMS)
            self.game.sfx("blip")
        elif event.key in (pygame.K_DOWN, pygame.K_s, pygame.K_d, pygame.K_RIGHT):
            self.index = (self.index + 1) % len(SHOP_ITEMS)
            self.game.sfx("blip")
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self.index = event.key - pygame.K_1
            self.buy()
        elif event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
            self.buy()
        return True

    # ------------------------------------------------------------------
    def draw(self, canvas):
        x, y, w, h = 34, 30, SCREEN_W - 68, 204
        ui.panel(canvas, (x, y, w, h), bg=(24, 20, 30), border=(198, 150, 82), alpha=244)
        ui.text(canvas, "КУЗНИЦА ПУСТЫНИ", x + w // 2, y + 8,
                (255, 218, 132), 11, True, center=True)
        ui.text(canvas, "Торговец: «Выбирай, путник, но ресурсы не забудь!»",
                x + w // 2, y + 23, (176, 166, 148), 7, center=True)

        row_y = y + 40
        for i, item in enumerate(SHOP_ITEMS):
            selected = i == self.index
            row = (x + 10, row_y + i * 30, w - 20, 27)
            if selected:
                ui.panel(canvas, row, bg=(76, 58, 36), border=(246, 202, 110), alpha=255)
            else:
                ui.panel(canvas, row, bg=(38, 34, 44), border=(74, 68, 84), alpha=255)
            ui.text(canvas, f"{item['key']}. {item['name']}", row[0] + 8, row[1] + 4,
                    (252, 238, 200) if selected else (214, 208, 194), 8, True)
            ui.text(canvas, self._cost_text(item), row[0] + 8, row[1] + 15,
                    (188, 176, 150), 7)
            if self._owned(item["key"]):
                ui.text(canvas, "есть", row[0] + row[2] - 8, row[1] + 9,
                        (140, 226, 150), 7, right=True)
            else:
                ui.text(canvas, "купить", row[0] + row[2] - 8, row[1] + 9,
                        (250, 206, 120) if selected else (150, 142, 130), 7, right=True)

        msg_y = y + 164
        ui.panel(canvas, (x + 10, msg_y, w - 20, 18), bg=(14, 12, 20),
                 border=(70, 62, 80), alpha=255)
        ui.text(canvas, self.message, x + w // 2, msg_y + 4,
                self.color, 8, True, center=True)

        p = self.game.player
        res_y = y + h - 13
        rx = x + 14
        ui.icon_wood(canvas, rx, res_y)
        rx += ui.text(canvas, str(p.wood), rx + 12, res_y - 1, (206, 190, 164), 8) + 24
        ui.icon_stone(canvas, rx, res_y)
        rx += ui.text(canvas, str(p.stones), rx + 12, res_y - 1, (206, 190, 164), 8) + 24
        ui.icon_iron(canvas, rx, res_y)
        rx += ui.text(canvas, str(p.iron), rx + 12, res_y - 1, (206, 190, 164), 8) + 24
        ui.icon_coin(canvas, rx, res_y)
        ui.text(canvas, str(p.money), rx + 12, res_y - 1, (250, 214, 120), 8)
        ui.text(canvas, "Esc — выйти", x + w - 12, res_y - 1, (130, 124, 118), 7,
                right=True)
