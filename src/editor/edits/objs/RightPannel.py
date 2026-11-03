from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput, _types

from .LeftPannel import Item
from..scenes.Objs import Attribute as _attr

#This file contains both functions and import manager

class RightPannel(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(sub.dim.x-400, 0), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.attr = self.child(Attributes(self.sub, data))
        self.args = self.child(Arguments(self.sub, data))

        self.OPEN = None

    def update(self):
        self.attr.update()
        self.args.update()

    def render(self):
        self.sub.clear()

        self.attr.render()
        self.args.render()

        self.sub.render()


class Attributes(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(0, sub.dim.y//2+5), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y//2-5)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)
        self.sub = SubScreen(5, 40, self.size.x-10, self.size.y-50, Colors["bg"], self._sub.screen, self._sub)
        self.data = data

        self.title = self.child(Text(Assets.get_font("default-35"), "Object Attributes:", "white", Vector2D(self.size.x//2, 20), visible=False))
        i = data["variables"]
        self.attrs: list[_attr] = [
            _attr(10, "pos", "Vector2D", i["pos"], self.sub),
            _attr(50, "z_index", "int", i["z_index"], self.sub),
            _attr(90, "active", "bool", i["active"], self.sub),
            _attr(130, "visible", "bool", i["visible"], self.sub),
            _attr(170, "Global", "bool", i["Global"], self.sub),
        ]

    def save(self):
        for attr in self.attrs:
            if attr.input: self.data["variables"][attr.name] = attr.input.get_value()

    def update(self):
        for attr in self.attrs:
            attr.update()

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)

        for attr in self.attrs:
            attr.render()

        self.sub.render()
        self._sub.render()

class Arguments(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(0, 0), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y//2-5)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)
        self.sub = SubScreen(5, 40, self.size.x-10, self.size.y-50, Colors["pannel"], self._sub.screen, self._sub)
        self.show_sub = SubScreen(5, 50, self.size.x-10, self.size.y-60, Colors["bg"], self.sub.screen, self.sub)
        self.data = data
        self.func = "__init__"

        self._type = TypesBox(265, 5, 150, 40, self.sub)
        self.input = self.child(StrInput(5, 5, 200, 40, "", self.sub))
        self.input_rect = pygame.Rect((3, 3), (203, 43))
        self.add_btn = btn(215, 5, 40, 40, "+", self.sub, -1, 5, Colors["b"])

        self.title = self.child(Text(Assets.get_font("default-35"), "Func Args:", "white", Vector2D(self.size.x//2, 20), visible=False))

        self.items: list[Item] = []
        self.gen()

    def gen(self):
        self.items.clear()
        y = 5
        for attr in self.data["functions"][self.func]["args"]:
            name = attr["name"]
            self.items.append(self.child(Item(y, name, self.show_sub, False)))
            y += self.items[-1].size.y+10

    def set_func(self, func):
        self.func = func
        self.gen()

    def save(self):
        pass

    def update(self):
        self.input.update()
        self.add_btn.update()
        self._type.update()

        for item in self.items:
            item.update()
            if item.Del.hovered and Keys.is_pressed(Keys.enter):
                index = None
                for i in range(len(self.data["functions"][self.func]["args"])):
                    if self.data["functions"][self.func]["args"][i]["name"] == item.text.text:
                        index = i
                        break
                if index == None: return
                self.data["functions"][self.func]["args"].pop(index)
                self.gen()

        if self.add_btn.pressed:
            text = self.input.get_value()
            for attr in self.data["functions"][self.func]["args"]:
                if attr["name"] == text: return
            self.data["functions"][self.func]["args"].append({"name": text, "type": self._type._value, "default": self.get_default(self._type._value)})
            self.gen()
            self.input = self.child(StrInput(5, 5, 200, 40, "", self.sub))

    def get_default(self, _type):
        if _type == "int": return 0
        elif _type == "float": return 0.0
        elif _type == "str": return ""
        elif _type == "bool": return True
        elif _type == "color": return [0, 0, 0]
        elif _type == "Vector2D": return [0, 0]
        return None

    def render(self):
        self._sub.clear()
        self.sub.clear()
        self.show_sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.rect(self.sub.screen, Colors["bg"], self.input_rect)
        self.input.render()
        self.add_btn.render()
        self._type.render()

        for item in self.items:
            item.render()

        self.show_sub.render()
        self.sub.render()
        self._sub.render()

class TypesBox(GameObj):
    def __init__(self, x, y, w, h, sub: SubScreen):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)

        self.value = self.child(Text(Assets.get_font("default-25"), "int", "white", Vector2D(self.size.x//2, self.size.y//2), visible=False))
        self._value = "int"
        self.types = []
        for var in vars(_types):
            self.types.append(var)
        print(self.types)
        self.index = self.types.index(self._value)

    def update(self):
        change = 0
        for event in Game.events:
            if event.type == pygame.MOUSEWHEEL: change = event.y
        if change != 0:
            self.index = (self.index + change) % len(self.types)
            self._value = self.types[self.index]
            self.value.set_text(self._value)

    def render(self):
        self._sub.clear()

        self.value.render_to(self._sub.screen)

        self._sub.render()
        


