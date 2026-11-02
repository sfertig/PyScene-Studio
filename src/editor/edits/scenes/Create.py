from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

class CreateObj(GameObj):
    def __init__(self, sub: SubScreen, data: dict):
        super().__init__(Vector2D(0, 0), visible=False, active=False)
        self.data = data["objects"].copy()

        self.PSub = sub
        self.btn = btn(0, 0, 200, 30, "+ Add Obj", sub, -1, 5, Colors["pannel"], True, pygame.Rect((0, 0), (Game.width, Game.height)))

    def save(self):
        pass

    def update(self):
        self.btn.update()

        #test / debug
        if self.btn.pressed:
            self.create("test", "Rect", PySceneObjectVarDef.Rect.copy())
            self.btn.pressed = False
            return True
        
        return False

    def create(self, name, _type: str, data: list[dict]):
        name = self.find_name(name)
        i = {"obj_type": _type, "variables": {}}
        for _i in data:
            i["variables"][_i["name"]] = _i["default"]
        self.data[name] = i.copy()
        #print(self.data)

    def find_name(self, name):
        #make sure the current name isn't already in use
        name+="0"
        for k in self.data:
            if k == name: 
                num = int(name[-1])
                num+=1
                name = name[:-1]
                name+= str(num)
        return name


    def render(self):
        self.btn.render()


