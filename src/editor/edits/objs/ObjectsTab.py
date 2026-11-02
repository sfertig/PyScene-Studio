import colorsys

from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

from .LeftPannel import LeftPannel

class ObjectsTabEdit(GameObj):
    def __init__(self, name):
        print(name)
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], Game.screen)
        self.name = name

        with open(get_save_dir_path()+f"/{Game.project}/objects/{self.name}.json", "r") as f: self.data: dict = json.load(f)

        self.gen()

    def gen(self):
        #components
        self.r = pygame.Rect(self.sub.dim.x-400, 0, 400, self.sub.dim.y)
        self.test = pygame.Rect(420, 0, self.sub.dim.x-840, self.sub.dim.y)

        self.left = self.child(LeftPannel(self.sub, self.data))

    def save(self):
        with open(get_save_dir_path()+f"/{Game.project}/objects/{self.name}.json", "w") as f: json.dump(self.data, f, indent=4)

    def update(self):
        self.left.update()

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.r)
        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.test)
        self.left.render()

        self.sub.render()

