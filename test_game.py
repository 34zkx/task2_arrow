"""
自动测试：对照作业要求里的 T01~T06，另外加上飞出动画、飞出中的箭头规则、关卡可通关性。

运行方式：python test_game.py
用 SDL 的 dummy 驱动在后台跑，不会弹窗口，也不需要显示器。
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

import main

RESULTS = []


def check(no: str, title: str, condition: bool, detail: str = ""):
    RESULTS.append(condition)
    print(f"{no} {title} -> {'通过' if condition else '不通过'} {detail}")


def new_game() -> main.Game:
    return main.Game()


def pump(game: main.Game, frames: int = 1):
    """推进若干帧：draw_game 里会 update 所有箭头，并判定通关。"""
    for _ in range(frames):
        game.draw_game()


def settle(game: main.Game, limit: int = 300):
    """一直推进到没有箭头还在飞。"""
    for _ in range(limit):
        if not any(a.flying for a in game.arrows):
            return
        game.draw_game()


def free_arrow(game: main.Game):
    return next(a for a in game.arrows if a.alive and not a.flying and game.can_remove_arrow(a))


def blocked_arrow(game: main.Game):
    return next(a for a in game.arrows if a.alive and not a.flying and not game.can_remove_arrow(a))


def clear_level(game: main.Game, limit: int = 100) -> bool:
    """只点能飞出的箭头，直到清空棋盘；卡住就返回 False。"""
    for _ in range(limit):
        candidates = [a for a in game.arrows if a.alive and not a.flying and game.can_remove_arrow(a)]
        if not candidates:
            break
        game.handle_click(candidates[0].get_rect().center)
        settle(game)
    return game.check_level_complete()


def test_t01():
    game = new_game()
    game.load_level(0)
    arrow = free_arrow(game)
    game.handle_click(arrow.get_rect().center)
    flying = arrow.flying and arrow.alive  # 先进入飞出状态，而不是凭空消失
    settle(game)
    check("T01", "点击前方无阻挡的箭头", flying and not arrow.alive, "箭头飞出后消失")


def test_t02():
    game = new_game()
    game.load_level(2)
    arrow = blocked_arrow(game)
    total = len(game.arrows)
    game.handle_click(arrow.get_rect().center)
    check("T02", "点击前方有阻挡的箭头",
          arrow.alive and not arrow.flying and game.mistakes == 1 and len(game.arrows) == total,
          f"箭头保留，失误 {game.mistakes}")


def test_t03():
    game = new_game()
    game.load_level(3)
    arrow = next(a for a in game.arrows if a.col == 0 and a.direction == main.Direction.LEFT)
    game.handle_click(arrow.get_rect().center)
    settle(game)
    check("T03", "点击边缘且朝向棋盘外的箭头", not arrow.alive, "正常飞出，无越界异常")


def test_t04():
    game = new_game()
    game.load_level(0)
    cleared = clear_level(game)
    completed = game.state == main.GameState.LEVEL_COMPLETE
    game.load_level(game.current_level + 1)
    next_level = game.state == main.GameState.PLAYING and game.current_level == 1
    check("T04", "消除本关全部箭头",
          cleared and completed and next_level, "显示通关并进入下一关")


def test_t06():
    game = new_game()
    game.load_level(2)
    total = len(game.arrows)
    clear_level(game)
    game.mistakes = 1
    game.load_level(2)
    check("T06", "游戏进行中重新开始",
          game.mistakes == 0 and len(game.arrows) == total
          and all(a.alive and not a.flying for a in game.arrows), "布局和失误次数恢复")


def test_t05():
    game = new_game()
    game.load_level(2)
    total = len(game.arrows)
    game.mistakes = main.LEVELS[2].max_mistakes - 1
    arrow = blocked_arrow(game)
    game.handle_click(arrow.get_rect().center)
    failed = (game.state == main.GameState.GAME_OVER
              and game.mistakes == main.LEVELS[2].max_mistakes)
    game.load_level(game.current_level)   # 失败后允许重新开始
    restarted = (game.state == main.GameState.PLAYING and game.mistakes == 0
                 and len(game.arrows) == total)
    check("T05", "失误次数耗尽", failed and restarted, "显示失败并允许重新开始")


def test_t07():
    game = new_game()
    game.load_level(1)
    arrow = next(a for a in game.arrows if a.direction == main.Direction.RIGHT)
    start_x, start_y = arrow.get_position()
    game.handle_click(arrow.get_rect().center)
    entered_flight = arrow.flying and arrow.alive
    pump(game, 5)
    mid_x, mid_y = arrow.get_position()
    on_board_while_flying = arrow.alive
    settle(game)
    check("T07", "飞出动画",
          entered_flight and mid_x > start_x and mid_y == start_y
          and on_board_while_flying and not arrow.alive,
          f"位置 {start_x} -> {mid_x}，飞出窗口后才消失")


def test_t08():
    game = new_game()
    game.load_level(3)
    lower = next(a for a in game.arrows if (a.row, a.col) == (4, 2))   # 朝下，前方空
    upper = next(a for a in game.arrows if (a.row, a.col) == (0, 2))   # 被 lower 挡住
    game.handle_click(lower.get_rect().center)
    pump(game, 3)
    path_freed = game.can_remove_arrow(upper)
    game.handle_click(lower.get_rect().center)   # 正在飞的箭头点不到
    no_extra_mistake = game.mistakes == 0
    game.handle_click(upper.get_rect().center)
    check("T08", "飞出中的箭头",
          path_freed and no_extra_mistake and upper.flying, "不再挡路、也点不到")


def test_t09():
    game = new_game()
    solved = []
    for index in range(len(main.LEVELS)):
        game.load_level(index)
        solved.append(clear_level(game))
    check("T09", f"全部 {len(main.LEVELS)} 个关卡都存在通关顺序", all(solved), "逐关贪心点击验证")


def test_t10():
    game = new_game()
    window = pygame.Rect(0, 0, main.WINDOW_WIDTH, main.WINDOW_HEIGHT)

    game.load_level(0)
    game.draw_menu()
    menu_card, start = game.card_rect, game.start_button
    game.draw_game()
    board, bar, restart = game.board_rect, game.top_bar, game.restart_button

    game.state = main.GameState.LEVEL_COMPLETE
    game.draw_level_complete()
    result_card = game.card_rect

    fits = all(window.contains(r) for r in (menu_card, start, board, bar, restart, result_card))
    separated = (not board.colliderect(bar) and not board.colliderect(restart)
                 and not bar.colliderect(restart) and not menu_card.colliderect(start))
    check("T10", "界面布局",
          fits and separated, "开始按钮、状态条、棋盘、结果卡片都在窗口内且互不重叠")


if __name__ == "__main__":
    tests = (test_t01, test_t02, test_t03, test_t04, test_t05, test_t06,
             test_t07, test_t08, test_t09, test_t10)
    for test in tests:
        test()
    passed = sum(RESULTS)
    print(f"\n共 {len(RESULTS)} 项，通过 {passed} 项，失败 {len(RESULTS) - passed} 项")
