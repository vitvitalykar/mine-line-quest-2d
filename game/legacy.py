# -*- coding: utf-8 -*-
"""Загрузчик оригинальных ASCII-карт MINE-LINE.

Мы сохраняем все экраны 0..12: метаданные (спавн, объекты, переходы)
читаются из тех же трёх служебных строк, что и в оригинальной игре.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .config import TILE


def _resource_root() -> Path:
    """Корень ресурсов: обычный запуск или распакованный PyInstaller exe."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parent.parent


LEGACY_DIR = _resource_root() / "legacy"
SCREENS_DIR = LEGACY_DIR / "screens"
HEROES_DIR = LEGACY_DIR / "heroes"

WATER_CHARS = set("wWvVoOlLnNaAhH")
SOLID_KINDS = {"rock", "ground", "struct", "dock"}

# kind -> (legacy width, legacy height, hero file)
OBJECTS = {
    "tree": (5, 9, "tree.txt"),
    "dragon": (8, 3, "dragon.txt"),
    "mine": (20, 9, "mine.txt"),
    "ore": (3, 2, "ore.txt"),
    "stone": (3, 6, "javal.txt"),
    "boat": (6, 2, "lodka.txt"),
    "wall": (1, 2, "empty.txt"),
    "trader": (4, 6, "trader.txt"),
    "boss": (40, 28, "boss.txt"),
}

SYMBOL_TO_KIND = {
    "t": "tree",
    "d": "dragon",
    "m": "mine",
    "o": "ore",
    "j": "stone",
    "l": "boat",
    "!": "wall",
    "r": "trader",
    "b": "boss",
}


@dataclass
class EntitySpec:
    kind: str
    col: int          # колонка символа в метаданных
    row: int          # верх спрайта в координатах ASCII
    legacy_w: int
    legacy_h: int
    feet_row: int = 0
    uid: str = ""

    def __post_init__(self) -> None:
        if not self.uid:
            self.uid = f"{self.kind}:{self.col}:{self.row}"


@dataclass
class Transition:
    target: str
    col_start: int
    col_end: int

    @property
    def x_start(self) -> int:
        return self.col_start * TILE

    @property
    def x_end(self) -> int:
        return (self.col_end + 1) * TILE


