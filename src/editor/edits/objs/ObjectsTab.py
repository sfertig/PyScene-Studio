import colorsys

from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

from .LeftPannel import LeftPannel
from .CenterPannel import CenterPannel

class ObjectsTabEdit(GameObj):
    def __init__(self, name):
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], Game.screen)
        self.name = name

        with open(get_save_dir_path()+f"/{Game.project}/objects/{self.name}.json", "r") as f: self.data: dict = json.load(f)

        self.gen()

    def gen(self):
        #components
        self.r = pygame.Rect(self.sub.dim.x-400, 0, 400, self.sub.dim.y)

        self.left = self.child(LeftPannel(self.sub, self.data))
        self.center = self.child(CenterPannel(self.sub, self.data))

    def save(self):
        self.center.save()
        path = get_save_dir_path()+f"/{Game.project}/objects/{self.name}.json"
        save_source_json(self.data, path)

    def update(self):
        self.left.update()
        func = self.left.OPEN #will be used for center pannel
        self.center.update(func)


    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.r)
        self.left.render()
        self.center.render()

        self.sub.render()
