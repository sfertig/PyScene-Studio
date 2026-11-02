from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

class CreateObj(GameObj):
    def __init__(self, sub: SubScreen, data: dict, rect: pygame.Rect):
        super().__init__(Vector2D(0, 0), visible=False, active=False)
        self.data = data["objects"].copy()

        self.PSub = sub
        self.btn = btn(0, 0, 200, 30, "+ Add Obj", sub, -1, 5, Colors["pannel"], True, pygame.Rect((0, 0), (Game.width, Game.height)))

        self._r = pygame.Rect(0, 0, Game._usableEdit.width, 30)
        self._rect = rect.copy() #rect for center screen position and size
        self.center = Center_Surface(sub, self._rect, self.data)

    def save(self):
        pass

    def update(self):
        if not self.btn.pressed and (Keys.is_held(Keys.control) and Keys.is_pressed(Keys.a)): self.btn.pressed = True
        if self.btn.pressed: 
            self.center.update()
            if self.center.DONE: return True
        self.btn.update()
        return False

    def render(self):
        pygame.draw.rect(self.PSub.screen, Colors["pannel"], self._r, 2)
        self.btn.render()
        if self.btn.pressed: 
            self.center.render()

class Center_Surface(GameObj):
    def __init__(self, sub: SubScreen, rect: pygame.Rect, data: dict):
        super().__init__(Vector2D(0, 0), visible=False, active=False)
        self.data = data
        self.PSub = sub
        self.size = Vector2D(rect.width, rect.height)
        self.rect = pygame.Rect((0, 0), self.size.to_int())
        self.sub = SubScreen(rect.x, rect.y, rect.width, rect.height, Colors["pannel"], sub.screen, sub)

        self.CustomObjs = CustomObjs(self.sub)
        self.PySceneObjs = PySceneObjs(self.sub)
        self.DONE = False


    def update(self):
        self.DONE = False
        self.CustomObjs.update()
        self.PySceneObjs.update()

        #creation
        if Game.click:
            for btn in self.CustomObjs.objs:
                if btn.pressed:
                    self.gen(btn.text.text)
                    return
            for btn in self.PySceneObjs.objs:
                if btn.pressed:
                    self._gen(btn.text.text)
                    return

    def gen(self, name):
        #load data
        with open(get_save_dir_path()+f"/{Game.project}/objects/{name}.json", "r") as f:
            data = json.load(f)
        self.create(name, name, data["functions"]["__init__"]["args"])
    def _gen(self, name):
        self.create(name, name, getattr(PySceneObjectVarDef, name))

    def create(self, name, _type: str, data: list[dict]):
        self.DONE = True
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
        self.sub.clear()

        self.CustomObjs.render()
        self.PySceneObjs.render()

        self.sub.render()

class CustomObjs(GameObj):
    def __init__(self, sub: SubScreen):
        super().__init__(Vector2D(10, 50), visible=False, active=False)
        self.title = self.child(Text(Assets.get_font("default-35"), "Custom Objects:", "white", Vector2D(self.pos.x, 5), "topleft", visible=False))
        self.size = Vector2D(400, sub.dim.y-60)

        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)

        self.objs: list[btn] = []
        self.gen()

    def gen(self):
        self.objs.clear()
        #scan objs folder
        y = 5
        for file in os.listdir(get_save_dir_path()+f"/{Game.project}/objects"):
            if not file.endswith(".json"): continue
            name = file.replace(".json", "")
            self.objs.append(btn(10, y, self.size.x-20, 30, name, self.sub, -1, 3, Colors["pannel"]))
            y += 35

    def update(self):
        for obj in self.objs:
            obj.update()

    def render(self):
        self.title.render_to(self.PSub.screen)
        self.sub.clear()

        for obj in self.objs:
            obj.render()

        self.sub.render()

class PySceneObjs(GameObj):
    def __init__(self, sub: SubScreen):
        super().__init__(Vector2D(sub.dim.x-410, 50), visible=False, active=False)
        self.title = self.child(Text(Assets.get_font("default-35"), "PyScene Objects:", "white", Vector2D(self.pos.x, 5), "topleft", visible=False))
        self.size = Vector2D(400, sub.dim.y-60)

        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)

        self.objs: list[btn] = []
        self.gen()

    def gen(self):
        self.objs.clear()
        #scan objs folder
        y = 5
        for obj, value in vars(PySceneObjectVarDef).items():
            self.objs.append(btn(10, y, self.size.x-20, 30, obj, self.sub, -1, 3, Colors["pannel"]))
            y += 35

    def update(self):
        for obj in self.objs:
            obj.update()

    def render(self):
        self.title.render_to(self.PSub.screen)
        self.sub.clear()

        for obj in self.objs:
            obj.render()

        self.sub.render()


