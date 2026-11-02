import colorsys

from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput

#This file contains both functions and import manager

class LeftPannel(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(0, 0), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.imports = self.child(Imports(self.sub, data))
        self.functions = self.child(Functions(self.sub, data))

    def update(self):
        self.imports.update()
        self.functions.update()

    def render(self):
        self.sub.clear()

        self.imports.render()
        self.functions.render()

        self.sub.render()

class Imports(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(0, 0), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y//2-5)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)
        self.min_sub = SubScreen(5, 40, self.size.x-10, self.size.y-50, Colors["bg"], self._sub.screen, self._sub)
        self.show_sub = SubScreen(0, 50, self.min_sub.dim.x, self.min_sub.dim.y-50, Colors["bg"], self.min_sub.screen, self.min_sub)
        self.abs = pygame.Rect(self.show_sub.get_absolute_pos().to_int(), self.show_sub.dim.to_int())
        self.data = data

        self.input = StrInput(5, 5, 300, 40, "", self.min_sub)
        self.input_rect = pygame.Rect((3, 3), (303, 43))
        self.input_btn = btn(self.min_sub.dim.x-70, 5, 50, 40, "ADD", self.min_sub, -1, 5, Colors["b"])

        self.title = self.child(Text(Assets.get_font("default-35"), "Imports:", "white", Vector2D(self.size.x//2, 20), visible=False))

        self.items: list[Item] = []
        self.gen()

    def gen(self):
        self.items.clear()
        y = 5
        for func in self.data["imports"]:
            self.items.append(self.child(Item(y, func, self.show_sub, False)))
            y += self.items[-1].size.y+10


    def update(self):
        if self.abs.collidepoint(pygame.mouse.get_pos()):
            change = 0
            for event in Game.events:
                if event.type == pygame.MOUSEWHEEL: change = event.y*10
            if change != 0:
                for item in self.items:
                    item.scroll(change)

        for item in self.items:
            item.update()
            if item.Del.hovered and Keys.is_pressed(Keys.enter):
                self.items.remove(item)
                self.data["imports"].remove(item.text.text)
                self.gen()

        self.input.update()
        self.input_btn.update()

        if self.input_btn.pressed:
            name = self.input.text.text
            if name in self.data["imports"] or name == "": return
            else:
                self.input.text.set_text("")
                self.data["imports"].append(name)
                self.gen()



    def render(self):
        self._sub.clear()
        self.min_sub.clear()
        self.show_sub.clear()

        self.title.render_to(self._sub.screen)

        for item in self.items:
            item.render()

        pygame.draw.rect(self.min_sub.screen, Colors["pannel"], self.input_rect)
        self.input.render()
        self.input_btn.render()
        self.show_sub.render()
        self.min_sub.render()
        self._sub.render()

class Functions(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(0, sub.dim.y//2+5), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y//2-5)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)
        self.min_sub = SubScreen(5, 40, self.size.x-10, self.size.y-50, Colors["bg"], self._sub.screen, self._sub)
        self.show_sub = SubScreen(0, 50, self.min_sub.dim.x, self.min_sub.dim.y-50, Colors["bg"], self.min_sub.screen, self.min_sub)
        self.abs = pygame.Rect(self.show_sub.get_absolute_pos().to_int(), self.show_sub.dim.to_int())
        self.data = data

        self.input = StrInput(5, 5, 300, 40, "", self.min_sub)
        self.input_rect = pygame.Rect((3, 3), (303, 43))
        self.input_btn = btn(self.min_sub.dim.x-70, 5, 50, 40, "ADD", self.min_sub, -1, 5, Colors["b"])

        self.title = self.child(Text(Assets.get_font("default-35"), "Functions:", "white", Vector2D(self.size.x//2, 20), visible=False))

        self.items: list[Item] = []
        self.gen()

    def gen(self):
        self.items.clear()
        y = 5
        for func in self.data["functions"]:
            self.items.append(self.child(Item(y, func, self.show_sub)))
            y += self.items[-1].size.y+10


    def update(self):
        if self.abs.collidepoint(pygame.mouse.get_pos()):
            change = 0
            for event in Game.events:
                if event.type == pygame.MOUSEWHEEL: change = event.y*10
            if change != 0:
                for item in self.items:
                    item.scroll(change)

        for item in self.items:
            item.update()
            if (item.Del.hovered and Keys.is_pressed(Keys.enter)) and item.text.text not in ["__init__", "update", "render"]:
                self.items.remove(item)
                del self.data["functions"][item.text.text]
                self.gen()

        self.input.update()
        self.input_btn.update()
        self.format_input()

        if self.input_btn.pressed:
            name = self.format_input()
            if name in self.data["functions"] or name == "": return
            else:
                self.input.text.set_text("")
                self.data["functions"][name] = {"args": [], "code": ["pass"]}
                self.gen()

    def format_input(self):
        text = self.input.text.text
        for char in text:
            if char.isalnum() or char == "_":
                continue
            elif char == " ": text = text.replace(char, "_")
            else:
                text = text.replace(char, "")
        self.input.text.set_text(text)
        return text

    def render(self):
        self._sub.clear()
        self.min_sub.clear()
        self.show_sub.clear()

        self.title.render_to(self._sub.screen)

        for item in self.items:
            item.render()

        pygame.draw.rect(self.min_sub.screen, Colors["pannel"], self.input_rect)
        self.input.render()
        self.input_btn.render()
        self.show_sub.render()
        self.min_sub.render()
        self._sub.render()

class Item(GameObj):
    def __init__(self, y, text, sub: SubScreen, open=True):
        super().__init__(Vector2D(10, y), 0, visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 30)
        self._rect = pygame.Rect((0, 0), self.size.to_int())

        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.text = self.child(Text(Assets.get_font("default-25"), text, "white", Vector2D(10, 5), "topleft", visible=False))
        self.Del = btn(self.size.x-45, 3, 42, self.size.y-6, "DEL", self.sub, -1, 0, (255, 0, 0))
        self.open = btn(self.size.x-95, 3, 45, self.size.y-6, "OPEN", self.sub, -1, 5, Colors["b"])
        self._open = open

    def scroll(self, dy):
        self.pos.y += dy
        self.sub.pos.y += dy

    def update(self):
        self.Del.update()
        if self._open: self.open.update()

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["pannel"], self._rect, 3)
        self.text.render_to(self.sub.screen)
        self.Del.render()
        if self._open: self.open.render()

        self.sub.render()
