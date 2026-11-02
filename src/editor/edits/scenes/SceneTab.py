import colorsys

from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

from .Inputs import *
from .Objs import *
from .Create import *

class VisualSceneTabEdit(GameObj):
    def __init__(self, name):
        print(name)
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], Game.screen)
        self.name = name

        with open(get_save_dir_path()+f"/{Game.project}/scenes/{self.name}.json", "r") as f: self.data: dict = json.load(f)

        self.gen()

    def gen(self):
        #components

        self.r = pygame.Rect(self.sub.dim.x-400, 35, 400, self.sub.dim.y-35)
        self.test = pygame.Rect(420, 35, self.sub.dim.x-840, self.sub.dim.y-35)
        self.objs = self.child(ObjectsMenue(self.name, self.data, self.sub))
        self.create = self.child(CreateObj(self.sub, self.data.copy(), self.test))

    def save(self):
        #print("saving...\n")
        #self.print_dict(self.data)

        #self.create.save()
        self.objs.save()
        with open(get_save_dir_path()+f"/{Game.project}/scenes/{self.name}.json", "w") as f: json.dump(self.data, f, indent=4)

    def update(self):
        if self.create.update():
            self.data["objects"] = self.create.data.copy()
            self.gen()
            self.save()
            return

        if self.objs.update():
            self.gen()
            self.save()
            return

    def print_dict(self, data): #debug func
        for k, v in data.items():
            print(k, v)
            print("\n")

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.r)
        #pygame.draw.rect(self.sub.screen, Colors["pannel"], self.test)
        self.objs.render()
        self.create.render()

        self.sub.render()

