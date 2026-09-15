"""
一箭又一箭 - Arrow Puzzle Game
"""
import pygame
import os
import sys
import random
from enum import Enum
from typing import List, Tuple, Optional

pygame.init()

# 界面文字里出现过的全部汉字，用来验证字体是否真的包含中文字形
NEEDED_GLYPHS = "。一下中为主了体余你入关到剩功单卡又可告喜回失头始字开恭戏成所找按数文新方显有本束格框次没消游用界的示空箭结能菜解警试误谜过返进通重键除面"

# 按名称查找的字体（pygame 会自动匹配系统里已安装的字体）
FONT_NAMES = (
    "microsoftyaheiui", "microsoftyahei", "msyh", "simhei", "dengxian", "simsun",
    "notosanscjksc", "notosanssc", "sourcehansanssc", "wqyzenhei",
    "wenquanyimicrohei", "pingfangsc", "stheiti", "heiti", "arialunicodems",
)

# 按文件路径查找的字体，覆盖 Windows / macOS / Linux 的常见位置
FONT_FILES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/Deng.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/NotoSansSC-VF.ttf",
    "C:/Windows/Fonts/ARIALUNI.TTF",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
)


def _supports_cjk(path: str) -> bool:
    """字体能打开、并且这些字符都有字形时才算可用。"""
    try:
        probe = pygame.font.Font(path, 20)
    except Exception:
        return False
    return all(probe.metrics(ch)[0] is not None for ch in NEEDED_GLYPHS)


def find_cjk_font() -> Optional[str]:
    for path in FONT_FILES:
        if os.path.exists(path) and _supports_cjk(path):
            return path
    for name in FONT_NAMES:
        path = pygame.font.match_font(name)
        if path and _supports_cjk(path):
            return path
    return None


FONT_PATH = find_cjk_font()
if FONT_PATH is None:
    print("警告：没有找到可用的中文字体，界面文字可能显示为方框。")


def load_font(size: int) -> pygame.font.Font:
    """统一的中文字体入口，找不到中文字体时退回 pygame 默认字体。"""
    return pygame.font.Font(FONT_PATH, size)


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 80
BOARD_OFFSET_X = 150
BOARD_OFFSET_Y = 150

class Direction(Enum):
    UP = 1
    DOWN = 2
    LEFT = 3
    RIGHT = 4


# 四个方向对应的单位向量，飞行动画和路径检测都用它算下一格
DIRECTION_VECTORS = {
    Direction.UP: (0, -1),
    Direction.DOWN: (0, 1),
    Direction.LEFT: (-1, 0),
    Direction.RIGHT: (1, 0),
}


class GameState(Enum):
    MENU = 1
    PLAYING = 2
    LEVEL_COMPLETE = 3
    GAME_OVER = 4
    WIN = 5

