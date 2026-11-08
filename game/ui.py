# -*- coding: utf-8 -*-
"""Текст, панели и мелкие пиксельные иконки интерфейса."""
from __future__ import annotations

import pygame

from .assets import alpha_surface, font, rect, outline, shade


def text(surface, value, x, y, color=(245, 245, 235), size=8, bold=False,
         center=False, right=False, shadow=True):
    f = font(size, bold)
    img = f.render(str(value), True, color)
    if center:
        x -= img.get_width() // 2
    elif right:
        x -= img.get_width()
    if shadow:
        sh = f.render(str(value), True, (10, 9, 16))
        surface.blit(sh, (int(x) + 1, int(y) + 1))
    surface.blit(img, (int(x), int(y)))
    return img.get_width()


def wrap(value, width, size=8, bold=False):
    f = font(size, bold)
    words = str(value).split()
    lines: list[str] = []
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        if f.size(test)[0] <= width or not line:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def panel(surface, area, bg=(18, 16, 28), border=(96, 88, 120), alpha=232, radius=0):
    x, y, w, h = [int(v) for v in area]
    if alpha >= 255:
        rect(surface, x, y, w, h, bg)
    else:
        layer = alpha_surface((w, h))
        pygame.draw.rect(layer, (*bg, alpha), (0, 0, w, h))
        surface.blit(layer, (x, y))
    outline(surface, x, y, w, h, border)
    if w > 4 and h > 4:
        outline(surface, x + 1, y + 1, w - 2, h - 2, shade(bg, 0.10))


def bar(surface, x, y, w, h, value, maximum, color=(214, 72, 72),
        back=(52, 26, 34), border=(18, 14, 22)):
    rect(surface, x - 1, y - 1, w + 2, h + 2, border)
    rect(surface, x, y, w, h, back)
    if maximum > 0:
        fill = int(w * max(0, min(1.0, value / maximum)))
        if fill:
            rect(surface, x, y, fill, h, color)
            rect(surface, x, y, fill, 1, shade(color, 0.25))
            rect(surface, x, y + h - 1, fill, 1, shade(color, -0.2))


def icon_wood(surface, x, y, scale=1):
    rect(surface, x, y + 2, 9, 3, (142, 92, 49))
    rect(surface, x, y + 2, 9, 1, (186, 130, 71))
    rect(surface, x, y + 4, 9, 1, (98, 61, 35))
    rect(surface, x + 8, y + 2, 2, 3, (210, 176, 120))


def icon_stone(surface, x, y, scale=1):
    pygame.draw.ellipse(surface, (136, 138, 154), (x, y + 1, 10, 7))
    pygame.draw.ellipse(surface, (172, 174, 188), (x + 1, y + 2, 7, 4))
    rect(surface, x + 7, y + 4, 2, 2, (100, 102, 118))


def icon_iron(surface, x, y, scale=1):
    rect(surface, x, y + 3, 10, 4, (150, 170, 190))
    rect(surface, x + 1, y + 2, 8, 2, (190, 206, 220))
    rect(surface, x, y + 6, 10, 1, (92, 110, 132))
    surface.set_at((x + 2, y + 3), (240, 250, 255))


def icon_coin(surface, x, y, scale=1):
    pygame.draw.circle(surface, (247, 200, 72), (x + 5, y + 5), 5)
    pygame.draw.circle(surface, (255, 228, 126), (x + 5, y + 5), 3)
    rect(surface, x + 4, y + 2, 1, 6, (198, 148, 32))


def heart(surface, x, y, filled=True, size=1):
    col = (224, 72, 72) if filled else (72, 54, 64)
    hi = (255, 148, 148) if filled else (96, 76, 88)
    points = [(x + 1, y + 2), (x + 2, y + 1), (x + 3, y + 1), (x + 4, y + 2),
              (x + 5, y + 1), (x + 6, y + 1), (x + 7, y + 2), (x + 7, y + 3),
              (x + 4, y + 7), (x + 1, y + 3)]
    pygame.draw.polygon(surface, col, points)
    surface.set_at((x + 2, y + 2), hi)


def keycap(surface, x, y, label, size=8):
    w = max(12, font(size, True).size(label)[0] + 6)
    panel(surface, (x, y, w, 12), bg=(42, 38, 56), border=(120, 110, 150), alpha=255)
    text(surface, label, x + w // 2, y + 1, (240, 238, 220), size, True, center=True, shadow=False)
    return w
