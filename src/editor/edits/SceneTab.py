from PyScene import *
import pygame
import json

from ...utils.load_assets import Colors
from ...utils.files import *
from .TabManager import btn

class VisualSceneTabEdit(GameObj):
    def __init__(self, name):
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], Game.screen)

        #load data
        with open(get_save_dir_path()+f"/{Game.project}/scenes/{name}.json", "r") as f: self.data: dict = json.load(f)

        #components

        self.r = pygame.Rect(self.sub.dim.x-400, 0, 400, self.sub.dim.y)
        self.objs = self.child(ObjectsMenue(name, self.data, self.sub))

    def save(self):
        pass

    def update(self):
        self.objs.update()

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.r)
        self.objs.render()

        self.sub.render()

class ObjectsMenue(GameObj):
    def __init__(self, name: str, data: dict, sub: SubScreen):
        super().__init__(Vector2D(0, 0), visible=False, active=False)
        self.scene_name = name
        self.data = data

        self.size = Vector2D(400, sub.dim.y)
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)

        self.title = self.child(Text(Assets.get_font("default-35"), self.scene_name+" Scene Objects:", "white", Vector2D(10, 5), "topleft", visible=False))

        self.sub = SubScreen(self.pos.x, self.pos.y+37, self.size.x, self.size.y-37, Colors["pannel"], self._sub.screen, self._sub)
        self.PSub = sub
        self.screen = self.sub.screen

        self.objs: list[_SceneObject] = []

        self.gen()

    def gen(self):
        y = 0
        for name in self.data["objects"]:
            self.objs.append(self.child(_SceneObject(y, name, self.data["objects"][name], self.sub, self.PSub)))
            y += self.objs[-1].size.y+10

    def update(self):
        for obj in self.objs: obj.update()

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.line(self._sub.screen, "black", (5, 35), (self.size.x-5, 35))

        for obj in self.objs: obj.render()

        self.sub.render()

        self._sub.render()

class _SceneObject(GameObj):
    def __init__(self, y, name, data, sub: SubScreen, display: SubScreen):
        super().__init__(Vector2D(10, y), 0, visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 30)

        self.obj_name = name
        self.data = data

        self.display = display
        self.PSub = sub
        pos = sub.get_absolute_pos().to_int()
        r = pygame.Rect(pos, sub.dim.to_int())
        self.btn = btn(self.pos.x, self.pos.y, self.size.x, self.size.y, self.obj_name, sub, -1, 5, Colors["bg"], True, r)
        self.child(self.btn.text)
        self.props: PropertiesPannel = None
        

    def update(self):
        self.btn.update()
        if self.btn.pressed and not self.props:
            self.props = self.child(PropertiesPannel(self.display, self.obj_name, self.data))
        elif not self.btn.pressed and self.props:
            self.props.destroy()
            self.props = None

        if self.props: self.props.update()

    def render(self):
        self.btn.render()
        if self.props: self.props.render()

class PropertiesPannel(GameObj):
    def __init__(self, sub: SubScreen, name, data):
        super().__init__(Vector2D(sub.dim.x-400, 0), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y)
        self.name = name
        self.type = data["obj_type"]
        self.data = data

        self.Psub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)

        self.title = self.child(Text(Assets.get_font("default-35"), "Object Properties:", "white", Vector2D(10, 5), "topleft", visible=False))

        self.sub = SubScreen(0, self.pos.y+37, self.size.x, self.size.y-37, Colors["pannel"], self._sub.screen, self._sub)
        self.screen = self.sub.screen

        self.attr: list[Attribute] = []

        self.gen()
        print(len(self.attr))
        for attr in self.attr:
            print(attr.pos.to_int())

    def gen(self):
        self.attr.clear()
        y = 5
        #self.attr.append(self.child(Attribute(5, "Test", "str", "test", self.sub)))
        for var in self.data["variables"]:
            #get var type, using args dict or prebuilt

            if self.type in ["Rect", "Circle", "Text", "Line"]: continue #TODO: add pyscene dict for var type lookup

            #load obj file
            with open(get_save_dir_path()+f"/{Game.project}/objects/{self.type}.json", "r") as f: data = json.load(f)
            args = data["functions"]["__init__"]["args"]
            for i in args:
                if i["name"] == var:
                    #print(f"adding property: {var} of type: {i['type']} with value: {self.data['variables'][var]} at y: {y}")
                    self.attr.append(self.child(Attribute(y, var, i["type"], self.data["variables"][var], self.sub)))
                    break

            y += self.attr[-1].size.y+10

    def update(self):
        for attr in self.attr: attr.update()

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.line(self._sub.screen, "black", (5, 35), (self.size.x-5, 35))

        for attr in self.attr: attr.render()

        self.sub.render()
        self._sub.render()

class Attribute(GameObj):
    def __init__(self, y, name, type, value, sub):
        super().__init__(Vector2D(10, y), 0, visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 30)

        self.PSub: SubScreen = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.title = self.child(Text(Assets.get_font("default-25"), name+":", "white", Vector2D(10, 5), "topleft", visible=False))

        self.name = name
        self.type = type
        self.value = value

    def update(self):
        pass

    def render(self):
        self.sub.clear()

        self.title.render_to(self.screen)

        self.sub.render()

