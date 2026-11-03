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
        self.code = CodePannel(self.sub, self.data)
        self.right = RightPannel(sub, data)

    def save(self): 
        self.right.attr.save()

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
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(10, 55), visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, sub.dim.y-65)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.data = data
        self.set_func("__init__")

    def set_func(self, func):
        pass

    def save(self): #will later write to data
        pass

    def update(self):
        pass

    def render(self):
        self.sub.clear()

        self.sub.render()

