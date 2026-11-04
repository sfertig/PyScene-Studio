from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput
from .RightPannel import *

#This file contains both functions and import manager

class CenterPannel(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(420, 0), visible=False, active=False)
        self.size = Vector2D(sub.dim.x-840, sub.dim.y)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)
        self.screen = self.sub.screen

        self.title = self.child(Text(Assets.get_font("default-35"), "__init__", "white", Vector2D(self.size.x//2, 20), visible=False))

        self.data = data
        self.func = "__init__"
        self.right = RightPannel(sub, data)
        self.code = CodePannel(self.sub, self.data, self.right)
        

    def save(self): 
        self.right.attr.save()
        self.code.save()

    def update(self, func):
        if func != self.func and func is not None: 
            self.save()
            self.func = func
            self.title.set_text(func)
            self.code.set_func(func)

        self.code.update()
        self.right.update()

    def render(self):
        self.sub.clear()

        self.title.render_to(self.sub.screen)
        pygame.draw.line(self.sub.screen, "black", (10, 50), (self.size.x-20, 50))
        self.code.render()
        self.right.render()

        self.sub.render()

class CodePannel(GameObj):
    def __init__(self, sub: SubScreen, data, right: RightPannel):
        super().__init__(Vector2D(10, 55), visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, sub.dim.y-65)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.data = data
        self.args: Arguments = right.args
        self.code: list[CodeLine] = []
        self.set_func("__init__")

    def set_func(self, func):
        self.func = func
        self.args.set_func(func)
        self.active_line = 0

        #gen code
        self.code.clear()
        y = 5
        for i in range(20):
            self.code.append(CodeLine(y, self.sub, {}, func, i+1))
            y += self.code[-1].size.y
        #set code
        i = 0
        for line in self.data["functions"][func]["code"]:
            self.code[i].set_code(line)
            i += 1

    def save(self):
        lines = [line._code for line in self.code]
        while lines and not lines[-1]:
            lines.pop()
        self.data["functions"][self.func]["code"] = lines

    def update(self):
        line_to_delete = None
        for line in self.code:
            line.update()
            if line.active: self.active_line = line.num-1
            if line.DEL:
                line_to_delete = line
                break

        if line_to_delete and len(self.code) > 1:
            self.del_line(line_to_delete)
            return
        if line_to_delete:
            line_to_delete.DEL = False

        if Keys.is_pressed(Keys.up): self.move_active(-1)
        elif Keys.is_pressed(Keys.down): self.move_active(1)

        if Keys.is_pressed(Keys.enter) and self.code[self.active_line].active:
            line_index = max(0, min(self.active_line, len(self.code) - 1))
            line = self.code[line_index]
            split_at = max(0, min(line.cursor_index, len(line._code)))
            following = CodeLine(
                line.pos.y + line.size.y,
                self.sub,
                {},
                self.func,
                line_index + 2,
            )
            following.set_code(line._code[split_at:])
            line.set_code(line._code[:split_at])

            for existing in self.code[line_index + 1:]:
                existing.move_y(line.size.y)
            self.code.insert(line_index + 1, following)

            for num, existing in enumerate(self.code, start=1):
                existing.num = num
                existing.lineNum.set_text(str(num))

            line.active = False
            self.active_line = line_index + 1
            following.active = True
            following._on_active()
            following.set_cursor(0)

    def del_line(self, line):
        if len(self.code) == 1:
            return

        i = self.code.index(line)
        self.code.remove(line)
        for num, remaining in enumerate(self.code, start=1):
            if remaining.num != num:
                remaining.move_y(-line.size.y)
                remaining.num = num
                remaining.lineNum.set_text(str(num))

        self.active_line = min(i, len(self.code) - 1)
        for remaining in self.code:
            remaining.active = False
        active = self.code[self.active_line]
        active.active = True
        active._on_active()
        active.backspace_buffer = 15

    def move_active(self, dir):
        self.code[self.active_line].active = False
        self.active_line = max(0, min(len(self.code)-1, self.active_line+dir))
        self.code[self.active_line].active = True
        self.code[self.active_line]._on_active()


    def render(self):
        self.sub.clear()
        #pygame.draw.rect(self.sub.screen, "yellow", (0, 0, 100, 100)) #test to find the subscreen

        for line in self.code:
            line.render()

        self.sub.render()

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
        self.code = self.child(Text(self.font, "", "white", Vector2D(0, 0), "topleft", visible=False))
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
                self._code = (
                    self._code[:self.cursor_index - 1]
                    + self._code[self.cursor_index:]
                )
                self.set_code(self._code)
                self.set_cursor(self.cursor_index - 1)
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
