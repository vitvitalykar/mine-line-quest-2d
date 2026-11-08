# -*- coding: utf-8 -*-
"""Игровые объекты на уровнях: деревья, руда, камни, лодка, торговец, босс."""
from __future__ import annotations

import math
import random

import pygame

from . import assets, ui
from .config import ORE_LOCKED, DRAGON_YES, DRAGON_NO, LEVEL_INFO
from .legacy import EntitySpec, TILE


class Entity:
    kind = "entity"
    solid = False

    def __init__(self, game, spec: EntitySpec):
        self.game = game
        self.spec = spec
        self.level_id = game.level_id
        self.uid = f"{self.level_id}:{spec.uid}"
        self.x = (spec.col + spec.legacy_w / 2) * TILE
        self.bottom = spec.feet_row * TILE
        self.w = spec.legacy_w * TILE
        self.h = spec.legacy_h * TILE
        self.interact = pygame.Rect(int(self.x - 28), int(self.bottom - 56), 56, 56)
        self.solid_rect = None

    @property
    def used(self):
        return self.game.is_used(self.uid)

    def mark_used(self):
        self.game.mark_used(self.uid)

    def update(self, dt):
        pass

    def prompt(self):
        return ""

    def activate(self):
        pass

    def draw(self, canvas, cam_x, cam_y, t):
        pass

    def _on_screen(self, cam_x, cam_y, pad=120):
        sx = self.x - cam_x
        sy = self.bottom - cam_y
        return -pad <= sx <= 480 + pad and -pad <= sy <= 270 + pad


class TreeEntity(Entity):
    kind = "tree"

    def prompt(self):
        return "E — срубить дерево" if not self.used else ""

    def activate(self):
        if self.used:
            return
        self.mark_used()
        self.game.player.inventory["wood"] += 2
        self.game.particles.burst(self.x, self.bottom - 30, (142, 92, 49), count=12, spread=110)
        self.game.particles.burst(self.x, self.bottom - 40, (86, 168, 82), count=6, spread=80)
        self.game.toast("Дерево +2", (186, 130, 71))
        self.game.sfx("chop")

    def draw(self, canvas, cam_x, cam_y, t):
        if not self._on_screen(cam_x, cam_y):
            return
        assets.draw_tree(canvas, self.x - cam_x, self.bottom - cam_y, t,
                         broken=self.used, cave=self.game.level.theme == "cave")


class OreEntity(Entity):
    kind = "ore"

    def prompt(self):
        if self.used:
            return ""
        if self.game.player.pickaxe_type in ("stone", "iron"):
            return "E — добыть руду"
        return "E — руда (нужна кирка)"

    def activate(self):
        if self.used:
            return
        if self.game.player.pickaxe_type not in ("stone", "iron"):
            self.game.toast(ORE_LOCKED, (240, 120, 110))
            self.game.sfx("lock")
            self.game.particles.sparks(self.x, self.bottom - 18, (180, 180, 190), count=6)
            return
        self.mark_used()
        iron = random.randrange(2, 6)
        stones = random.randrange(0, 4)
        self.game.player.inventory["iron"] += iron
        self.game.player.inventory["stones"] += stones
        self.game.particles.sparks(self.x, self.bottom - 16, (110, 220, 240), count=14)
        self.game.particles.burst(self.x, self.bottom - 12, (110, 140, 160), count=8, spread=90)
        msg = f"Железо +{iron}"
        if stones:
            msg += f", камни +{stones}"
        self.game.toast(msg, (120, 220, 240))
        self.game.sfx("mine")

    def draw(self, canvas, cam_x, cam_y, t):
        if self.used or not self._on_screen(cam_x, cam_y):
            return
        assets.draw_ore(canvas, self.x - cam_x, self.bottom - cam_y, t)


class StoneEntity(Entity):
    kind = "stone"
    solid = True

    def __init__(self, game, spec):
        super().__init__(game, spec)
        self.solid_rect = pygame.Rect(int(self.x - 13), int(self.bottom - 30), 26, 30)
        self.interact = pygame.Rect(int(self.x - 30), int(self.bottom - 54), 60, 56)

    def prompt(self):
        return "E — сломать камень рукой" if not self.used else ""

    def activate(self):
        if self.used:
            return
        self.mark_used()
        self.game.player.inventory["stones"] += 2
        self.game.particles.burst(self.x, self.bottom - 18, (136, 138, 154), count=14, spread=120)
        self.game.particles.burst(self.x, self.bottom - 10, (100, 102, 118), count=6, spread=80)
        self.game.toast("Камни +2", (172, 174, 188))
        self.game.sfx("chop")

    def draw(self, canvas, cam_x, cam_y, t):
        if self.used or not self._on_screen(cam_x, cam_y):
            return
        assets.draw_stone(canvas, self.x - cam_x, self.bottom - cam_y, t)


