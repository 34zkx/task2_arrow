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

# 界面文案里出现过的全部汉字，用来验证字体是否真的包含这些字形
NEEDED_GLYPHS = "。一上下中为主了他会住体余你入全共关其出击到前剩加动单卡即又可告喜回失头始字它完就并序开恭戏所找把按挡掉数文新方显晃有本机束格框棋次没油消清游点用界的盘示空箭结继续耗能菜被警试误过返还进送通部都里重键限面顺飞"

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

# 粗体优先级更高，标题用它更有分量；找不到粗体就退回常规字重
BOLD_FONT_FILES = (
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/Dengb.ttf",
) + FONT_FILES


def _supports_cjk(path: str) -> bool:
    """字体能打开、并且这些字符都有字形时才算可用。"""
    try:
        probe = pygame.font.Font(path, 20)
    except Exception:
        return False
    return all(probe.metrics(ch)[0] is not None for ch in NEEDED_GLYPHS)


def find_cjk_font(bold: bool = False) -> Optional[str]:
    for path in (BOLD_FONT_FILES if bold else FONT_FILES):
        if os.path.exists(path) and _supports_cjk(path):
            return path
    for name in FONT_NAMES:
        path = pygame.font.match_font(name, bold=bold)
        if path and _supports_cjk(path):
            return path
    return None


FONT_PATH = find_cjk_font()
FONT_PATH_BOLD = find_cjk_font(bold=True) or FONT_PATH
if FONT_PATH is None:
    print("警告：没有找到可用的中文字体，界面文字可能显示为方框。")


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """统一的中文字体入口，找不到中文字体时退回 pygame 默认字体。"""
    return pygame.font.Font(FONT_PATH_BOLD if bold else FONT_PATH, size)


WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
CELL_SIZE = 80
BOARD_OFFSET_X = 150
BOARD_OFFSET_Y = 150


# ---------------- 界面配色 ----------------
BG_TOP = (32, 35, 60)          # 背景渐变的上端
BG_BOTTOM = (13, 14, 26)       # 背景渐变的下端
PANEL = (40, 44, 68)           # 卡片底色
PANEL_EDGE = (62, 68, 102)     # 卡片描边
CHIP = (50, 55, 84)            # 状态条里的小格子
CELL = (44, 48, 74)            # 棋盘空格
CELL_EDGE = (62, 68, 100)
CELL_HOVER = (58, 64, 96)      # 鼠标所在的格子
TILE = (74, 132, 198)          # 箭头方块
TILE_HOVER = (100, 160, 228)   # 鼠标悬停且可以飞出
TILE_WARN = (208, 88, 76)      # 鼠标悬停但前方被挡住
TEXT = (236, 239, 250)
TEXT_DIM = (146, 152, 180)
ACCENT = (255, 198, 92)
GREEN = (112, 216, 150)
RED = (240, 112, 102)
GOLD = (255, 206, 84)
SHADOW = (9, 10, 18)


def shade(color, delta: int):
    """整体调亮或调暗一个颜色，用来算高光和描边。"""
    return tuple(max(0, min(255, c + delta)) for c in color)


def draw_panel(surface, rect, radius: int = 18, fill=PANEL, edge=PANEL_EDGE, shadow: int = 6):
    """带投影和描边的圆角卡片，界面里的面板都用它画。"""
    if shadow:
        pygame.draw.rect(surface, SHADOW, rect.move(0, shadow), border_radius=radius)
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, edge, rect, 2, border_radius=radius)


def draw_text(surface, text, font, pos, color=TEXT, shadow=True, anchor: str = "center"):
    """带投影的文字，在深色背景上更清楚；返回文字矩形方便继续排版。

    anchor 就是 Rect 的对齐方式，比如 center / midleft / topleft。
    """
    if shadow:
        dark = font.render(text, True, SHADOW)
        surface.blit(dark, dark.get_rect(**{anchor: (pos[0], pos[1] + 2)}))
    label = font.render(text, True, color)
    rect = label.get_rect(**{anchor: pos})
    surface.blit(label, rect)
    return rect


