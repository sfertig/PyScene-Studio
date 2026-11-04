from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from .Inputs import _types

class ObjectsMenue(GameObj):
    def __init__(self, name: str, data: dict, sub: SubScreen):
        super().__init__(Vector2D(0, 35), visible=False, active=False)
        self.scene_name = name
        self.data = data

        self.size = Vector2D(400, sub.dim.y-35)
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

    def save(self):
        for obj in self.objs: obj.save()
        self.data["objects"] = {} #"reconstruct" objects
        for obj in self.objs:
            self.data["objects"][obj.obj_name] = obj.data

    def update(self):
        for obj in self.objs: 
            obj.update()
            if obj.DEL: 
                self.objs.remove(obj)
                #remove from data
                del self.data["objects"][obj.obj_name]
                self.save()
                return True

        return False

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

        #update self data
        if not hasattr(PySceneObjectVarDef, self.data["obj_type"]):
            with open(f"{get_save_dir_path()}/{Game.project}/objects/{self.data['obj_type']}.json", "r") as f: obj_init = json.load(f)
            for arg in obj_init["functions"]["__init__"]["args"]:
                k = arg["name"]
                v = arg["default"]
                if k not in self.data["variables"]:
                    self.data["variables"][k] = v

        self.display = display
        self.PSub = sub
        pos = sub.get_absolute_pos().to_int()
        r = pygame.Rect(pos, sub.dim.to_int())
        self.btn = btn(self.pos.x, self.pos.y, self.size.x, self.size.y, f"{self.obj_name}  |   ({self.data['obj_type']})", sub, -1, 5, Colors["bg"], True, r)
        self.child(self.btn.text)
        self.props: PropertiesPannel = None
        self.DEL = False

    def save(self):
        if self.props: self.props.save()
        

    def update(self):
        self.btn.update()
        if self.btn.pressed and not self.props:
            self.props = self.child(PropertiesPannel(self.display, self.obj_name, self.data))
        elif not self.btn.pressed and self.props:
            self.props.save()
            self.props.destroy()
            self.props = None

        if self.props: self.props.update()
        if self.props and self.props.Del.pressed:
            self.destroy()
            self.props.destroy()
            self.props = None
            self.DEL = True

        #name
        if self.props:
            name = self.props.attr[0].input.get_value()
            if name != self.obj_name:
                self.obj_name = name
                self.btn.text.set_text(f"{self.obj_name}  |   ({self.data['obj_type']})")

    def render(self):
        self.btn.render()
        if self.props: self.props.render()

class PropertiesPannel(GameObj):
    def __init__(self, sub: SubScreen, name, data):
        super().__init__(Vector2D(sub.dim.x-400, 35), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y-35)
        self.name = name
        self.type = data["obj_type"]
        self.data = data

        self.Psub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)

        self.title = self.child(Text(Assets.get_font("default-35"), "Object Properties:", "white", Vector2D(10, 5), "topleft", visible=False))

        self.sub = SubScreen(0, 37, self.size.x, self.size.y-37, Colors["pannel"], self._sub.screen, self._sub)
        self.screen = self.sub.screen
        self.open = btn(10, self.sub.dim.y-80, self.size.x-20, 30, "Open", self.sub, -1, 3, Colors["b"])
        self.Del = btn(10, self.sub.dim.y-40, self.size.x-20, 30, "Remove", self.sub, -1, 3, (255, 0, 0))

        self.attr: list[Attribute] = []

        self.gen()

    def save(self):
        for attr in self.attr[1:]: 
            if attr.input: self.data["variables"][attr.name] = attr.input.get_value()

    def gen(self):
        self.attr.clear()
        self.attr.append(self.child(Attribute(5, "Name", "str", self.name, self.sub)))
        y = self.attr[-1].size.y+10
        #self.attr.append(self.child(Attribute(5, "Test", "str", "test", self.sub)))
        for var in self.data["variables"]:
            #get var type, using args dict or prebuilt

            if hasattr(PySceneObjectVarDef, self.type): 
                args = getattr(PySceneObjectVarDef, self.type)
            else:
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
        self.Del.update()
        self.open.update()
        if self.open.pressed or (Keys.is_held(Keys.control) and Keys.is_pressed(Keys.tab)):
            if not hasattr(PySceneObjectVarDef, self.type): Game._tabs.open_tab(self.type, "_object_", "object")

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.line(self._sub.screen, "black", (5, 35), (self.size.x-5, 35))

        for attr in self.attr: attr.render()
        self.Del.render()
        self.open.render()

        self.sub.render()
        self._sub.render()

class Attribute(GameObj):
    def __init__(self, y, name, _type, value, sub):
        super().__init__(Vector2D(10, y), 0, visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 30)

        self.PSub: SubScreen = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.title = self.child(Text(Assets.get_font("default-25"), name+":", "white", Vector2D(10, 5), "topleft", visible=False))

        self.name = name
        self.type = _type
        self.value = value

        self.input = None
        if hasattr(_types, self.type): self.input=getattr(_types, self.type)(self.size.x-200, 0, 200, 30, self.value, self.sub)

    def update(self):
        if self.input: self.input.update()

    def render(self):
        self.sub.clear()

        self.title.render_to(self.screen)
        if self.input: self.input.render()

        self.sub.render()