class BoatEntity(Entity):
    kind = "boat"

    def __init__(self, game, spec):
        super().__init__(game, spec)
        self.bottom += 4
        self.interact = pygame.Rect(int(self.x - 38), int(self.bottom - 50), 76, 58)

    def prompt(self):
        return "E — сесть в лодку"

    def activate(self):
        self.game.board_boat()

    def draw(self, canvas, cam_x, cam_y, t):
        if not self._on_screen(cam_x, cam_y):
            return
        assets.draw_boat(canvas, self.x - cam_x, self.bottom - cam_y, t)


class TraderEntity(Entity):
    kind = "trader"

    def __init__(self, game, spec):
        super().__init__(game, spec)
        self.interact = pygame.Rect(int(self.x - 34), int(self.bottom - 52), 68, 56)

    def prompt(self):
        return "E — кузница пустыни"

    def activate(self):
        self.game.open_shop()

    def draw(self, canvas, cam_x, cam_y, t):
        if not self._on_screen(cam_x, cam_y):
            return
        assets.draw_trader(canvas, self.x - cam_x, self.bottom - cam_y, t)


class DragonEntity(Entity):
    kind = "dragon"

    def __init__(self, game, spec):
        super().__init__(game, spec)
        self.bottom = spec.row * TILE + 32
        self.interact = pygame.Rect(int(self.x - 34), int(self.bottom - 48), 68, 56)

    def prompt(self):
        if self.game.dragon_following:
            return ""
        return "E — поговорить с Джеком"

    def activate(self):
        if self.game.dragon_following:
            return
        lines = []
        for speaker, text in [
            ("Джек", "Привет, {name}!"),
            ("{name}", "Привет, Дракон Джек! Хочешь пойти со мной?"),
            ("Джек", "..."),
            ("Джек", "Да, хочу!"),
        ]:
            lines.append((speaker.format(name=self.game.player.name),
                          text.format(name=self.game.player.name)))
        self.game.start_dialogue(
            lines,
            choice=("Принять Джека в команду?", "Да", "Нет"),
            on_choice=self._answer,
        )

    def _answer(self, yes: bool):
        if yes:
            self.game.dragon_following = True
            self.game.toast(DRAGON_YES, (120, 220, 150))
            self.game.sfx("accept")
        else:
            self.game.toast(DRAGON_NO, (210, 180, 120))
            self.game.sfx("deny")

    def draw(self, canvas, cam_x, cam_y, t):
        if self.game.dragon_following or not self._on_screen(cam_x, cam_y):
            return
        bob = math.sin(t * 3.2) * 4
        assets.draw_dragon(canvas, self.x - cam_x, self.bottom - cam_y + bob, t, facing=-1)


class BossEntity(Entity):
    kind = "boss"

    def __init__(self, game, spec):
        super().__init__(game, spec)
        self.interact = pygame.Rect(int(self.x - 70), int(self.bottom - 150), 140, 155)

    def prompt(self):
        if self.game.boss_defeated:
            return ""
        if not self.game.boss_intro_seen:
            return "E — подойти к королю-гоблину"
        return "E — атака,  Z — защита"

    def activate(self):
        self.game.boss_player_action("attack")

    def draw(self, canvas, cam_x, cam_y, t):
        if not self._on_screen(cam_x, cam_y, pad=220):
            return
        assets.draw_boss(
            canvas,
            self.x - cam_x,
            self.bottom - cam_y,
            t,
            self.game.boss_hp,
            self.game.boss_max_hp,
            defeated=self.game.boss_defeated,
            windup=self.game.boss_windup,
            flash=self.game.boss_flash,
        )


class MineEntity(Entity):
    kind = "mine"

    def __init__(self, game, spec):
        super().__init__(game, spec)
        self.interact = pygame.Rect(int(self.x - 80), int(self.bottom - 80), 160, 90)

    def prompt(self):
        return "E — войти в шахту"

    def activate(self):
        self.game.enter_level("4")

    def draw(self, canvas, cam_x, cam_y, t):
        if not self._on_screen(cam_x, cam_y):
            return
        assets.draw_mine(canvas, self.x - cam_x, self.bottom - cam_y, t)


class WallEntity(Entity):
    kind = "wall"

    def draw(self, canvas, cam_x, cam_y, t):
        if self.level_id != "8":
            return
        if not self._on_screen(cam_x, cam_y):
            return
        x = int(self.x - cam_x)
        y = int(self.bottom - cam_y)
        # деревянный забор в конце пирса
        assets.rect(canvas, x - 9, y - 42, 18, 42, (86, 54, 30))
        assets.rect(canvas, x - 7, y - 42, 4, 42, (142, 92, 49))
        assets.rect(canvas, x + 3, y - 42, 4, 42, (142, 92, 49))
        assets.rect(canvas, x - 12, y - 34, 24, 4, (142, 92, 49))
        assets.rect(canvas, x - 12, y - 18, 24, 4, (142, 92, 49))