def draw_button(surface, rect, label, font, hover: bool = False, fill=TILE, hover_fill=TILE_HOVER):
    """圆角药丸按钮，鼠标悬停时变亮。"""
    base = hover_fill if hover else fill
    draw_panel(surface, rect, radius=rect.height // 2, fill=base,
               edge=shade(base, 34 if hover else 16), shadow=5)
    draw_text(surface, label, font, rect.center, (255, 255, 255))


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

    def draw(self, screen: pygame.Surface, highlight: bool = False, warn: bool = False):
        """highlight：鼠标停在这个格子上；warn：它前方被挡住、点了会算失误。"""
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

        if self.shaking:
            color = TILE_WARN
        elif highlight and warn:
            color = TILE_WARN
        elif highlight:
            color = TILE_HOVER
        else:
            color = TILE

        tile = pygame.Rect(0, 0, CELL_SIZE - 12, CELL_SIZE - 12)
        tile.center = (x, y + 4)
        pygame.draw.rect(screen, SHADOW, tile, border_radius=14)   # 方块自身的投影
        tile.centery -= 4
        pygame.draw.rect(screen, color, tile, border_radius=14)
        # 顶部高光，方块看起来有点立体感
        gloss = pygame.Rect(tile.x + 7, tile.y + 5, tile.width - 14, tile.height // 3)
        pygame.draw.rect(screen, shade(color, 26), gloss, border_radius=9)

        # 箭头先画一层深色影子，再叠白色的，看起来是浮在方块上的
        for offset, fill in ((3, SHADOW), (0, (255, 255, 255))):
            head, shaft = self.get_shape(x, y + offset)
            pygame.draw.rect(screen, fill, shaft, border_radius=2)
            pygame.draw.polygon(screen, fill, head)
    
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
        self.font_title = load_font(70, bold=True)
        self.font_medium = load_font(30, bold=True)
        self.font_small = load_font(24)
        self.font_tiny = load_font(18)
        self.background = self.build_background()

        self.state = GameState.MENU
        self.current_level = 0
        self.mistakes = 0
        self.arrows: List[Arrow] = []
        self.selected_arrow: Optional[Arrow] = None
        self.level_complete_timer = 0
        self.game_over_timer = 0

        self.top_bar = pygame.Rect(24, 16, WINDOW_WIDTH - 48, 96)
        self.start_button = pygame.Rect(0, 0, 220, 62)
        self.start_button.center = (WINDOW_WIDTH // 2, 478)
        self.restart_button = pygame.Rect(WINDOW_WIDTH - 212, WINDOW_HEIGHT - 84, 188, 54)
        # 布局矩形留成属性，测试里可以直接检查有没有互相压住
        self.board_rect = pygame.Rect(0, 0, 0, 0)
        self.card_rect = pygame.Rect(0, 0, 0, 0)

    def build_background(self) -> pygame.Surface:
        """竖直渐变背景，只在启动时生成一次，不用每帧重画。"""
        surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        for y in range(WINDOW_HEIGHT):
            t = y / (WINDOW_HEIGHT - 1)
            color = [int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)]
            pygame.draw.line(surface, color, (0, y), (WINDOW_WIDTH, y))
        return surface
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
        if self.state != GameState.PLAYING:
            return
        if self.restart_button.collidepoint(pos):   # 右下角的重启按钮
            self.load_level(self.current_level)
            return
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
        self.screen.blit(self.background, (0, 0))
        mouse = pygame.mouse.get_pos()

        title_y = 156
        draw_text(self.screen, "一箭又一箭", self.font_title, (WINDOW_WIDTH // 2, title_y), ACCENT)
        accent = pygame.Rect(0, 0, 112, 6)
        accent.center = (WINDOW_WIDTH // 2, title_y + 56)
        pygame.draw.rect(self.screen, ACCENT, accent, border_radius=3)
        draw_text(self.screen, "按顺序把箭头送出棋盘", self.font_small,
                  (WINDOW_WIDTH // 2, 250), TEXT_DIM)

        # 玩法说明卡片
        self.card_rect = pygame.Rect(120, 288, 560, 148)
        draw_panel(self.screen, self.card_rect)
        tips = [
            "点击箭头：前方没有其他箭头挡住，它就会飞出棋盘",
            "前方被挡住还点击：箭头会晃动，并消耗一次失误机会",
            f"共 {len(LEVELS)} 关，清空棋盘即可进入下一关",
        ]
        for i, tip in enumerate(tips):
            y = self.card_rect.y + 42 + i * 36
            pygame.draw.circle(self.screen, ACCENT, (self.card_rect.x + 34, y), 5)
            draw_text(self.screen, tip, self.font_tiny, (self.card_rect.x + 56, y),
                      TEXT_DIM, anchor="midleft")

        draw_button(self.screen, self.start_button, "开始游戏", self.font_medium,
                    hover=self.start_button.collidepoint(mouse))

    def draw_game(self):
        self.screen.blit(self.background, (0, 0))
        level = LEVELS[self.current_level]
        mouse = pygame.mouse.get_pos()

        # 顶部状态条：关卡 / 剩余箭头 / 失误次数
        draw_panel(self.screen, self.top_bar, radius=20)
        chips = [
            ("关卡", f"{self.current_level + 1} / {len(LEVELS)}", TEXT),
            ("剩余箭头", f"{sum(1 for a in self.arrows if a.alive)}", TEXT),
            ("失误次数", f"{self.mistakes} / {level.max_mistakes}",
             RED if self.mistakes else GREEN),
        ]
        chip_width = (self.top_bar.width - 40) // 3
        for i, (label, value, color) in enumerate(chips):
            chip = pygame.Rect(self.top_bar.x + 16 + i * chip_width, self.top_bar.y + 14,
                               chip_width - 8, self.top_bar.height - 28)
            pygame.draw.rect(self.screen, CHIP, chip, border_radius=14)
            draw_text(self.screen, label, self.font_tiny, (chip.centerx, chip.y + 18),
                      TEXT_DIM, shadow=False)
            draw_text(self.screen, value, self.font_medium, (chip.centerx, chip.y + 46),
                      color, shadow=False)

        # 棋盘底板
        self.board_rect = pygame.Rect(BOARD_OFFSET_X - 20, BOARD_OFFSET_Y - 20,
                                      level.cols * CELL_SIZE + 40, level.rows * CELL_SIZE + 40)
        draw_panel(self.screen, self.board_rect, radius=24, fill=shade(PANEL, -10), shadow=8)

        # 鼠标停在哪一格：可以飞出的高亮成蓝色，被挡住的提示成红色
        hover = None
        if self.state == GameState.PLAYING:
            col = (mouse[0] - BOARD_OFFSET_X) // CELL_SIZE
            row = (mouse[1] - BOARD_OFFSET_Y) // CELL_SIZE
            if 0 <= row < level.rows and 0 <= col < level.cols:
                hover = next((a for a in self.arrows
                              if a.alive and not a.flying and a.row == row and a.col == col), None)

        for row in range(level.rows):
            for col in range(level.cols):
                cell = pygame.Rect(col * CELL_SIZE + BOARD_OFFSET_X + 4,
                                   row * CELL_SIZE + BOARD_OFFSET_Y + 4,
                                   CELL_SIZE - 8, CELL_SIZE - 8)
                fill = CELL_HOVER if (hover and (hover.row, hover.col) == (row, col)) else CELL
                pygame.draw.rect(self.screen, fill, cell, border_radius=14)
                pygame.draw.rect(self.screen, CELL_EDGE, cell, 2, border_radius=14)

        for arrow in self.arrows:
            arrow.update()
            hovered = arrow is hover
            arrow.draw(self.screen, highlight=hovered,
                       warn=hovered and not self.can_remove_arrow(arrow))

        # 最后一个箭头完全飞出棋盘后才算通关，这样动画能播完
        if self.check_level_complete():
            self.state = GameState.LEVEL_COMPLETE
            self.level_complete_timer = 120

        draw_text(self.screen, "把箭头全部送出棋盘", self.font_tiny,
                  (self.restart_button.centerx, self.restart_button.y - 20),
                  TEXT_DIM, shadow=False)
        draw_button(self.screen, self.restart_button, "重新开始 R", self.font_small,
                    hover=self.restart_button.collidepoint(mouse),
                    fill=shade(PANEL, 18), hover_fill=shade(PANEL, 44))

    def draw_level_complete(self):
        self.screen.blit(self.background, (0, 0))
        self.card_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, 168, 500, 264)
        draw_panel(self.screen, self.card_rect, radius=24, shadow=8)
        if self.current_level + 1 >= len(LEVELS):
            draw_text(self.screen, "全部通关！", self.font_title, (WINDOW_WIDTH // 2, 246), GOLD)
            draw_text(self.screen, "你清掉了所有关卡里的箭头", self.font_small,
                      (WINDOW_WIDTH // 2, 328), TEXT_DIM)
            hint = "按空格键结束游戏"
        else:
            draw_text(self.screen, "本关通过！", self.font_title, (WINDOW_WIDTH // 2, 246), GREEN)
            draw_text(self.screen, f"还剩 {len(LEVELS) - self.current_level - 1} 关，继续加油",
                      self.font_small, (WINDOW_WIDTH // 2, 328), TEXT_DIM)
            hint = "按空格键进入下一关"
        draw_text(self.screen, hint, self.font_medium, (WINDOW_WIDTH // 2, 390), ACCENT)

    def draw_game_over(self):
        self.screen.blit(self.background, (0, 0))
        self.card_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, 168, 500, 264)
        draw_panel(self.screen, self.card_rect, radius=24, shadow=8)
        draw_text(self.screen, "失误用完了", self.font_title, (WINDOW_WIDTH // 2, 246), RED)
        level = LEVELS[self.current_level]
        draw_text(self.screen, f"本关失误 {self.mistakes} 次，上限 {level.max_mistakes} 次",
                  self.font_small, (WINDOW_WIDTH // 2, 328), TEXT_DIM)
        draw_text(self.screen, "按 R 重试本关", self.font_medium, (WINDOW_WIDTH // 2, 390), ACCENT)

    def draw_win(self):
        self.screen.blit(self.background, (0, 0))
        self.card_rect = pygame.Rect(WINDOW_WIDTH // 2 - 250, 168, 500, 264)
        draw_panel(self.screen, self.card_rect, radius=24, shadow=8)
        draw_text(self.screen, "恭喜通关！", self.font_title, (WINDOW_WIDTH // 2, 246), GOLD)
        draw_text(self.screen, "所有关卡里的箭头都被你清空了", self.font_small,
                  (WINDOW_WIDTH // 2, 328), TEXT_DIM)
        draw_text(self.screen, "按 ESC 返回主菜单", self.font_medium, (WINDOW_WIDTH // 2, 390), ACCENT)
    
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