@dataclass
class LevelData:
    id: str
    raw_rows: list[str]
    tiles: list[list[str]]
    solid: list[list[bool]]
    spawn_col: int
    spawn_row: int
    entities: list[EntitySpec]
    transitions: list[Transition]
    width: int
    height: int
    theme: str = "forest"

    @property
    def pixel_width(self) -> int:
        return self.width * TILE

    @property
    def pixel_height(self) -> int:
        return self.height * TILE

    @property
    def spawn_x(self) -> int:
        return self.spawn_col * TILE + (TILE - 16) // 2

    @property
    def spawn_y(self) -> int:
        # spawn_row -- клетка, в которой стоят ноги героя
        return (self.spawn_row + 1) * TILE - 26

    @property
    def floor_y(self) -> int:
        return (self.height - 1) * TILE

    def solid_at(self, col: int, row: int) -> bool:
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return False
        return self.solid[row][col]

    def solid_px(self, x: float, y: float) -> bool:
        return self.solid_at(int(x // TILE), int(y // TILE))

    def tile_at(self, col: int, row: int) -> str:
        if row < 0 or row >= self.height or col < 0 or col >= self.width:
            return "empty"
        return self.tiles[row][col]


def _pad(lines: Iterable[str]) -> list[str]:
    lines = list(lines)
    width = max((len(line) for line in lines), default=0)
    return [line.ljust(width) for line in lines]


def _char(line: str, index: int) -> str:
    return line[index] if 0 <= index < len(line) else " "


def _pair(low: str, high: str, index: int) -> int:
    a = _char(low, index)
    b = _char(high, index)
    digits = (a + b).strip()
    if not digits:
        return 0
    digits = "".join(ch for ch in digits if ch.isdigit())
    return int(digits) if digits else 0


def _transition_value(top: str, mid: str, low: str, index: int) -> int | None:
    t = _char(top, index)
    if not t.isdigit():
        return None
    digits = _char(low, index) + _char(mid, index) + t
    digits = "".join(ch for ch in digits if ch.isdigit())
    if not digits:
        return None
    return int(digits)


def _load_hero_size(kind: str) -> tuple[int, int]:
    w, h, filename = OBJECTS[kind]
    path = HEROES_DIR / filename
    if path.exists():
        rows = path.read_text(encoding="utf-8-sig").splitlines()
        if rows:
            return max(len(r) for r in rows), len(rows)
    return w, h


def _ground_row(tiles: list[list[str]], col: int, start_row: int) -> int | None:
    if not tiles:
        return None
    col = max(0, min(col, len(tiles[0]) - 1))
    for row in range(max(0, start_row), len(tiles)):
        if tiles[row][col] in SOLID_KINDS:
            return row
    return None


def _make_solid(level_id: str, tiles: list[list[str]]) -> list[list[bool]]:
    """Слой коллизий.

    В оригинале это текстовый квест: вертикальные стены были декорацией.
    Для платформера твёрдым делаем только нижнюю строку (пол/пирс/мост),
    а шахтные колонны и потолки остаются красивым фоном, сквозь который
    герой проходит «перед» стеной.
    """
    if not tiles:
        return []
    height = len(tiles)
    width = len(tiles[0])
    solid = [[False] * width for _ in range(height)]
    if level_id in ("0", "9"):
        return solid
    floor = height - 1
    for col in range(width):
        if tiles[floor][col] in SOLID_KINDS:
            solid[floor][col] = True

    # Невидимый страховочный пол под переходами у краёв карты.
    if level_id not in ("8", "9"):
        for col in range(width):
            solid[floor][col] = True

    # Небольшие платформы-ящики в кузнице и на пирсе.
    if level_id in ("7", "8"):
        extra = []
        if level_id == "7":
            extra = [(86, 6), (87, 6), (88, 6)]
        if level_id == "8":
            extra = [(66, 6), (67, 6)]
        for col, row in extra:
            if 0 <= row < height and 0 <= col < width:
                solid[row][col] = True
    return solid


def _make_tiles(level_id: str, rows: list[str], theme: str) -> list[list[str]]:
    width = max((len(r) for r in rows), default=0)
    tiles: list[list[str]] = []
    for row_index, line in enumerate(rows):
        row: list[str] = []
        for col in range(width):
            ch = _char(line, col)
            kind = "empty"
            if level_id == "2":
                # Огромный дуб и текст нарисованы отдельными пиксельными
                # объектами; нам нужна сплошная лесная земля.
                kind = "ground" if row_index == len(rows) - 1 else "empty"
            elif level_id == "9":
                kind = "water" if row_index == len(rows) - 1 else "empty"
            elif level_id == "10":
                if row_index == len(rows) - 1 and col <= 15:
                    kind = "dock"
                elif ch == "█":
                    kind = "rock"
                elif ch in "_\\/-=+":
                    kind = "ground" if ch == "_" else "struct"
                elif ch == "|":
                    kind = "struct"
                elif ch in WATER_CHARS:
                    kind = "water"
            else:
                if ch == "█":
                    kind = "rock"
                elif ch == "_":
                    kind = "ground"
                elif ch in "\\/-=+":
                    kind = "struct"
                elif ch == "|":
                    kind = "struct"
                elif ch in WATER_CHARS:
                    kind = "water"
            row.append(kind)
        tiles.append(row)
    return tiles


def _parse_entities(
    level_id: str,
    top: str,
    mid: str,
    low: str,
    tiles: list[list[str]],
) -> list[EntitySpec]:
    specs: list[EntitySpec] = []
    width = max(len(top), len(mid), len(low))
    for index in range(width):
        symbol = _char(top, index)
        kind = SYMBOL_TO_KIND.get(symbol)
        if kind is None:
            continue
        lw, lh = _load_hero_size(kind)
        y = _pair(low, mid, index)
        col = index - 2
        spec = EntitySpec(kind=kind, col=col, row=y, legacy_w=lw, legacy_h=lh)
        if kind == "dragon":
            spec.feet_row = y + lh          # дракон летает
        else:
            ground = _ground_row(tiles, col + lw // 2, y)
            spec.feet_row = ground if ground is not None else y + lh
        specs.append(spec)

    # Левел-дизайн: на 6-м уровне спавн в оригинале находится внутри стены.
    if level_id == "6":
        for spec in specs:
            pass

    return specs


def _parse_transitions(level_id: str, top: str, mid: str, low: str) -> list[Transition]:
    groups: list[Transition] = []
    width = max(len(top), len(mid), len(low))
    current_target: str | None = None
    start = 0
    last = -2
    for index in range(width + 1):
        value = None if index >= width else _transition_value(top, mid, low, index)
        target = None if value is None else str(value)
        if target is not None and target == current_target and index == last + 1:
            last = index
            continue
        if current_target is not None and start <= last:
            groups.append(Transition(current_target, start, last))
        if target is None:
            current_target = None
        else:
            current_target = target
            start = index
            last = index
    if current_target is not None and start <= last:
        groups.append(Transition(current_target, start, last))

    # Чиним известные опечатки/обрывы оригинальных карт.
    fixed: list[Transition] = []
    for tr in groups:
        target = tr.target
        if target == "666":
            target = "6"  # очевидная опечатка: слева от кузницы должна быть 6
        if target.isdigit() and 0 <= int(target) <= 12:
            fixed.append(Transition(target, tr.col_start, tr.col_end))

    existing = {(t.target, t.col_start, t.col_end) for t in fixed}
    if level_id == "4" and not any(t.target == "3" for t in fixed):
        fixed.insert(0, Transition("3", 0, 1))
    if level_id == "6" and not any(t.target == "5" for t in fixed):
        fixed.insert(0, Transition("5", 0, 1))
    if level_id == "7":
        fixed = [t for t in fixed if t.target != "666"]
        if not any(t.target == "6" for t in fixed):
            fixed.insert(0, Transition("6", 0, 1))
    if level_id == "9" and not any(t.target == "8" for t in fixed):
        fixed.insert(0, Transition("8", 0, 1))
    if level_id == "10" and not any(t.target == "9" for t in fixed):
        fixed.insert(0, Transition("9", 0, 1))
    if level_id == "11":
        # из арены можно отступить на пирс, а направо — только после победы
        fixed = [t for t in fixed if t.target not in ("0", "2")]
        if not any(t.target == "10" for t in fixed):
            fixed.insert(0, Transition("10", 0, 1))
        if not any(t.target == "12" for t in fixed):
            fixed.append(Transition("12", width - 4, width - 1))
    return fixed


def load_level(level_id: str, theme: str) -> LevelData:
    path = SCREENS_DIR / f"{level_id}.txt"
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if len(lines) < 3:
        lines += [""] * (3 - len(lines))
    rows = _pad(lines[:-3])
    top, mid, low = _pad(lines[-3:])

    width = max((len(r) for r in rows), default=0)
    height = len(rows)
    tiles = _make_tiles(level_id, rows, theme)

    at = top.find("@")
    if at < 0:
        at = 0
    spawn_col = at - 2
    spawn_row_meta = _pair(low, mid, at)

    # Спавн не должен попадать внутрь декоративной стены или на переход.
    spawn_overrides = {"6": 3, "7": 5, "10": 5}
    spawn_col = max(spawn_col, spawn_overrides.get(level_id, 0))

    if level_id == "9":
        spawn_row = height - 1
    else:
        # Ищем пол под точкой спавна; ноги ставим на его верх.
        ground = _ground_row(tiles, spawn_col + 1, spawn_row_meta)
        if ground is None:
            ground = height - 1
        spawn_row = max(0, ground - 1)

    entities = _parse_entities(level_id, top, mid, low, tiles)
    transitions = _parse_transitions(level_id, top, mid, low)
    solid = _make_solid(level_id, tiles)

    # Если под ногами всё-таки оказалась твердь, поднимаемся выше.
    for _ in range(height):
        if spawn_row <= 0:
            break
        if not solid[spawn_row][max(0, min(spawn_col, width - 1))]:
            break
        spawn_row -= 1

    return LevelData(
        id=level_id,
        raw_rows=rows,
        tiles=tiles,
        solid=solid,
        spawn_col=max(0, min(spawn_col, max(0, width - 1))),
        spawn_row=max(0, min(spawn_row, max(0, height - 1))),
        entities=entities,
        transitions=transitions,
        width=width,
        height=height,
        theme=theme,
    )


def build_levels(level_info: dict) -> dict[str, LevelData]:
    """Строит LevelData для всех экранов 0..12."""
    result: dict[str, LevelData] = {}
    for level_id, info in level_info.items():
        result[level_id] = load_level(level_id, info.get("theme", "forest"))
    return result