class WiseOakEntity(Entity):
    kind = "oak"

    def __init__(self, game, x, bottom):
        self.game = game
        self.level_id = game.level_id
        self.uid = f"{self.level_id}:oak"
        self.x = x
        self.bottom = bottom
        self.w = 150
        self.h = 176
        self.interact = pygame.Rect(int(x - 70), int(bottom - 190), 140, 190)
        self.solid_rect = None

    def prompt(self):
        return "E — послушать мудрый дуб"

    def activate(self):
        oak = LEVEL_INFO["2"]["oak"]
        self.game.start_dialogue([(speaker, line) for speaker, line in oak])

    def draw(self, canvas, cam_x, cam_y, t):
        assets.draw_tree(canvas, self.x - 75 - cam_x, self.bottom - cam_y, t, wise=True)


class SignEntity(Entity):
    kind = "sign"

    def __init__(self, game, x, bottom, title, lines, draw_sign=True, big=False):
        self.game = game
        self.level_id = game.level_id
        self.uid = f"{self.level_id}:sign:{int(x)}:{int(bottom)}"
        self.x = x
        self.bottom = bottom
        self.title = title
        self.lines = lines
        self.big = big
        self.draw_sign = draw_sign
        self.interact = pygame.Rect(int(x - 70), int(bottom - 80), 140, 90)
        self.solid_rect = None

    def prompt(self):
        return "E — прочитать"

    def activate(self):
        self.game.start_dialogue([(self.title, line) for line in self.lines])

    def draw(self, canvas, cam_x, cam_y, t):
        x = int(self.x - cam_x)
        y = int(self.bottom - cam_y)
        if self.big:
            w = 190
            h = 60
            ui.panel(canvas, (x - w // 2, y - 78, w, h), bg=(92, 60, 38),
                     border=(46, 30, 20), alpha=245)
            ui.text(canvas, "ЭТО НЕ КОНЕЦ ИГРЫ", x, y - 68,
                    (245, 226, 170), 8, True, center=True)
            ui.text(canvas, "И ЭТО МОРЕ", x, y - 56, (245, 226, 170), 9, True, center=True)
            assets.rect(canvas, x - 8, y - 18, 6, 20, (78, 50, 30))
            assets.rect(canvas, x + 2, y - 18, 6, 20, (78, 50, 30))
            return
        if self.draw_sign:
            assets.draw_sign(canvas, x, y, t)
        if self.title:
            label = self.title
            ui.text(canvas, label, x, y - 44, (245, 234, 196), 7, True, center=True)


class EndingSignEntity(Entity):
    """Финальный знак на 12-м уровне: открывает экран победы."""

    kind = "ending"

    def __init__(self, game, x, bottom):
        self.game = game
        self.level_id = game.level_id
        self.uid = f"{self.level_id}:ending"
        self.x = x
        self.bottom = bottom
        self.w = 120
        self.h = 100
        self.interact = pygame.Rect(int(x - 80), int(bottom - 110), 160, 120)
        self.solid_rect = None

    def prompt(self):
        return "E — завершить историю"

    def activate(self):
        self.game.show_victory()

    def draw(self, canvas, cam_x, cam_y, t):
        if not self._on_screen(cam_x, cam_y):
            return
        x = int(self.x - cam_x)
        y = int(self.bottom - cam_y)
        # каменная арка
        assets.rect(canvas, x - 44, y - 74, 12, 74, (96, 88, 108))
        assets.rect(canvas, x + 32, y - 74, 12, 74, (96, 88, 108))
        assets.rect(canvas, x - 52, y - 86, 104, 14, (122, 112, 132))
        ui.panel(canvas, (x - 42, y - 70, 84, 34), bg=(62, 42, 32),
                 border=(210, 176, 112), alpha=248)
        ui.text(canvas, "КОНЕЦ", x, y - 64, (255, 232, 150), 13, True,
                center=True)
        ui.text(canvas, "истории", x, y - 49, (226, 206, 170), 7, center=True)
        for i in range(3):
            spin = math.sin(t * 2.2 + i * 2.1)
            col = (255, 220 + int(20 * spin), 120)
            assets.circle(canvas, x - 30 + i * 30, y - 94 + int(spin * 4), 2, col)


def create_entity(game, spec: EntitySpec):
    table = {
        "tree": TreeEntity,
        "ore": OreEntity,
        "stone": StoneEntity,
        "boat": BoatEntity,
        "trader": TraderEntity,
        "dragon": DragonEntity,
        "boss": BossEntity,
        "mine": MineEntity,
        "wall": WallEntity,
    }
    cls = table.get(spec.kind, Entity)
    return cls(game, spec)
