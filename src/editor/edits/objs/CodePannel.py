from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput
from .RightPannel import *

from .CodeLine import CodeLine

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
        #set code
        y = 5
        i = 0
        for line in self.data["functions"][func]["code"]:
            self.code.append(CodeLine(y, self.sub, {}, func, i+1))
            y += self.code[-1].size.y
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
            line.DEL = False
            return

        i = self.code.index(line)
        if i == 0 and line._code:
            line.DEL = False
            return

        cursor_index = 0
        if i > 0:
            previous = self.code[i - 1]
            cursor_index = len(previous._code)
            previous.set_code(previous._code + line._code)

        self.code.remove(line)
        for num, remaining in enumerate(self.code, start=1):
            if remaining.num != num:
                remaining.move_y(-line.size.y)
                remaining.num = num
                remaining.lineNum.set_text(str(num))

        self.active_line = max(0, i - 1)
        for remaining in self.code:
            remaining.active = False
        active = self.code[self.active_line]
        active.active = True
        if i > 0:
            active.set_cursor(cursor_index)
        else:
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

