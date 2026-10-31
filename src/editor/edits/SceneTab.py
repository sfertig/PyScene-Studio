from PyScene import *
import PyScene
import pygame
import json

from ...utils.load_assets import Colors
from ...utils.files import *
from .TabManager import btn

class VisualSceneTabEdit(GameObj):
    def __init__(self, name):
        print(name)
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], Game.screen)
        self.name = name

        self.gen()

    def gen(self):
        #load data
        with open(get_save_dir_path()+f"/{Game.project}/scenes/{self.name}.json", "r") as f: self.data: dict = json.load(f)

        #components

        self.r = pygame.Rect(self.sub.dim.x-400, 0, 400, self.sub.dim.y)
        self.test = pygame.Rect(420, 0, self.sub.dim.x-840, self.sub.dim.y)
        self.objs = self.child(ObjectsMenue(self.name, self.data, self.sub))

    def save(self):
        print("saving...")
        self.objs.save()
        with open(get_save_dir_path()+f"/{Game.project}/scenes/{self.name}.json", "w") as f: json.dump(self.data, f, indent=4)

    def update(self):
        self.objs.update()

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.r)
        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.test)
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

    def save(self):
        for obj in self.objs: obj.save()
        self.data["objects"] = {} #"reconstruct" objects
        for obj in self.objs:
            self.data["objects"][obj.obj_name] = obj.data

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

    def save(self):
        for attr in self.attr: 
            if attr.input: self.data["variables"][attr.name] = attr.input.get_value()

    def gen(self):
        self.attr.clear()
        y = 5
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

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.line(self._sub.screen, "black", (5, 35), (self.size.x-5, 35))

        for attr in self.attr: attr.render()

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

#region Attribute Inputs
#inputs for different arg types

class IntInput(GameObj):
    def __init__(self, x, y, w, h, value, sub: SubScreen):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        self.value = value

        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.r = pygame.Rect((0, 0), self.size.to_int())
        self._rect = pygame.Rect(self.pos.to_int(), self.size.to_int())
        self.text = self.child(Text(Assets.get_font("default-25"), str(self.value), "white", Vector2D(self.r.centerx, self.r.centery), visible=False))
        
        self.w = 0
        self.hovered = False
        self.pressed = False
        self.buffer = 0

    def get_value(self) -> int:
        return int(format_int(self.text.text) or "0")

    def update(self):
        if self.buffer < 0: self.buffer = 0
        mpos = self.PSub.local_mouse_pos().to_int()
        self.hovered = self._rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = -1

        if self.pressed: self.w = 5

        if Game.click:
            if self.hovered: self.pressed = not self.pressed
            else: self.pressed = False
            if not self.pressed: 
                self.text.set_text(format_int(self.text.text))

        if not self.pressed: return
        #text input and format
        text = self.text.text
        for event in Game.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE: continue #text = text[:-1]
                elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE: 
                    self.pressed = False
                    text = str(format_int(self.text.text))
                    break
                else: text += event.unicode
        if Keys.is_held(Keys.backspace) and self.buffer == 0: 
            text = text[:-1]
            self.buffer = 15
        elif not Keys.is_held(Keys.backspace): self.buffer = 0
        if text != self.text.text: self.text.set_text(text)
        

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["b"], self.r, self.w)
        self.text.render_to(self.sub.screen)

        self.sub.render()



#funcs for formatting
class _types_:
    def __init__(self):
        self.int = IntInput

_types = _types_()

def format_int(text):
    #print("formatting...")
    for char in text:
        if not char.isdigit():
            text = text.replace(char, "")
    if text == "": text = "0"
    return text

#endregion
