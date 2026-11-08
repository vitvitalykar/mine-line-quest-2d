# -*- coding: utf-8 -*-
"""Герой Вадик: физика платформера, снаряжение и лодка."""
from __future__ import annotations

import pygame

from . import assets
from .config import GRAVITY, PLAYER_H, PLAYER_JUMP, PLAYER_SPEED, PLAYER_W, TILE


class Player:
    def __init__(self, game):
        self.game = game
        self.rect = pygame.Rect(0, 0, PLAYER_W, PLAYER_H)
        self.vx = 0.0
        self.vy = 0.0
        self.facing = 1
        self.on_ground = False
        self.state = "idle"
        self.riding_boat = False
        self.attack_timer = 0.0
        self.defend_timer = 0.0
        self.hurt_timer = 0.0
        self.step_timer = 0.0
        self.reset_inventory()

    # ------------------------------------------------------------------
    def reset_inventory(self):
        self.wood = 0
        self.stones = 0
        self.iron = 0
        self.money = 100
        self.pickaxe_type = None      # None | stone | iron
        self.sword_type = None        # None | stone | iron
        self.hp = 3
        self.max_hp = 3
        self.name = "Вадик"

    @property
    def inventory(self):
        """Совместимость с сущностями: обращаются к player.inventory["wood"]."""
        return _InventoryView(self)

    # ------------------------------------------------------------------
    def place(self, x, bottom):
        self.rect.x = int(x)
        self.rect.bottom = int(bottom)
        self.vx = self.vy = 0.0
        self.on_ground = False

    def update(self, dt, axis, jump_pressed, jump_held):
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.defend_timer = max(0.0, self.defend_timer - dt)
        self.hurt_timer = max(0.0, self.hurt_timer - dt)

        if self.riding_boat:
            self._update_boat(dt, axis)
            return

        # --- горизонталь ---
        speed = PLAYER_SPEED
        self.vx = axis * speed
        if axis:
            self.facing = 1 if axis > 0 else -1
            self.step_timer += dt
            if self.step_timer > 0.28 and self.on_ground:
                self.step_timer = 0.0
                self.game.sfx("step")
        else:
            self.step_timer = 0.0

        self.rect.x += int(round(self.vx * dt))
        self._resolve_horizontal()

        # --- прыжок / гравитация ---
        if jump_pressed and self.on_ground:
            self.vy = -PLAYER_JUMP
            self.on_ground = False
            self.game.sfx("jump")
        if not jump_held and self.vy < -90:
            self.vy += GRAVITY * 1.6 * dt

        self.vy = min(720.0, self.vy + GRAVITY * dt)
        self.rect.y += int(round(self.vy * dt))
        self._resolve_vertical()

        # --- границы карты ---
        self._clamp_x()

        # --- состояние ---
        if not self.on_ground:
            self.state = "jump"
        elif abs(self.vx) > 6:
            self.state = "run"
        else:
            self.state = "idle"

        # --- падение в воду/пропасть ---
        if self.rect.top > self.game.level.pixel_height + 64:
            self.game.player_fell()

    def _update_boat(self, dt, axis):
        self.vx = axis * PLAYER_SPEED * 1.25
        if axis:
            self.facing = 1 if axis > 0 else -1
        self.rect.x += int(round(self.vx * dt))
        self._clamp_x()
        self.rect.y = self.game.level.floor_y - PLAYER_H
        self.vy = 0.0
        self.on_ground = True
        self.state = "walk" if axis else "idle"

    def _clamp_x(self):
        level = self.game.level
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > level.pixel_width:
            self.rect.right = level.pixel_width

    def _resolve_horizontal(self):
        for r in self.game.world.solid_rects(self.rect):
            if not self.rect.colliderect(r):
                continue
            if self.vx > 0:
                self.rect.right = r.left
            elif self.vx < 0:
                self.rect.left = r.right

    def _resolve_vertical(self):
        self.on_ground = False
        for r in self.game.world.solid_rects(self.rect):
            if not self.rect.colliderect(r):
                continue
            if self.vy > 0:
                self.rect.bottom = r.top
                self.on_ground = True
                self.vy = 0.0
            elif self.vy < 0:
                self.rect.top = r.bottom
                self.vy = 0.0

    # ------------------------------------------------------------------
    def equipment_sprite(self):
        if self.sword_type:
            kind = "iron_sword" if self.sword_type == "iron" else "stone_sword"
        elif self.pickaxe_type:
            kind = "iron_pick" if self.pickaxe_type == "iron" else "stone_pick"
        else:
            kind = None
        # в бою с боссом меч важнее кирки
        if self.game.level_id == "11" and self.sword_type:
            kind = "iron_sword" if self.sword_type == "iron" else "stone_sword"
        return kind

    @property
    def feet(self):
        return self.rect.bottom

    @property
    def center(self):
        return self.rect.center

    def draw(self, canvas, cam_x, cam_y, t):
        if self.riding_boat:
            assets.draw_player(canvas, self.rect.move(-cam_x, -cam_y),
                               self.facing, self.state, self.equipment_sprite(), t,
                               attack=self.attack_timer, defend=self.defend_timer,
                               hurt=self.hurt_timer, riding_boat=True)
            return
        assets.draw_shadow(canvas, self.rect.centerx - cam_x,
                           self.rect.bottom - cam_y + 1, 18)
        assets.draw_player(canvas, self.rect.move(-cam_x, -cam_y),
                           self.facing, self.state, self.equipment_sprite(), t,
                           attack=self.attack_timer, defend=self.defend_timer,
                           hurt=self.hurt_timer)


class _InventoryView:
    """Позволяет писать player.inventory["wood"] += 2, как в старом коде."""

    def __init__(self, player):
        self._p = player

    def __getitem__(self, key):
        return getattr(self._p, key)

    def __setitem__(self, key, value):
        setattr(self._p, key, value)

    def get(self, key, default=0):
        return getattr(self._p, key, default)
