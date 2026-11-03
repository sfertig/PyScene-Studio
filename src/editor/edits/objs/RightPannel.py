from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput

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
        self.sub = SubScreen(5, 40, self.size.x-10, self.size.y-50, Colors["bg"], self._sub.screen, self._sub)
        self.data = data

        self.title = self.child(Text(Assets.get_font("default-35"), "Func Args:", "white", Vector2D(self.size.x//2, 20), visible=False))

    def save(self):
        pass

    def update(self):
        pass

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)

        self.sub.render()
        self._sub.render()

