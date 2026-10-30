from PyScene import *
import pygame
import json

from ...utils.load_assets import Colors
from ...utils.files import *

class TabManagerEdit(GameObj):
    def __init__(self, tabs):
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], Game.screen)
        self.tabs = tabs

        #children
        self.scenes = self.child(Display(5, self.sub, tabs, "scene", "Scenes:"))
        self.objs = self.child(Display(425, self.sub, tabs, "object", "Objects:"))

        self.create_scene = self.child(Create(Vector2D(845, 345), self.sub, tabs, "scene"))
        self.create_obj = self.child(Create(Vector2D(845, 25), self.sub, tabs, "object"))

    def update(self):
        self.scenes.update()
        self.objs.update()

        self.create_scene.update()
        self.create_obj.update()
        if self.create_scene.GEN: self.scenes.gen()
        if self.create_obj.GEN: self.objs.gen()

    def render(self):
        self.sub.clear()

        self.scenes.render()
        self.objs.render()

        self.create_scene.render()
        self.create_obj.render()
        
        self.sub.render()

class Create(GameObj):
    def __init__(self, pos: Vector2D, sub: SubScreen, tabs, name):
        super().__init__(pos, visible=False, active=False)
        self.PSub = sub
        self.tabs = tabs
        self.GEN = False

        self.size = Vector2D(400, 300)
        self.sub = SubScreen(pos.x, pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen
        self.title = self.child(Text(Assets.get_font("default-35"), f"Create New {name}:", "white", Vector2D(5, 5), "topleft", visible=False))

        self._name = name
        self._name_ = f"_{name}_"
        self.id = name
        self.name = self.child(TextInput(5, 50, self.size.x-10, 30, Assets.get_font("default-25"), "", self.sub))
        self.create = btn(self.size.x/2-50, self.size.y-50, 100, 50, "Create", self.sub, -1, 2, Colors["b"])
        self.child(self.create.text)

    def update(self):
        self.GEN = False
        self.name.update()
        self.create.update()
        if self.create.pressed:
            name = self.name.text.text
            if self.check_exists(name): 
                print(f"[TabManager] - {self._name} Already Exists")
                return
            if name == "": return
            self._create(name)

    def _create(self, name):
        #create file
        if self._name == "scene": data = DEFAULTSCENE.copy()
        else: data = DEFAULTOBJECT.copy()
        data["name"] = name
        with open(get_save_dir_path()+f"/{Game.project}/{self._name}s/{name}.json", "w") as f:
            json.dump(data, f, indent=4)
            print(f"[TabManager] - {self._name} File Created: "+name)
        self.tabs.open_tab(name, self._name_, self.id)
        self.name.text.set_text("")
        self.GEN = True


    def check_exists(self, name):
        scenes = os.listdir(get_save_dir_path()+f"/{Game.project}/scenes/")
        objs = os.listdir(get_save_dir_path()+f"/{Game.project}/objects/")
        for s in scenes:
            if s[:-5] == name: return True
        for o in objs:
            if o[:-5] == name: return True
        return False

    def render(self):
        self.sub.clear()

        self.title.render_to(self.sub.screen)
        pygame.draw.line(self.screen, "black", (5, 35), (self.size.x-5, 35))
        self.name.render()
        self.create.render()

        self.sub.render()

class Display(GameObj):
    def __init__(self, x, sub: SubScreen, tabs, name, title):
        super().__init__(Vector2D(x, 25), visible=False, active=False)
        self.PSub = sub
        self.tabs = tabs

        self.title = self.child(Text(Assets.get_font("default-35"), title, "white", Vector2D(self.pos.x, 0), "topleft", visible=False))
        self.name = name
        self._name_ = f"_{name}_"

        self.sub = SubScreen(self.pos.x, self.pos.y, 400, sub.dim.y-30, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        #options
        self.op_sub = SubScreen(0, self.sub.dim.y-130, self.sub.dim.x, 130, Colors["bg"], self.screen, self.sub)
        self.op_rect = pygame.Rect(0, 0, self.sub.dim.x, 130)
        self.open = btn(5, 5, 100, 30, "Open", self.op_sub, 2)
        self.child(self.open.text)
        self.delete = btn(5, 50, 275, 30, "Delete (hover and press enter)", self.op_sub, -1, 0, (255, 0, 0))
        self.child(self.delete.text)
        self.show_options = False

        #load / create scenes
        self.scenes: list[btn] = []
        self.gen()

    def gen(self):
        self.scenes.clear()
        y = 5
        w = self.sub.dim.x-20
        pos = self.sub.get_absolute_pos()
        rect = pygame.Rect(pos.x, pos.y, self.sub.dim.x, self.sub.dim.y-130)
        for file in os.listdir(get_save_dir_path()+f"/{Game.project}/{self.name}s/"):
            if file.endswith(".json"):
                name = file[:-5]
                self.scenes.append(btn(10, y, w, 40, name, self.sub, -1, 3, Colors["pannel"], True, rect))
                y += 50
                self.child(self.scenes[-1].text)


    def update(self):
        self.open.update()
        self.delete.update()

        self.show_options = False
        for s in self.scenes: 
            s.update()
            if s.pressed: self.show_options = True

        for s in self.scenes:
            if s.pressed: self.check_open(s)

    def check_open(self, scene):
        #print(f"checking {scene.text.text}, open: {self.open.pressed}")
        if scene.pressed and self.open.pressed:
            #print("open scene")
            #check if tab is alread open
            name = scene.text.text
            self.tabs.open_tab(name, self._name_, self.name)
        #del
        elif scene.pressed and self.delete.hovered and Keys.is_pressed(Keys.enter):
            #check if scene is main, that dosnt delete
            if scene.text.text == "main": return
            #close tab if open
            for tab in self.tabs.tabs:
                if hasattr(tab, self._name_): 
                    if tab._name == scene.text.text:
                        tab.close()
                        break
            #delete file
            os.remove(get_save_dir_path()+f"/{Game.project}/{self.name}s/{scene.text.text}.json")
            print(f"[TabManager] - {self.name} Deleted: "+scene.text.text)
            self.gen()


    def render(self):
        self.sub.clear()

        self.title.render_to(self.PSub.screen)

        for s in self.scenes: s.render()

        #options
        if self.show_options:
            self.op_sub.clear()
            pygame.draw.rect(self.op_sub.screen, Colors["b"], self.op_rect, 2)
            self.open.render()
            self.delete.render()
            self.op_sub.render()

        self.sub.render()

class btn():
    def __init__(self, x, y, w, h, text, sub, min_w=-1, max_w=5, color=Colors["b"], toggle=False, _rect=None):
        self.pos = Vector2D(x, y)
        self.size = Vector2D(w, h)
        self.rect = pygame.Rect(self.pos.to_int(), self.size.to_int())
        self.text = Text(Assets.get_font("default-25"), text, "white", Vector2D(self.rect.centerx, self.rect.centery), visible=False)
        self.sub: SubScreen = sub

        self._r = _rect
        self.min_w = min_w
        self.max_w = max_w
        self.w = min_w
        self.hovered = False
        self.pressed = False
        self.toggle = toggle
        self.color = color

    def update(self):
        if not self.toggle: self.pressed = False
        mpos = self.sub.local_mouse_pos().to_int()
        #self.mpos = mpos
        self.hovered = self.rect.collidepoint(mpos)
        if self.hovered: self.w = self.max_w
        else: self.w = self.min_w

        if self.toggle and self.pressed: self.w = self.max_w

        if not self.toggle: 
            if Game.click and self.hovered:
                self.pressed = True
        else:
            # Handles the toggle logic properly
            #if Game.click: print(f"checking: mpos: {pygame.mouse.get_pos()}, hit: {self._r.collidepoint(pygame.mouse.get_pos())}, hovered: {self.hovered}, pressed: {self.pressed}")
            if Game.click and self._r.collidepoint(pygame.mouse.get_pos()):
                if self.hovered and not self.pressed:
                    self.pressed = True  # Flips between True and False
                elif self.hovered and self.pressed:
                    self.pressed = False
                elif self.pressed:
                    self.pressed = False             # Turns off if clicking anywhere else


    def render(self):
        pygame.draw.rect(self.sub.screen, self.color, self.rect, self.w)
        self.text.render_to(self.sub.screen)
        #pygame.draw.circle(self.sub.screen, "yellow", self.mpos, 3)
        #if self._r: pygame.draw.rect(self.sub.screen, self.color, self._r, 2)

class TextInput(GameObj):
    def __init__(self, x, y, w, h, font, text="", sub=None, _input=True):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        s = Game.screen
        if sub: s = sub.screen
        self.sub = SubScreen(x, y, w, h, Colors["bg"], s, sub)
        self.PSub = sub
        self.rect = pygame.Rect((0, 0), self.size.to_int())
        self._rect = pygame.Rect(x, y, w, h)
        self.w = 2
        self.text = Text(font, text, "white", Vector2D(self.rect.centerx, self.rect.centery), "center", 5, visible=False)
        self.active = False
        self.hovered = False

        self.buffer = 0
        self._input = _input

        self.child(self.text)

    def update(self):
        self.buffer -= 1
        if self.buffer < 0: self.buffer = 0
        mpos = self.PSub.local_mouse_pos().to_int()
        self.hovered = self._rect.collidepoint(mpos)
        if not self.active:
            if self.hovered: self.w = 5
            else: self.w = 2

        if Game.click:
            if not self.hovered:
                self.active = False
            else:
                self.active = True

        if self.active:
            if Keys.is_pressed(Keys.enter) or Keys.is_pressed(Keys.escape):
                self.active = False
                self.w = 2
            if self._input:
                text = self.text.text
                done = False
                for event in Game.events:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_BACKSPACE: continue #text = text[:-1]
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE: continue
                        else: text += event.unicode
                if Keys.is_held(Keys.backspace) and self.buffer == 0: 
                    text = text[:-1]
                    self.buffer = 7
                elif not Keys.is_held(Keys.backspace): self.buffer = 0
                if text != self.text.text: self.text.set_text(text)

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.rect, self.w)
        self.text.render_to(self.sub.screen)
        self.sub.render()
