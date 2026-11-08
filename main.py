# -*- coding: utf-8 -*-
"""Запуск MINE-LINE QUEST — 2D pixel remake."""
from __future__ import annotations

import sys


def _smoke_test() -> int:
    """Тихая проверка сборки: запускает игру без окна и выходит."""
    from game.game import Game

    game = Game(headless=True)
    game.start_new_game()
    for _ in range(60):
        game.update(1.0 / 60.0)
        game.draw()
    game.show_victory()
    game.draw()
    game.running = False
    print("MINE-LINE QUEST smoke test OK")
    return 0


def main() -> int:
    if "--smoke-test" in sys.argv:
        return _smoke_test()

    from game.game import main as run_game

    run_game()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
