# -*- coding: utf-8 -*-
"""Диалоги в стиле оригинального текстового квеста."""
from __future__ import annotations

import pygame

from . import ui
from .config import SCREEN_H, SCREEN_W


class Dialogue:
    """Очередь реплик с эффектом печатной машинки и выбором Да/Нет."""

    def __init__(self, game, lines, choice=None, on_choice=None, on_close=None):
        self.game = game
        self.lines = [(str(speaker or ""), str(text)) for speaker, text in lines]
        self.choice = choice          # (вопрос, "Да", "Нет") или None
        self.on_choice = on_choice
        self.on_close = on_close
        self.index = 0
        self.reveal = 0.0
        self.mode = "text"            # text | choice
        self.choice_index = 0
        self.done = False
        self.closed = False

    # ------------------------------------------------------------------
    # Логика
    # ------------------------------------------------------------------
    @property
    def current(self):
        if not self.lines:
            return ("", "")
        return self.lines[min(self.index, len(self.lines) - 1)]

    @property
    def text(self) -> str:
        return self.current[1]

    @property
    def speaker(self) -> str:
        return self.current[0]

    @property
    def reveal_max(self) -> int:
        return max(1, len(self.text))

    def update(self, dt):
        if self.mode == "text":
            self.reveal = min(self.reveal_max, self.reveal + dt * 52.0)

    def _finish(self):
        self.done = True
        self.closed = True
        if self.on_close:
            self.on_close()

    def advance(self):
        if self.mode == "text":
            if self.reveal < self.reveal_max:
                self.reveal = self.reveal_max
                return
            if self.index + 1 < len(self.lines):
                self.index += 1
                self.reveal = 0.0
                self.game.sfx("blip")
                return
            if self.choice:
                self.mode = "choice"
                self.game.sfx("blip")
                return
            self._finish()
            return
        self._confirm_choice()

    def _confirm_choice(self):
        yes = self.choice_index == 0
        if self.on_choice:
            self.on_choice(yes)
        self._finish()

    def close(self):
        """Esc: закрыть диалог без выбора (выбор считается «Нет»)."""
        if self.mode == "choice" and self.choice:
            yes = self.choice_index == 0
            if self.on_choice:
                self.on_choice(yes)
        self._finish()

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return False
        if event.key == pygame.K_ESCAPE:
            self.close()
            return True
        if self.mode == "choice":
            if event.key in (pygame.K_LEFT, pygame.K_a):
                self.choice_index = 0
                self.game.sfx("blip")
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.choice_index = 1
                self.game.sfx("blip")
            elif event.key in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                self._confirm_choice()
            return True
        if event.key in (pygame.K_e, pygame.K_SPACE, pygame.K_RETURN, pygame.K_z):
            self.advance()
            return True
        return False

    # ------------------------------------------------------------------
    # Рисование
    # ------------------------------------------------------------------
    def draw(self, canvas):
        if not self.lines:
            return
        x, y, w, h = 8, 158, SCREEN_W - 16, 104
        ui.panel(canvas, (x, y, w, h), bg=(16, 14, 26), border=(132, 116, 86),
                 alpha=238)

        speaker = self.speaker
        if speaker:
            name_w = max(48, ui.font(8, True).size(speaker)[0] + 14)
            ui.panel(canvas, (x + 8, y - 9, name_w, 17),
                     bg=(78, 58, 42), border=(198, 170, 112), alpha=255)
            ui.text(canvas, speaker, x + 8 + name_w // 2, y - 7,
                    (250, 230, 176), 8, True, center=True)

        if self.mode == "text":
            shown = self.text[: int(self.reveal)]
            lines = ui.wrap(shown, w - 24, 9)
            ty = y + 12
            for line in lines[:5]:
                ui.text(canvas, line, x + 12, ty, (236, 232, 214), 9)
                ty += 13
            if self.reveal >= self.reveal_max:
                blink = int(self.game.t * 3) % 2 == 0
                if blink:
                    ui.text(canvas, "▼", x + w - 16, y + h - 17, (250, 220, 140), 8)
                hint = "E / Пробел — далее"
                if self.index + 1 >= len(self.lines) and not self.choice:
                    hint = "E / Пробел — закрыть"
                ui.text(canvas, hint, x + w - 10, y + h - 14, (150, 142, 132), 7,
                        right=True)
        else:
            prompt, yes_label, no_label = self.choice
            ui.text(canvas, prompt, x + w // 2, y + 14, (250, 232, 190), 9,
                    True, center=True)
            labels = (yes_label, no_label)
            total_w = 150
            start = x + (w - total_w) // 2
            for i, label in enumerate(labels):
                bx = start + i * 80
                by = y + 44
                selected = i == self.choice_index
                ui.panel(canvas, (bx, by, 70, 26),
                         bg=(112, 84, 44) if selected else (42, 38, 54),
                         border=(250, 214, 120) if selected else (96, 88, 110),
                         alpha=255)
                ui.text(canvas, label, bx + 35, by + 7,
                        (255, 244, 206) if selected else (206, 202, 190),
                        10, True, center=True)
                if selected:
                    ui.text(canvas, "▶", bx - 11, by + 6, (255, 220, 120), 9)
            ui.text(canvas, "← → выбрать · E подтвердить", x + w // 2, y + h - 18,
                    (150, 142, 132), 7, center=True)
