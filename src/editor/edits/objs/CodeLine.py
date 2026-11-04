from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput
from .RightPannel import *
from .CodeHighlighter import CodeHighlighter

class CodeLine(GameObj):
    def __init__(self, y, sub: SubScreen, data: dict, func, num):
        super().__init__(Vector2D(10, y), visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 37)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.font = Assets.get_font("default-35")
        self.lineNum = self.child(Text(self.font, str(num), "white", Vector2D(0, 0), "topleft", visible=False))

        self.codeSub = SubScreen(40, 0, self.size.x-40, self.size.y, Colors["bg"], self._sub.screen, self._sub)
        self.codeRect = pygame.Rect(0, 0, self.size.x-40, self.size.y)
        self.code = self.child(Text(self.font, "", "white", Vector2D(0, self.size.y/2), "centery", visible=False))
        self.highlighter = CodeHighlighter()
        self._code = ""

        self.num = num
        self.data = data
        self.func = func

        self.hovered = False
        self.active = False
        self.cursor_x = 0
        self.cursorTimer = self.child(Timer(0.5))
        self.show_cursor = False
        self.cursor_index = 0
        self.scroll_x = 0
        self.backspace_buffer = 0
        self.just_clicked = False
        self.selection = None
        self.error = None

        #flags
        self.DEL = False

    def move_y(self, ay):
        self.pos.y += ay
        self._sub.pos.y += ay

    def move_x(self, ax):
        self.pos.x += ax
        self._sub.pos.x += ax

    def set_code(self, code: str):
        self.code.set_text(code)
        self._code = code
        self.set_cursor(self.cursor_index)

    def _on_active(self):
        self.cursorTimer.start()
        self.show_cursor = True
        self.set_cursor(len(self._code))

    def set_cursor(self, index):
        self.cursor_index = max(0, min(index, len(self._code)))
        cursor_x = self.font.size(self._code[:self.cursor_index])[0]
        visible_width = self.codeSub.dim.x
        margin = min(20, visible_width // 4)
        if cursor_x - self.scroll_x < margin:
            self.scroll_x = max(0, cursor_x - margin)
        elif cursor_x - self.scroll_x > visible_width - margin:
            self.scroll_x = cursor_x - visible_width + margin
        max_scroll = max(0, self.font.size(self._code)[0] - visible_width + margin)
        self.scroll_x = max(0, min(max_scroll, self.scroll_x))
        self.update_horizontal_position()
        self.show_cursor = True
        self.cursorTimer.start()

    def scroll_horizontal(self, amount):
        visible_width = self.codeSub.dim.x
        margin = min(20, visible_width // 4)
        max_scroll = max(0, self.font.size(self._code)[0] - visible_width + margin)
        self.scroll_x = max(0, min(max_scroll, self.scroll_x + amount))
        self.update_horizontal_position()

    def update_horizontal_position(self):
        self.code.set_pos(Vector2D(-self.scroll_x, self.size.y / 2))
        self.cursor_x = self.font.size(self._code[:self.cursor_index])[0] - self.scroll_x + 1

    def update(self):
        self.just_clicked = False
        if self.cursorTimer.is_done():
            self.show_cursor = not self.show_cursor
            self.cursorTimer.start()

        mpos = self.codeSub.local_mouse_pos().to_int()
        self.hovered = self.codeRect.collidepoint(mpos)

        left_mouse_down = any(
            event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            for event in Game.events
        )
        if left_mouse_down or (Game.click and pygame.mouse.get_pressed()[0]):
            self.active = self.hovered
            if self.active:
                self.just_clicked = True
                self._on_active()
                self.set_cursor_from_x(mpos[0])

    def set_cursor_from_x(self, x):
        x = max(0, x + self.scroll_x)
        distances = [
            abs(self.font.size(self._code[:index])[0] - x)
            for index in range(len(self._code) + 1)
        ]
        self.set_cursor(distances.index(min(distances)))


    def render(self):
        self._sub.clear()
        self.codeSub.clear()

        if self.selection is not None:
            start, end, extends_to_end = self.selection
            left = self.font.size(self._code[:start])[0] - self.scroll_x
            right = (
                self.codeSub.dim.x
                if extends_to_end
                else self.font.size(self._code[:end])[0] - self.scroll_x
            )
            if extends_to_end and left < self.codeSub.dim.x:
                right = self.codeSub.dim.x
            if right > left:
                pygame.draw.rect(
                    self.codeSub.screen,
                    (65, 95, 145),
                    pygame.Rect(left, 0, right - left, self.size.y),
                )

        self.lineNum.render_to(self._sub.screen)
        text_y = (self.size.y - self.font.get_height()) // 2
        for start, segment, color in self.highlighter.get_segments(self._code):
            if not segment:
                continue
            x = self.font.size(self._code[:start])[0] - self.scroll_x
            rendered = self.font.render(segment, True, color)
            self.codeSub.screen.blit(rendered, (x, text_y))

        if self.error is not None:
            start = self.error["start"]
            end = self.error["end"]
            x1 = self.font.size(self._code[:start])[0] - self.scroll_x
            x2 = self.font.size(self._code[:end])[0] - self.scroll_x
            if x2 <= x1:
                x2 = x1 + 8
            x1 = max(0, x1)
            x2 = min(self.codeSub.dim.x, x2)
            if x2 > x1:
                pygame.draw.line(
                    self.codeSub.screen,
                    (255, 65, 65),
                    (x1, self.size.y - 2),
                    (x2, self.size.y - 2),
                    2,
                )

        if self.active:
            if self.show_cursor: pygame.draw.line(self.codeSub.screen, "white", (self.cursor_x, 4), (self.cursor_x, self.size.y-4), 2)

        self.codeSub.render()
        self._sub.render()
