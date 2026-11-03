from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput

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

    def save(self): #will later write to data
        pass

    def update(self, func):
        if func != self.func and func is not None: 
            self.save()
            self.func = func
            self.title.set_text(func)
            self.code.set_func(func)

        self.code.update()

    def render(self):
        self.sub.clear()

        self.title.render_to(self.sub.screen)
        pygame.draw.line(self.sub.screen, "black", (10, 50), (self.size.x-20, 50))
        self.code.render()

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
        if func != "__init__": self.args = self.child(ArgsInput(self.sub, self.data, func))
        else: self.args = None

    def save(self): #will later write to data
        pass

    def update(self):
        if self.args is not None: self.args.update()

    def render(self):
        self.sub.clear()

        if self.args is not None: self.args.render()

        self.sub.render()

class ArgsInput(GameObj):
    def __init__(self, sub: SubScreen, data, func):
        super().__init__(Vector2D(5, 5), visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 60)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen
        self._rect = pygame.Rect((0, 0), self.size.to_int())

        self.args_sub = SubScreen(5, 5, self.size.x-125, self.size.y-10, Colors["bg"], self.sub.screen, self.sub)
        self.args_rect = pygame.Rect((5, 5), (self.size.x-125, self.size.y-10))

        self.data = data
        self.func = func

    def update(self):
        pass

    def render(self):
        self.sub.clear()
        self.args_sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["pannel"], self._rect, 3)
        pygame.draw.rect(self.args_sub.screen, Colors["b"], self.args_rect, 3)

        self.args_sub.render() 
        self.sub.render()