class Arrow:
    FLY_SPEED = 18  # 飞出速度，单位是像素/帧（60 帧/秒下约 1080 像素/秒）

    def __init__(self, row: int, col: int, direction: Direction):
        self.row = row
        self.col = col
        self.direction = direction
        self.alive = True
        self.flying = False
        self.fly_offset = 0.0
        self.shaking = False
        self.shake_timer = 0
        self.shake_duration = 30
        self.shake_offset_x = 0
        self.shake_offset_y = 0

    def get_position(self) -> Tuple[int, int]:
        dx, dy = DIRECTION_VECTORS[self.direction]
        x = self.col * CELL_SIZE + BOARD_OFFSET_X + CELL_SIZE // 2 + dx * self.fly_offset
        y = self.row * CELL_SIZE + BOARD_OFFSET_Y + CELL_SIZE // 2 + dy * self.fly_offset
        return int(x), int(y)
    
    def get_rect(self) -> pygame.Rect:
        x, y = self.get_position()
        return pygame.Rect(x - CELL_SIZE // 2, y - CELL_SIZE // 2, CELL_SIZE, CELL_SIZE)

    def get_shape(self, cx: int, cy: int) -> Tuple[List[Tuple[int, int]], pygame.Rect]:
        """返回箭头（三角形）的顶点和箭杆（矩形），已按方向旋转并移到格子中心。

        先在局部坐标里按“朝右的箭头”写好，再整体旋转，这样四个方向共用一套数值。
        箭头用绘图而不是 ▲▼◀▶ 字符，避免系统缺字形时显示成方框。
        """
        ARROW_HALF = 23   # 箭头总长的一半
        HEAD_BASE = 5     # 箭头三角形底边到中心的距离
        HEAD_HALF = 14    # 箭头三角形底边半宽
        SHAFT_HALF = 4    # 箭杆半宽

        def place(x: int, y: int) -> Tuple[int, int]:
            """把局部坐标旋转到当前方向，再平移到 (cx, cy)。"""
            if self.direction == Direction.UP:
                x, y = y, -x
            elif self.direction == Direction.DOWN:
                x, y = -y, x
            elif self.direction == Direction.LEFT:
                x, y = -x, -y
            return cx + x, cy + y

        head = [place(ARROW_HALF, 0), place(HEAD_BASE, -HEAD_HALF), place(HEAD_BASE, HEAD_HALF)]
        corner_a = place(-ARROW_HALF, -SHAFT_HALF)
        corner_b = place(HEAD_BASE, SHAFT_HALF)
        left, right = sorted((corner_a[0], corner_b[0]))
        top, bottom = sorted((corner_a[1], corner_b[1]))
        shaft = pygame.Rect(left, top, right - left, bottom - top)
        return head, shaft

    def draw(self, screen: pygame.Surface):
        if not self.alive:
            return

        x, y = self.get_position()

        if self.shaking:
            self.shake_offset_x = random.randint(-3, 3)
            self.shake_offset_y = random.randint(-3, 3)
        else:
            self.shake_offset_x = 0
            self.shake_offset_y = 0

        x += self.shake_offset_x
        y += self.shake_offset_y

        color = (70, 130, 180)
        if self.shaking:
            color = (220, 80, 60)

        pygame.draw.rect(screen, color, (x - CELL_SIZE // 2 + 5, y - CELL_SIZE // 2 + 5,
                                        CELL_SIZE - 10, CELL_SIZE - 10), border_radius=10)

        head, shaft = self.get_shape(x, y)
        pygame.draw.rect(screen, (255, 255, 255), shaft, border_radius=2)
        pygame.draw.polygon(screen, (255, 255, 255), head)
    
    def start_shake(self):
        self.shaking = True
        self.shake_timer = self.shake_duration

    def start_fly(self):
        """进入飞出状态，之后由 update() 逐帧推到窗口外才真正消失。"""
        self.flying = True

    def update(self):
        if self.shaking:
            self.shake_timer -= 1
            if self.shake_timer <= 0:
                self.shaking = False
        if self.flying:
            self.fly_offset += self.FLY_SPEED
            x, y = self.get_position()
            if not (-CELL_SIZE < x < WINDOW_WIDTH + CELL_SIZE
                    and -CELL_SIZE < y < WINDOW_HEIGHT + CELL_SIZE):
                self.flying = False
                self.alive = False

class Level:
    def __init__(self, grid: List[List[int]], max_mistakes: int):
        self.grid = grid
        self.max_mistakes = max_mistakes
        self.rows = len(grid)
        self.cols = len(grid[0]) if grid else 0
    
    def get_arrow_count(self) -> int:
        count = 0
        for row in self.grid:
            for cell in row:
                if cell != 0:
                    count += 1
        return count

LEVELS = [
    Level([
        [4, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 3],
        [0, 0, 0, 0, 0],
    ], 3),
    
    Level([
        [4, 0, 0, 0, 0],
        [0, 0, 0, 0, 2],
        [0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 0, 0, 3],
    ], 3),
    
    Level([
        [4, 0, 2, 0, 4],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [3, 0, 2, 0, 3],
    ], 3),
    
    Level([
        [4, 0, 2, 0, 4],
        [0, 0, 0, 0, 0],
        [3, 0, 0, 0, 1],
        [0, 0, 0, 0, 0],
        [3, 0, 2, 0, 3],
    ], 3),
]

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("一箭又一箭")
        self.clock = pygame.time.Clock()
        self.font_large = load_font(64)
        self.font_medium = load_font(48)
        self.font_small = load_font(36)
        self.font_tiny = load_font(24)
        
        self.state = GameState.MENU
        self.current_level = 0
        self.mistakes = 0
        self.arrows: List[Arrow] = []
        self.selected_arrow: Optional[Arrow] = None
        self.level_complete_timer = 0
        self.game_over_timer = 0
        
        self.start_button = pygame.Rect(WINDOW_WIDTH // 2 - 100, 400, 200, 60)
        self.restart_button = pygame.Rect(WINDOW_WIDTH // 2 - 100, 400, 200, 60)
        self.next_button = pygame.Rect(WINDOW_WIDTH // 2 - 100, 400, 200, 60)
        
    def load_level(self, level_index: int):
        if level_index >= len(LEVELS):
            self.state = GameState.WIN
            return
            
        self.current_level = level_index
        self.mistakes = 0
        self.arrows = []
        self.selected_arrow = None
        
        level = LEVELS[level_index]
        for row in range(level.rows):
            for col in range(level.cols):
                cell = level.grid[row][col]
                if cell != 0:
                    direction = Direction(cell)
                    self.arrows.append(Arrow(row, col, direction))
        
        self.state = GameState.PLAYING
    
    def can_remove_arrow(self, arrow: Arrow) -> bool:
        level = LEVELS[self.current_level]

        if arrow.direction == Direction.RIGHT:
            for col in range(arrow.col + 1, level.cols):
                for a in self.arrows:
                    if a.alive and not a.flying and a.row == arrow.row and a.col == col:
                        return False
            return True

        elif arrow.direction == Direction.LEFT:
            for col in range(arrow.col - 1, -1, -1):
                for a in self.arrows:
                    if a.alive and not a.flying and a.row == arrow.row and a.col == col:
                        return False
            return True

        elif arrow.direction == Direction.DOWN:
            for row in range(arrow.row + 1, level.rows):
                for a in self.arrows:
                    if a.alive and not a.flying and a.row == row and a.col == arrow.col:
                        return False
            return True

        elif arrow.direction == Direction.UP:
            for row in range(arrow.row - 1, -1, -1):
                for a in self.arrows:
                    if a.alive and not a.flying and a.row == row and a.col == arrow.col:
                        return False
            return True

        return False

    def check_level_complete(self) -> bool:
        for arrow in self.arrows:
            if arrow.alive:
                return False
        return True

    def handle_click(self, pos: Tuple[int, int]):
        if self.state == GameState.PLAYING:
            for arrow in self.arrows:
                # 正在飞出的箭头不再接受点击
                if not arrow.alive or arrow.flying:
                    continue
                if not arrow.get_rect().collidepoint(pos):
                    continue
                if self.can_remove_arrow(arrow):
                    arrow.start_fly()
                else:
                    arrow.start_shake()
                    self.mistakes += 1
                    level = LEVELS[self.current_level]
                    if self.mistakes >= level.max_mistakes:
                        self.state = GameState.GAME_OVER
                        self.game_over_timer = 120
                break
    
    def draw_menu(self):
        self.screen.fill((30, 30, 50))
        
        title = self.font_large.render("一箭又一箭", True, (255, 255, 255))
        title_rect = title.get_rect(center=(WINDOW_WIDTH // 2, 150))
        self.screen.blit(title, title_rect)
        
        subtitle = self.font_small.render("箭头解谜游戏", True, (180, 180, 180))
        subtitle_rect = subtitle.get_rect(center=(WINDOW_WIDTH // 2, 220))
        self.screen.blit(subtitle, subtitle_rect)
        
        instructions = [
            "点击箭头使其飞出棋盘",
            "箭头前方不能有其他箭头阻挡",
            "在有限失误次数内清除所有箭头",
        ]
        for i, text in enumerate(instructions):
            inst = self.font_tiny.render(text, True, (150, 150, 150))
            inst_rect = inst.get_rect(center=(WINDOW_WIDTH // 2, 300 + i * 30))
            self.screen.blit(inst, inst_rect)
        
        pygame.draw.rect(self.screen, (70, 130, 180), self.start_button, border_radius=10)
        start_text = self.font_medium.render("开始游戏", True, (255, 255, 255))
        start_rect = start_text.get_rect(center=self.start_button.center)
        self.screen.blit(start_text, start_rect)
    
    def draw_game(self):
        self.screen.fill((30, 30, 50))
        
        level_text = self.font_small.render(f"关卡: {self.current_level + 1}/{len(LEVELS)}", True, (255, 255, 255))
        self.screen.blit(level_text, (20, 20))
        
        remaining = sum(1 for a in self.arrows if a.alive)
        remaining_text = self.font_small.render(f"剩余箭头: {remaining}", True, (255, 255, 255))
        self.screen.blit(remaining_text, (20, 60))
        
        level = LEVELS[self.current_level]
        mistakes_text = self.font_small.render(f"失误次数: {self.mistakes}/{level.max_mistakes}", True, (255, 255, 255))
        self.screen.blit(mistakes_text, (20, 100))
        
        for row in range(level.rows):
            for col in range(level.cols):
                x = col * CELL_SIZE + BOARD_OFFSET_X
                y = row * CELL_SIZE + BOARD_OFFSET_Y
                pygame.draw.rect(self.screen, (50, 50, 70), (x, y, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(self.screen, (70, 70, 90), (x, y, CELL_SIZE, CELL_SIZE), 2)
        
        for arrow in self.arrows:
            arrow.update()
            arrow.draw(self.screen)

        # 最后一个箭头完全飞出棋盘后才算通关，这样动画能播完
        if self.check_level_complete():
            self.state = GameState.LEVEL_COMPLETE
            self.level_complete_timer = 120
        
        restart_text = self.font_small.render("按 R 重新开始", True, (150, 150, 150))
        self.screen.blit(restart_text, (WINDOW_WIDTH - 200, WINDOW_HEIGHT - 40))
    
    def draw_level_complete(self):
        self.screen.fill((30, 50, 30))
        
        complete_text = self.font_large.render("关卡通过!", True, (100, 255, 100))
        complete_rect = complete_text.get_rect(center=(WINDOW_WIDTH // 2, 200))
        self.screen.blit(complete_text, complete_rect)
        
        if self.current_level + 1 < len(LEVELS):
            next_text = self.font_small.render("按空格键进入下一关", True, (180, 180, 180))
            next_rect = next_text.get_rect(center=(WINDOW_WIDTH // 2, 300))
            self.screen.blit(next_text, next_rect)
        else:
            win_text = self.font_medium.render("恭喜通关!", True, (255, 215, 0))
            win_rect = win_text.get_rect(center=(WINDOW_WIDTH // 2, 300))
            self.screen.blit(win_text, win_rect)
    
    def draw_game_over(self):
        self.screen.fill((50, 30, 30))
        
        over_text = self.font_large.render("游戏结束", True, (255, 100, 100))
        over_rect = over_text.get_rect(center=(WINDOW_WIDTH // 2, 200))
        self.screen.blit(over_text, over_rect)
        
        retry_text = self.font_small.render("按 R 重试本关", True, (180, 180, 180))
        retry_rect = retry_text.get_rect(center=(WINDOW_WIDTH // 2, 300))
        self.screen.blit(retry_text, retry_rect)
    
    def draw_win(self):
        self.screen.fill((50, 50, 30))
        
        win_text = self.font_large.render("恭喜通关!", True, (255, 215, 0))
        win_rect = win_text.get_rect(center=(WINDOW_WIDTH // 2, 200))
        self.screen.blit(win_text, win_rect)
        
        win2_text = self.font_medium.render("你成功消除了所有箭头!", True, (200, 200, 100))
        win2_rect = win2_text.get_rect(center=(WINDOW_WIDTH // 2, 280))
        self.screen.blit(win2_text, win2_rect)
        
        menu_text = self.font_small.render("按 ESC 返回主菜单", True, (180, 180, 180))
        menu_rect = menu_text.get_rect(center=(WINDOW_WIDTH // 2, 380))
        self.screen.blit(menu_text, menu_rect)
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.state == GameState.MENU:
                            if self.start_button.collidepoint(event.pos):
                                self.load_level(0)
                        elif self.state == GameState.PLAYING:
                            self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state in [GameState.WIN, GameState.LEVEL_COMPLETE]:
                            self.state = GameState.MENU
                    elif event.key == pygame.K_r:
                        if self.state == GameState.PLAYING or self.state == GameState.GAME_OVER:
                            self.load_level(self.current_level)
                    elif event.key == pygame.K_SPACE:
                        if self.state == GameState.LEVEL_COMPLETE:
                            if self.current_level + 1 < len(LEVELS):
                                self.load_level(self.current_level + 1)
                            else:
                                self.state = GameState.WIN
            
            if self.state == GameState.MENU:
                self.draw_menu()
            elif self.state == GameState.PLAYING:
                self.draw_game()
            elif self.state == GameState.LEVEL_COMPLETE:
                self.draw_level_complete()
            elif self.state == GameState.GAME_OVER:
                self.draw_game_over()
            elif self.state == GameState.WIN:
                self.draw_win()
            
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
