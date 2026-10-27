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
        self.scenes = self.child(SceneDisplay(self.sub, tabs))
        #self.objs = self.child(ObjectDisplay(self.sub))

    def update(self):
        pass

    def render(self):
        self.sub.clear()

        self.scenes.render()
        #self.objs.render()
        
        self.sub.render()

class SceneDisplay(GameObj):
    def __init__(self, sub: SubScreen, tabs):
        super().__init__(Vector2D(5, 25), visible=False)
        self.PSub = sub
        self.tabs = tabs

        self.title = self.child(Text(Assets.get_font("default-35"), "Scenes:", "white", Vector2D(self.pos.x, 0), "topleft", visible=False))

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
        for file in os.listdir(get_save_dir_path()+f"/{Game.project}/scenes/"):
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
            if s.pressed and Game.click: self.check_open(s)

    def check_open(self, scene):
        print(f"checking {scene.text.text}, open: {self.open.pressed}")
        if scene.pressed and self.open.pressed:
            print("open scene")
            #check if tab is alread open
            name = scene.text.text
            for tab in self.tabs.tabs:
                if tab.name[-5:] == name: return #if name(- scene text) is already open
            self.tabs.new_scene(name)


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
    def __init__(self, x, y, w, h, text, sub=None, min_w=-1, max_w=5, color=Colors["b"], toggle=False, _rect=None):
        self.pos = Vector2D(x, y)
        self.size = Vector2D(w, h)
        self.rect = pygame.Rect(self.pos.to_int(), self.size.to_int())
        self.text = Text(Assets.get_font("default-25"), text, "white", Vector2D(self.rect.centerx, self.rect.centery), visible=False)
        self.sub: SubScreen = sub

        self._r = _rect
        #if _rect: Rect(_rect.x, _rect.y, _rect.width, _rect.height, "yellow", 9999999999)
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
            if Game.click and self._r.collidepoint(pygame.mouse.get_pos()):
                if self.hovered:
                    self.pressed = not self.pressed  # Flips between True and False
                elif self.pressed:
                    self.pressed = False             # Turns off if clicking anywhere else


    def render(self):
        pygame.draw.rect(self.sub.screen, self.color, self.rect, self.w)
        self.text.render_to(self.sub.screen)
        #pygame.draw.circle(self.sub.screen, "yellow", self.mpos, 3)
        #if self._r: pygame.draw.rect(self.sub.screen, self.color, self._r, 2)
