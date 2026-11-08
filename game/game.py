# -*- coding: utf-8 -*-
"""Основной игровой цикл MINE-LINE QUEST 2D."""
from __future__ import annotations

import array
import math
import random
import sys

import pygame

from . import assets, ui
from .config import (
    BOSS_ATTACK_IRON,
    BOSS_ATTACK_NO_IRON,
    BOSS_BLOCKED,
    BOSS_DEFEND,
    BOSS_HIT,
    BOSS_VICTORY,
    BOSS_WINDUP,
    CONTROLS,
    DRAGON_YES,
    FPS,
    GRAVITY,
    LEVEL_INFO,
    PLAYER_H,
    PLAYER_SPEED,
    SCALE,
    SCREEN_H,
    SCREEN_W,
    TILE,
    TITLE_LINES,
)
from .dialogue import Dialogue
from .legacy import build_levels
from .particles import Particles
from .player import Player
from .shop import Shop
from .world import World


class Game:
    def __init__(self, headless: bool = False):
        pygame.mixer.pre_init(22050, -16, 1, 256)
        pygame.init()
        try:
            pygame.mixer.init(22050, -16, 1, 256)
        except Exception:
            pass
        pygame.font.init()

        self.headless = headless
        self.fullscreen = False
        try:
            info = pygame.display.Info()
            fit = min((info.current_w - 80) // SCREEN_W,
                      (info.current_h - 120) // SCREEN_H)
            scale = max(1, min(SCALE, fit))
        except Exception:
            scale = SCALE
        size = (SCREEN_W * scale, SCREEN_H * scale)
        self.windowed_size = size
        flags = pygame.RESIZABLE
        self.window = pygame.display.set_mode(size, flags)
        pygame.display.set_caption("MINE-LINE QUEST — 2D pixel remake")
        self.canvas = pygame.Surface((SCREEN_W, SCREEN_H)).convert()

        self.clock = pygame.time.Clock()
        self.running = True
        self.t = 0.0
        self.state = "title"
        self.title_time = 0.0

        self.levels = build_levels(LEVEL_INFO)
        self.used: set[str] = set()
        self.particles = Particles()
        self.player = Player(self)
        self.world_player_entity = self.player
        self.level = self.levels["1"]
        self.level_id = "1"
        self.world = World(self, self.level)
        self.cam_x = 0.0
        self.cam_y = self.world.camera_y
        self.transition_lock = 0.0
        self.banner_timer = 0.0
        self.banner_text = ""
        self.banner_sub = ""
        self.hint_timer = 9.0
        self.jump_requested = False

        self.dialogue: Dialogue | None = None
        self.shop: Shop | None = None
        self.inventory_open = False
        self.paused = False

        self.dragon_following = False
        self.dragon_pos = pygame.Vector2(0, 0)
        self.boss_max_hp = 3
        self.boss_hp = 3
        self.boss_turn = 0
        self.boss_windup = False
        self.boss_flash = 0.0
        self.boss_defeated = False
        self.boss_intro_seen = False
        self.boss_intro_active = False
        self.boss_log: list[str] = []

        self.toasts: list[dict] = []
        self.victory_time = 0.0
        self.fire_timer = 0.0
        self.victory_ready = False

        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.muted = False
        self._build_sounds()

        self.enter_level("1", side=None, announce=False)
        self.state = "title"

    # ==================================================================
    # Звук
    # ==================================================================
    def _synth(self, f0, f1, ms, vol=0.18, kind="square"):
        rate = 22050
        n = max(1, int(rate * ms / 1000.0))
        data = array.array("h")
        phase = 0.0
        for i in range(n):
            f = f0 + (f1 - f0) * (i / n)
            phase += f / rate
            if kind == "square":
                s = 1.0 if phase % 1.0 < 0.5 else -1.0
            elif kind == "noise":
                s = random.uniform(-1.0, 1.0)
            else:
                s = math.sin(phase * math.tau)
            env = 1.0 - i / n
            data.append(int(max(-1.0, min(1.0, s * vol * env)) * 32767))
        return pygame.mixer.Sound(buffer=data.tobytes())

    def _build_sounds(self):
        if not pygame.mixer.get_init():
            return
        specs = {
            "chop": (170, 105, 90, 0.22, "square"),
            "mine": (620, 260, 120, 0.16, "square"),
            "pickup": (720, 960, 70, 0.16, "sine"),
            "accept": (520, 800, 170, 0.16, "sine"),
            "deny": (210, 140, 150, 0.16, "square"),
            "lock": (120, 90, 130, 0.20, "square"),
            "hit": (100, 70, 150, 0.22, "noise"),
            "block": (280, 180, 110, 0.20, "square"),
            "win": (480, 1040, 480, 0.18, "sine"),
            "jump": (360, 560, 90, 0.10, "sine"),
            "step": (95, 80, 45, 0.05, "square"),
            "forge": (720, 280, 180, 0.18, "square"),
            "blip": (920, 920, 40, 0.05, "sine"),
            "swing": (420, 220, 90, 0.12, "square"),
            "open": (420, 700, 110, 0.10, "sine"),
        }
        for name, spec in specs.items():
            try:
                self.sounds[name] = self._synth(*spec)
            except Exception:
                pass

    def sfx(self, name):
        if self.muted:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            try:
                sound.play()
            except Exception:
                pass

    def toggle_mute(self):
        self.muted = not self.muted
        if pygame.mixer.get_init():
            if self.muted:
                pygame.mixer.pause()
            else:
                pygame.mixer.unpause()
        self.toast("Звук выключен" if self.muted else "Звук включён",
                   (200, 196, 180))

    # ==================================================================
    # Уровни и переходы
    # ==================================================================
    def enter_level(self, level_id: str, side: str | None = None, announce: bool = True):
        if level_id not in self.levels:
            return
        self.level_id = level_id
        self.level = self.levels[level_id]
        self.world = World(self, self.level)
        self.world_player_entity = self.player
        p = self.player
        p.riding_boat = level_id == "9"
        if side == "left":
            x = 5 * TILE
        elif side == "right":
            x = self.level.pixel_width - 6 * TILE - p.rect.width
        else:
            x = self.level.spawn_x
        p.place(x, self.level.floor_y)
        self.transition_lock = 0.8
        self.jump_requested = False
        self.dialogue = None
        self.shop = None
        self.inventory_open = False
        self.paused = False
        self.cam_x = self.world.camera_x(p)
        self.cam_y = self.world.camera_y
        self.particles.items.clear()
        self.victory_ready = False
        if level_id == "11" and not self.boss_defeated:
            self.boss_hp = self.boss_max_hp
            self.boss_turn = 0
            self.boss_windup = False
            self.boss_log.clear()
        if announce:
            info = LEVEL_INFO.get(level_id, {})
            self.banner_text = info.get("name", "")
            self.banner_sub = info.get("story", "")
            self.banner_timer = 2.6
        if level_id == "9":
            self.toast("Лодка отчаливает. ← к пирсу · → вперёд", (170, 226, 255))
        if level_id == "12":
            self.toast("ПОБЕДА! Дойди до знака конца истории.", (255, 226, 140))

    def _check_transitions(self):
        if self.transition_lock > 0:
            return
        p = self.player
        col = p.rect.centerx // TILE
        for tr in self.level.transitions:
            if not (tr.col_start <= col <= tr.col_end):
                continue
            if tr.target == "12" and not self.boss_defeated:
                continue
            left_side = tr.col_start < self.level.width / 2
            moving = p.vx
            if left_side and moving < -1:
                self.enter_level(tr.target, side="right")
                return
            if not left_side and moving > 1:
                self.enter_level(tr.target, side="left")
                return

    def board_boat(self):
        if self.level_id != "8":
            self.toast("Лодка ждёт у пирса.", (190, 220, 235))
            return
        self.sfx("open")
        self.enter_level("9", side=None)

    def player_fell(self):
        self.sfx("lock")
        self.toast("Ты промок! Возвращаемся на берег...", (160, 210, 240))
        self.enter_level(self.level_id, side=None, announce=False)
        self.transition_lock = 1.0

    # ==================================================================
    # Общие хуки для сущностей и мира
    # ==================================================================
    def is_used(self, uid):
        return uid in self.used

    def mark_used(self, uid):
        self.used.add(uid)

    def toast(self, text, color=(236, 230, 210)):
        self.toasts.append({"text": str(text), "color": color, "life": 2.8, "max": 2.8})
        if len(self.toasts) > 4:
            self.toasts.pop(0)

    def _update_toasts(self, dt):
        for item in self.toasts:
            item["life"] -= dt
        self.toasts = [i for i in self.toasts if i["life"] > 0]

    def _fmt(self, lines):
        out = []
        for speaker, text in lines:
            try:
                speaker = str(speaker).format(name=self.player.name)
                text = str(text).format(name=self.player.name)
            except Exception:
                speaker, text = str(speaker), str(text)
            out.append((speaker, text))
        return out

    def start_dialogue(self, lines, choice=None, on_choice=None, on_close=None):
        self.dialogue = Dialogue(self, self._fmt(lines), choice, on_choice, on_close)

    def open_shop(self):
        self.shop = Shop(self)
        self.sfx("open")

    def close_shop(self):
        self.shop = None
        self.transition_lock = 0.35

    def show_victory(self):
        self.state = "victory"
        self.victory_time = 0.0
        self.sfx("win")
        self.dialogue = None
        self.shop = None
        self.inventory_open = False
        self.paused = False

    # ==================================================================
    # Босс
    # ==================================================================
    def _boss_entity(self):
        for e in self.world.entities:
            if getattr(e, "kind", "") == "boss":
                return e
        return None

    def _boss_near(self):
        boss = self._boss_entity()
        if boss is None:
            return False
        return abs(self.player.rect.centerx - boss.x) < 130

    def _start_boss_intro(self):
        if self.boss_intro_active or self.boss_intro_seen:
            return
        self.boss_intro_active = True
        intro = LEVEL_INFO["11"].get("boss_intro", [])
        self.start_dialogue(intro, on_close=self._after_boss_intro)

    def _after_boss_intro(self):
        self.boss_intro_active = False
        self.boss_intro_seen = True
        self.boss_windup = False
        self.boss_turn = 0
        self._boss_log("Бой начался! E — атака, Z — защита.")
        self.toast("Чередуй удар и защиту!", (255, 204, 120))

    def _boss_log(self, text):
        self.boss_log.append(str(text))
        if len(self.boss_log) > 3:
            self.boss_log.pop(0)

    def _boss_counter(self, defending: bool):
        if self.boss_turn % 2 == 0:
            if defending:
                self.player.defend_timer = 0.55
                self.boss_windup = False
                for _s, text in BOSS_BLOCKED:
                    self._boss_log(text.format(name=self.player.name))
                self.toast("Удар отражён! Теперь атакуй (E).", (150, 232, 255))
                self.sfx("block")
                self.particles.sparks(self.player.rect.centerx, self.player.rect.centery,
                                      (150, 220, 255), count=10)
            else:
                self._boss_death()
        else:
            self.boss_windup = True
            for _s, text in [BOSS_WINDUP]:
                self._boss_log(text.format(name=self.player.name))
            self.toast("Босс замахивается — защищайся (Z)!", (255, 150, 100))
            self.sfx("lock")

    def _boss_death(self):
        self.player.hurt_timer = 1.0
        self.player.hp = 0
        self.sfx("hit")
        self.particles.burst(self.player.rect.centerx, self.player.rect.centery,
                             (230, 80, 80), count=24, spread=150)
        lines = self._fmt(BOSS_HIT)
        self._boss_log("Босс победил тебя. Очнёшься у пирса.")
        self.start_dialogue(lines, on_close=self._after_boss_death)

    def _after_boss_death(self):
        self.player.hp = self.player.max_hp
        self.boss_hp = self.boss_max_hp
        self.boss_turn = 0
        self.boss_windup = False
        self.boss_log.clear()
        self.sfx("open")
        self.enter_level("10", side="left")
        self.toast("Босс восстановил силы. Попробуй снова.", (240, 170, 130))

    def _boss_victory(self):
        self.boss_defeated = True
        self.boss_hp = 0
        self.boss_windup = False
        self.player.money += 500
        self.sfx("win")
        self.particles.burst(self.player.rect.centerx, self.player.rect.centery - 30,
                             (255, 220, 110), count=36, spread=190)
        for _s, text in BOSS_VICTORY:
            self._boss_log(text.format(name=self.player.name))
        self.start_dialogue(self._fmt(BOSS_VICTORY), on_close=self._after_boss_victory)

    def _after_boss_victory(self):
        self.enter_level("12", side="left")
        self.victory_ready = True

    def boss_player_action(self, action: str):
        if self.level_id != "11" or self.dialogue or self.boss_defeated:
            return
        if not self.boss_intro_seen:
            self._start_boss_intro()
            return
        if not self._boss_near():
            return
        if action == "attack":
            self.boss_turn += 1
            self.player.attack_timer = 0.24
            self.player.facing = 1
            self.sfx("swing")
            if self.player.sword_type != "iron":
                for _s, text in BOSS_ATTACK_NO_IRON:
                    self._boss_log(text.format(name=self.player.name))
                self.toast("Нужен железный меч!", (240, 130, 120))
                self.sfx("lock")
            else:
                self.boss_hp -= 1
                self.boss_flash = 0.35
                self.sfx("hit")
                self.particles.sparks(832, self.level.floor_y - 70,
                                      (255, 210, 130), count=22)
                for _s, text in [BOSS_ATTACK_IRON]:
                    self._boss_log(text.format(name=self.player.name))
            if self.boss_hp <= 0:
                self._boss_victory()
                return
            self._boss_counter(defending=False)
        elif action == "defend":
            self.boss_turn += 1
            self.player.defend_timer = 0.55
            for _s, text in [BOSS_DEFEND]:
                self._boss_log(text.format(name=self.player.name))
            self._boss_counter(defending=True)

    def _enforce_boss_gate(self):
        if self.level_id != "11" or self.boss_defeated or self.dialogue:
            return
        boss = self._boss_entity()
        if boss is None:
            return
        if not self.boss_intro_seen:
            if abs(self.player.rect.centerx - boss.x) < 250:
                self._start_boss_intro()
            return
        limit = int(boss.x - 34 - self.player.rect.width)
        if self.player.rect.x > limit:
            self.player.rect.x = limit
            if self.player.vx > 0:
                self.player.vx = 0.0

    # ==================================================================
    # События
    # ==================================================================
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                continue
            if event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.windowed_size = (max(320, event.w), max(180, event.h))
                self.window = pygame.display.set_mode(
                    self.windowed_size, pygame.RESIZABLE)
                continue
            if event.type != pygame.KEYDOWN:
                continue

            if event.key == pygame.K_F11:
                self._toggle_fullscreen()
                continue
            if event.key == pygame.K_m:
                self.toggle_mute()
                continue
            if event.key == pygame.K_q:
                self.running = False
                return

            if self.state == "title":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                    self.start_new_game()
                continue
            if self.state == "victory":
                if event.key == pygame.K_r:
                    self.start_new_game()
                elif event.key == pygame.K_ESCAPE:
                    self.running = False
                continue

            if self.dialogue:
                self.dialogue.handle_event(event)
                continue
            if self.shop:
                self.shop.handle_event(event)
                continue

            if self.paused:
                if event.key == pygame.K_ESCAPE:
                    self.paused = False
                continue
            if self.inventory_open:
                if event.key in (pygame.K_ESCAPE, pygame.K_i):
                    self.inventory_open = False
                    self.transition_lock = 0.2
                continue

            if event.key == pygame.K_ESCAPE:
                self.paused = True
                self.sfx("blip")
            elif event.key == pygame.K_i:
                self.inventory_open = True
                self.sfx("open")
            elif event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.jump_requested = True
            elif event.key == pygame.K_e:
                self._interact()
            elif event.key == pygame.K_z:
                if self.level_id == "11" and self.boss_intro_seen and not self.boss_defeated:
                    self.boss_player_action("defend")

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.window = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)

    def _interact(self):
        if self.level_id == "12" and not self.victory_ready:
            pass
        entity = self.world.find_interactable(self.player)
        if entity is not None:
            entity.activate()
            return
        if self.level_id == "11" and self.boss_intro_seen and not self.boss_defeated:
            if self._boss_near():
                self.boss_player_action("attack")

    def start_new_game(self):
        self.used.clear()
        self.particles.items.clear()
        self.player.reset_inventory()
        self.dragon_following = False
        self.boss_max_hp = 3
        self.boss_hp = 3
        self.boss_turn = 0
        self.boss_windup = False
        self.boss_flash = 0.0
        self.boss_defeated = False
        self.boss_intro_seen = False
        self.boss_intro_active = False
        self.boss_log.clear()
        self.toasts.clear()
        self.state = "play"
        self.hint_timer = 9.0
        self.enter_level("1", side=None)
        self.toast("Лесная тропа. Впереди — приключение!", (190, 240, 150))
        self.sfx("accept")

    def restart(self):
        self.start_new_game()

    # ==================================================================
    # Обновление
    # ==================================================================
    def update(self, dt):
        self.t += dt
        self.boss_flash = max(0.0, self.boss_flash - dt)
        self._update_toasts(dt)

        if self.state == "title":
            self.title_time += dt
            self.particles.update(dt)
            return
        if self.state == "victory":
            self.victory_time += dt
            self._update_fireworks(dt)
            self.particles.update(dt)
            return

        if self.banner_timer > 0:
            self.banner_timer = max(0.0, self.banner_timer - dt)
        if self.hint_timer > 0:
            self.hint_timer = max(0.0, self.hint_timer - dt)

        if self.dialogue:
            self.dialogue.update(dt)
            if self.dialogue.done:
                self.dialogue = None
            self._update_scene(dt, frozen=True)
            return
        if self.shop or self.inventory_open or self.paused:
            self.particles.update(dt)
            return

        self.transition_lock = max(0.0, self.transition_lock - dt)
        keys = pygame.key.get_pressed()
        axis = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            axis -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            axis += 1
        jump_held = keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
        jump_pressed = self.jump_requested
        self.jump_requested = False

        self.player.update(dt, axis, jump_pressed, jump_held)
        self._enforce_boss_gate()
        self._check_transitions()
        self._update_scene(dt, frozen=False)

    def _update_scene(self, dt, frozen: bool):
        self.cam_x = self.world.camera_x(self.player)
        self.cam_y = self.world.camera_y
        self.world.update(dt, self.cam_x, self.cam_y, self.player)
        self.particles.update(dt)
        self._update_dragon(dt)

    def _update_dragon(self, dt):
        if not self.dragon_following:
            return
        p = self.player
        target_x = p.rect.centerx - p.facing * 46 + math.sin(self.t * 2.2) * 3
        target_y = p.rect.centery - 44 + math.sin(self.t * 3.1) * 4
        if p.riding_boat:
            target_y -= 4
        if self.dragon_pos.length_squared() == 0:
            self.dragon_pos.update(target_x, target_y)
        else:
            k = min(1.0, dt * 4.5)
            self.dragon_pos.x += (target_x - self.dragon_pos.x) * k
            self.dragon_pos.y += (target_y - self.dragon_pos.y) * k

    def _update_fireworks(self, dt):
        self.fire_timer -= dt
        if self.fire_timer <= 0:
            self.fire_timer = random.uniform(0.25, 0.7)
            x = random.uniform(60, SCREEN_W - 60)
            y = random.uniform(40, 160)
            col = random.choice([(255, 220, 110), (255, 140, 110), (140, 230, 255),
                                 (190, 255, 150)])
            self.particles.burst(x, y, col, count=18, spread=120, up=0,
                                 gravity=120, life=1.0, size=1)

    # ==================================================================
    # Рисование
    # ==================================================================
    def draw(self):
        c = self.canvas
        if self.state == "title":
            self._draw_title(c)
        elif self.state == "victory":
            self._draw_victory(c)
        else:
            self.world.draw_background(c, self.t, self.cam_x, self.cam_y)
            self.world.draw_tiles(c, self.t, self.cam_x, self.cam_y)
            self.world.draw_decor(c, self.t, self.cam_x, self.cam_y)
            self.world.draw_entities(c, self.t, self.cam_x, self.cam_y)
            self._draw_dragon(c)
            self.player.draw(c, self.cam_x, self.cam_y, self.t)
            self.particles.draw(c, self.cam_x, self.cam_y)
            self._draw_hud(c)
            self._draw_banner(c)
            self._draw_toasts(c)
            self._draw_prompt(c)
            if self.dialogue:
                self.dialogue.draw(c)
            if self.shop:
                self._dim(c, 90)
                self.shop.draw(c)
            if self.inventory_open:
                self._dim(c, 110)
                self._draw_inventory(c)
            if self.paused:
                self._dim(c, 150)
                self._draw_pause(c)

    def _draw_dragon(self, c):
        if not self.dragon_following or self.state != "play":
            return
        x = self.dragon_pos.x - self.cam_x
        y = self.dragon_pos.y - self.cam_y
        assets.draw_dragon(c, x, y, self.t, facing=self.player.facing, scale=0.55)

    def _draw_title(self, c):
        assets.draw_background(c, "title", self.title_time, 0, 0, SCREEN_W, SCREEN_H)
        # земля
        for col in range(SCREEN_W // TILE + 1):
            assets.draw_tile(c, "ground", "forest", col * TILE, 234, col, 14,
                             self.title_time, top_open=True)
        assets.rect(c, 0, 250, SCREEN_W, 20, (34, 62, 44))
        # герой и дракон
        hero = pygame.Rect(210, 208, 16, 26)
        assets.draw_shadow(c, hero.centerx, 234, 18)
        assets.draw_player(c, hero, 1, "idle", "stone_pick", self.title_time)
        assets.draw_dragon(c, 258, 226, self.title_time, facing=-1, scale=0.8)
        assets.draw_tree(c, 96, 234, self.title_time)
        assets.draw_tree(c, 396, 234, self.title_time)
        assets.draw_ore(c, 160, 234, self.title_time)
        assets.draw_ore(c, 330, 234, self.title_time)

        ui.text(c, "MINE-LINE", SCREEN_W // 2, 58, (255, 232, 150), 34,
                True, center=True)
        ui.text(c, "QUEST", SCREEN_W // 2, 94, (180, 240, 255), 28,
                True, center=True)
        ui.text(c, "2D PIXEL REMAKE", SCREEN_W // 2, 126, (208, 200, 176), 9,
                True, center=True)
        for i, line in enumerate(TITLE_LINES):
            ui.text(c, line, SCREEN_W // 2, 146 + i * 11, (160, 156, 146), 7,
                    center=True)

        blink = int(self.title_time * 2.2) % 2 == 0
        if blink:
            ui.panel(c, (SCREEN_W // 2 - 92, 178, 184, 22),
                     bg=(24, 22, 38), border=(198, 170, 112), alpha=235)
            ui.text(c, "Нажми Enter, чтобы начать", SCREEN_W // 2, 184,
                    (255, 236, 180), 8, True, center=True)
        ui.text(c, "A/D — идти · Пробел — прыжок · E — действие · I — инвентарь",
                SCREEN_W // 2, 256, (140, 140, 136), 7, center=True)

    def _draw_victory(self, c):
        assets.draw_background(c, "victory", self.t, 0, 0, SCREEN_W, SCREEN_H)
        self.particles.draw(c, 0, 0)
        assets.rect(c, 0, 226, SCREEN_W, 44, (150, 72, 60))
        assets.rect(c, 0, 226, SCREEN_W, 5, (255, 214, 120))
        hero = pygame.Rect(150, 198, 16, 26)
        assets.draw_shadow(c, hero.centerx, 226, 18)
        assets.draw_player(c, hero, 1, "idle", "iron_sword", self.t)
        if self.dragon_following:
            assets.draw_dragon(c, 205, 218, self.t, facing=1, scale=0.9)
        assets.draw_boss(c, 330, 226, self.t, 0, self.boss_max_hp, defeated=True)

        ui.panel(c, (64, 36, 352, 122), bg=(30, 18, 24), border=(255, 214, 120), alpha=238)
        ui.text(c, "ПОБЕДА!", SCREEN_W // 2, 48, (255, 232, 140), 30,
                True, center=True)
        ui.text(c, "Король-гоблин повержен. Шахты свободны!", SCREEN_W // 2, 84,
                (245, 228, 198), 9, True, center=True)
        p = self.player
        gear_parts = []
        if p.pickaxe_type:
            gear_parts.append("кирка: " + ("железная" if p.pickaxe_type == "iron" else "каменная"))
        if p.sword_type:
            gear_parts.append("меч: " + ("железный" if p.sword_type == "iron" else "каменный"))
        gear = " · ".join(gear_parts) if gear_parts else "без снаряжения"
        ui.text(c, f"Монеты: {p.money}   ·   {gear}", SCREEN_W // 2, 102,
                (250, 214, 130), 8, center=True)
        ui.text(c, f"Джек-дракон: {'в команде' if self.dragon_following else 'остался в лесу'}",
                SCREEN_W // 2, 116, (190, 226, 200), 8, center=True)
        ui.text(c, "Сюжет, герои и диалоги — из оригинальной MINE-LINE.",
                SCREEN_W // 2, 134, (176, 166, 156), 7, center=True)
        blink = int(self.victory_time * 2) % 2 == 0
        if blink:
            ui.text(c, "R — начать заново   ·   Esc — выход", SCREEN_W // 2, 168,
                    (255, 244, 208), 8, True, center=True)

    # ------------------------------------------------------------------
    def _draw_hud(self, c):
        p = self.player
        ui.panel(c, (6, 6, 214, 43), bg=(14, 13, 22), border=(94, 86, 112), alpha=214)
        for i in range(p.max_hp):
            ui.heart(c, 12 + i * 10, 10, filled=i < max(0, p.hp))
        ui.icon_coin(c, 54, 9)
        ui.text(c, str(p.money), 66, 10, (250, 216, 120), 8, True)
        equip = "—"
        if p.sword_type:
            equip = "жел. меч" if p.sword_type == "iron" else "кам. меч"
        elif p.pickaxe_type:
            equip = "жел. кирка" if p.pickaxe_type == "iron" else "кам. кирка"
        ui.text(c, equip, 212, 10, (190, 184, 172), 7, right=True)

        rx = 12
        ui.icon_wood(c, rx, 28)
        w = ui.text(c, str(p.wood), rx + 12, 28, (214, 196, 168), 8)
        rx += 12 + w + 18
        ui.icon_stone(c, rx, 28)
        w = ui.text(c, str(p.stones), rx + 12, 28, (206, 202, 206), 8)
        rx += 12 + w + 18
        ui.icon_iron(c, rx, 28)
        w = ui.text(c, str(p.iron), rx + 12, 28, (190, 212, 230), 8)
        rx += 12 + w + 18
        if self.dragon_following:
            ui.text(c, "Джек", 198, 27, (150, 226, 170), 7, right=True)

        if self.level_id != "11":
            info = LEVEL_INFO.get(self.level_id, {})
            ui.panel(c, (SCREEN_W - 154, 6, 148, 20), bg=(14, 13, 22),
                     border=(94, 86, 112), alpha=214)
            ui.text(c, info.get("name", ""), SCREEN_W - 14, 10,
                    (232, 222, 200), 8, True, right=True)

        if self.level_id == "11" and self.boss_intro_seen and not self.boss_defeated:
            self._draw_boss_bar(c)

        if self.hint_timer > 0 and not self.dialogue:
            ui.text(c, "I — инвентарь · Esc — пауза · M — звук",
                    SCREEN_W - 8, SCREEN_H - 12, (170, 166, 156), 7, right=True)

        if self.player.riding_boat and not self.dialogue:
            ui.text(c, "← / → — управлять лодкой", SCREEN_W // 2, SCREEN_H - 22,
                    (200, 236, 255), 8, True, center=True)

    def _draw_boss_bar(self, c):
        x, y, w, h = SCREEN_W // 2 - 104, 54, 208, 31
        ui.panel(c, (x, y, w, h), bg=(34, 12, 18), border=(198, 92, 82), alpha=234)
        ui.text(c, "КОРОЛЬ-ГОБЛИН", x + 8, y + 4, (255, 190, 160), 8, True)
        for i in range(self.boss_max_hp):
            ui.heart(c, x + w - 62 + i * 12, y + 4, filled=i < self.boss_hp)
        if self.boss_windup:
            ui.text(c, "ЗАМАХ! Z — защита", x + 8, y + 16, (255, 142, 96), 7, True)
        else:
            ui.text(c, "E — атака · Z — защита", x + 8, y + 16, (222, 196, 180), 7)
        # последние сообщения боя
        for i, line in enumerate(self.boss_log[-2:]):
            ui.text(c, line, SCREEN_W // 2, y + h + 4 + i * 10,
                    (242, 216, 190), 7, center=True)

    def _draw_banner(self, c):
        if self.banner_timer <= 0 or self.dialogue:
            return
        fade = min(1.0, self.banner_timer / 0.55)
        w = 260
        x = SCREEN_W // 2 - w // 2
        y = 66
        ui.panel(c, (x, y, w, 38), bg=(18, 16, 28), border=(178, 152, 100),
                 alpha=int(220 * fade))
        ui.text(c, self.banner_text, SCREEN_W // 2, y + 7,
                (250, 228, 168), 11, True, center=True)
        if self.banner_sub:
            lines = ui.wrap(self.banner_sub, w - 20, 7)
            if lines:
                ui.text(c, lines[0], SCREEN_W // 2, y + 23,
                        (190, 184, 170), 7, center=True)

    def _draw_toasts(self, c):
        y = SCREEN_H - 42
        for item in reversed(self.toasts):
            life = max(0.0, item["life"])
            alpha = int(255 * min(1.0, life / 0.5))
            if alpha <= 8:
                continue
            f = ui.font(8, True)
            w = min(SCREEN_W - 24, f.size(item["text"])[0] + 18)
            x = SCREEN_W // 2 - w // 2
            ui.panel(c, (x, y - 8, w, 17), bg=(18, 15, 24),
                     border=(120, 110, 130), alpha=min(230, alpha + 40))
            ui.text(c, item["text"], SCREEN_W // 2, y - 5,
                    item["color"], 8, True, center=True)
            y -= 20

    def _draw_prompt(self, c):
        if self.dialogue or self.shop or self.inventory_open or self.paused:
            return
        entity = self.world.find_interactable(self.player)
        prompt = entity.prompt() if entity else ""
        if not prompt and self.level_id == "11" and self.boss_intro_seen and not self.boss_defeated:
            prompt = "E — атака, Z — защита"
        if not prompt:
            return
        f = ui.font(8, True)
        w = min(SCREEN_W - 20, f.size(prompt)[0] + 20)
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H - 32
        ui.panel(c, (x, y, w, 17), bg=(20, 18, 28), border=(210, 182, 120), alpha=228)
        ui.text(c, prompt, SCREEN_W // 2, y + 3, (255, 236, 184), 8, True,
                center=True)

    def _draw_inventory(self, c):
        p = self.player
        x, y, w, h = 88, 46, 304, 178
        ui.panel(c, (x, y, w, h), bg=(22, 20, 32), border=(168, 146, 108), alpha=246)
        ui.text(c, "ИНВЕНТАРЬ", x + w // 2, y + 8, (255, 226, 150), 12,
                True, center=True)
        ui.text(c, p.name, x + w // 2, y + 24, (190, 214, 236), 8, center=True)

        row = y + 42
        ui.icon_wood(c, x + 20, row)
        ui.text(c, f"Дерево: {p.wood}", x + 36, row, (216, 196, 168), 8)
        ui.icon_stone(c, x + 156, row)
        ui.text(c, f"Камни: {p.stones}", x + 172, row, (208, 204, 208), 8)

        row += 18
        ui.icon_iron(c, x + 20, row)
        ui.text(c, f"Железо: {p.iron}", x + 36, row, (192, 214, 232), 8)
        ui.icon_coin(c, x + 156, row)
        ui.text(c, f"Монеты: {p.money}", x + 172, row, (250, 214, 120), 8)

        row += 22
        pick = "нет"
        if p.pickaxe_type == "stone":
            pick = "каменная"
        elif p.pickaxe_type == "iron":
            pick = "железная"
        sword = "нет"
        if p.sword_type == "stone":
            sword = "каменный"
        elif p.sword_type == "iron":
            sword = "железный"
        ui.text(c, f"Кирка: {pick}", x + 20, row, (226, 216, 198), 8)
        ui.text(c, f"Меч: {sword}", x + 156, row, (226, 216, 198), 8)

        row += 22
        ui.text(c, "Джек-дракон: " + ("в команде" if self.dragon_following else "ещё не встречен"),
                x + 20, row, (176, 224, 188), 8)
        row += 18
        if self.boss_defeated:
            quest = "Король-гоблин повержен!"
        elif self.boss_intro_seen:
            quest = "Бой с королём-гоблином идёт."
        elif p.sword_type == "iron":
            quest = "Железный меч готов. Иди на арену (уровень 11)."
        elif p.pickaxe_type:
            quest = "Добудь железо и выкуй железный меч у торговца."
        else:
            quest = "Найди камни и дерево, затем кузницу пустыни."
        for line in ui.wrap(quest, w - 36, 8)[:2]:
            ui.text(c, line, x + 20, row, (238, 196, 132), 8)
            row += 11
        ui.text(c, "I / Esc — закрыть", x + w // 2, y + h - 14,
                (154, 148, 140), 7, center=True)

    def _draw_pause(self, c):
        x, y, w, h = 112, 34, 256, 206
        ui.panel(c, (x, y, w, h), bg=(18, 17, 28), border=(160, 140, 104), alpha=248)
        ui.text(c, "ПАУЗА", x + w // 2, y + 10, (255, 226, 152), 14,
                True, center=True)
        row = y + 34
        for keys, action in CONTROLS:
            ui.text(c, keys, x + 18, row, (180, 220, 240), 8, True)
            ui.text(c, action, x + w - 18, row, (224, 218, 204), 8, right=True)
            row += 14
        ui.text(c, "Esc — продолжить", x + w // 2, y + h - 18,
                (255, 236, 180), 8, True, center=True)

    def _dim(self, c, alpha=110):
        layer = assets.alpha_surface((SCREEN_W, SCREEN_H))
        layer.fill((6, 6, 12, alpha))
        c.blit(layer, (0, 0))

    # ==================================================================
    # Экран / цикл
    # ==================================================================
    def present(self):
        ww, wh = self.window.get_size()
        scale = min(ww / SCREEN_W, wh / SCREEN_H)
        if scale >= 1:
            scale = max(1, int(scale))
        sw, sh = max(1, int(SCREEN_W * scale)), max(1, int(SCREEN_H * scale))
        if (sw, sh) != (SCREEN_W, SCREEN_H):
            view = pygame.transform.scale(self.canvas, (sw, sh))
        else:
            view = self.canvas
        self.window.fill((0, 0, 0))
        self.window.blit(view, ((ww - sw) // 2, (wh - sh) // 2))
        pygame.display.flip()

    def run(self, max_frames: int | None = None):
        frames = 0
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000.0)
            if self.headless and frames > 0:
                dt = 1.0 / FPS
            self.handle_events()
            self.update(dt)
            self.draw()
            if not self.headless:
                self.present()
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        return frames


def main():
    game = Game()
    game.run()
    pygame.quit()
    sys.exit(0)
