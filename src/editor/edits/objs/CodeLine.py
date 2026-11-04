from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput
from .RightPannel import *

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
        self.backspace_buffer = 0

        #flags
        self.DEL = False

    def move_y(self, ay):
        self.pos.y += ay
        self._sub.pos.y += ay

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
        self.cursor_x = self.font.size(self._code[:self.cursor_index])[0] + 1
        self.show_cursor = True
        self.cursorTimer.start()

    def update(self):
        if self.cursorTimer.is_done():
            self.show_cursor = not self.show_cursor
            self.cursorTimer.start()

        mpos = self.codeSub.local_mouse_pos().to_int()
        self.hovered = self.codeRect.collidepoint(mpos)

        if Game.click:
            self.active = self.hovered
            if self.active:
                self._on_active()
                self.set_cursor_from_x(mpos[0])

        if not self.active: return

        for event in Game.events:
            if event.type == pygame.KEYDOWN:
                if event.key in (
                    pygame.K_BACKSPACE,
                    pygame.K_RETURN,
                    pygame.K_KP_ENTER,
                    pygame.K_LEFT,
                    pygame.K_RIGHT,
                    pygame.K_UP,
                    pygame.K_DOWN,
                    pygame.K_DELETE,
                ):
                    continue
                if event.unicode and event.unicode.isprintable():
                    inserted = event.unicode
                    self._code = (
                        self._code[:self.cursor_index]
                        + inserted
                        + self._code[self.cursor_index:]
                    )
                    self.set_code(self._code)
                    self.set_cursor(self.cursor_index + len(inserted))

        if Keys.is_pressed(Keys.left):
            self.set_cursor(self.cursor_index - 1)
        elif Keys.is_pressed(Keys.right):
            self.set_cursor(self.cursor_index + 1)

        self.backspace_buffer = max(0, self.backspace_buffer - 1)
        if Keys.is_held(Keys.backspace) and self.backspace_buffer == 0:
            if self.cursor_index == 0:
                self.DEL = True
            else:
                cursor_index = self.cursor_index - 1
                self._code = self._code[:cursor_index] + self._code[self.cursor_index:]
                self.code.set_text(self._code)
                self.set_cursor(cursor_index)
            self.backspace_buffer = 5
        elif not Keys.is_held(Keys.backspace):
            self.backspace_buffer = 0

    def set_cursor_from_x(self, x):
        x = max(0, x)
        distances = [
            abs(self.font.size(self._code[:index])[0] - x)
            for index in range(len(self._code) + 1)
        ]
        self.set_cursor(distances.index(min(distances)))


    def render(self):
        self._sub.clear()
        self.codeSub.clear()

        self.lineNum.render_to(self._sub.screen)
        self.code.render_to(self.codeSub.screen)

        if self.active:
            if self.show_cursor: pygame.draw.line(self.codeSub.screen, "white", (self.cursor_x, 4), (self.cursor_x, self.size.y-4), 2)

        self.codeSub.render()
        self._sub.render()
