from PyScene import *
import pygame
import json
import time
from importlib.metadata import version
from ..Build import Build
from ..Runner import Runner


from ..utils.load_assets import Colors, load_editor_assets
from ..utils.files import *

from .Tabs import TabMenue

def RunEditor(project_name):
    print("[Editor] - Running Editor")
    Game.init(1920, 1080, "PyScene-Studio Editor", Colors["bg"], 60, True, True)
    pygame.font.init()
    load_editor_assets()

    Game.project = project_name
    Game.always_global = True
    Game.BREAK = False
    Game.click = False

    Game._usableEdit = pygame.Rect(0, 100, Game.width, Game.height-140)

    WINDOW_HEAD(project_name)
    TabMenue(40)
    while True:
        Game.Tick()
        if Keys.is_held(Keys.shift) and Keys.is_pressed(Keys.escape): Game.quit() #debug / developement exit
        if Keys.is_pressed(Keys.escape) or Game.BREAK: break

    Game.quit(False)
    print("[Editor] - Editor Closed")
    time.sleep(0.3)
    Game._project_manager()
    

class WINDOW_HEAD(GameObj): #window head for quick options (and bottom versions bar)
    def __init__(self, project_name):
        super().__init__(Vector2D(0, 0), 100)
        self.size = Vector2D(Game.width, 40)
        self.sub = SubScreen(0, 0, self.size.x, self.size.y, Colors["pannel"], Game.screen)
        self.rect = pygame.Rect((0, 0), self.size.to_int())
        t = f"PyScene-Studio Editor - {project_name}"
        self.title = self.child(Text(Assets.get_font("default-35"), t, "white", Vector2D(10, self.size.y/2), "midleft", visible=False))

        #btns
        self.close = btn(Game.width-40, 30, "X", self.sub)
        self.build = btn(Game.width-160, 100, "Build", self.sub)
        self.run = btn(Game.width-270, 100, "Run", self.sub)

        r = self.child(Rect(0, Game.height-30, Game.width, 30, Colors["pannel"], 10))
        self.child(Text(Assets.get_font("default-25"), f"GUI Version: {Game.version} | PyScene Version: {version("PyScene")}", "white", Vector2D(5, r.pos.y+r.rect.height/2), "midleft", 100))

    def update(self):

        self.close.update()
        self.build.update()
        self.run.update()

        if self.close.pressed: Game.BREAK = True
        elif self.build.pressed: Build(Game.project)
        elif self.run.pressed: 
            Build(Game.project)
            Runner(Game.project)

    def render(self):
        self.sub.clear()

        self.title.render_to(self.sub.screen)

        pygame.draw.rect(self.sub.screen, Colors["b"], self.rect, 2)

        self.close.render()
        self.build.render()
        self.run.render()

        self.sub.render()

class btn:
    def __init__(self, x, w, text, sub: SubScreen):
        self.rect = pygame.Rect(x, 5, w, 30)
        self.text = Text(Assets.get_font("default-35"), text, "white", Vector2D(self.rect.centerx, self.rect.centery), visible=False)
        self.w = 2
        self.hovered = False
        self.pressed = False
        self.sub = sub

    def update(self):
        self.pressed = False
        mpos = self.sub.local_mouse_pos().to_int()
        self.hovered = self.rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = 2

        if Game.click and self.hovered:
            Game.click = False
            self.pressed = True

    def render(self):
        pygame.draw.rect(self.sub.screen, Colors["b"], self.rect, self.w)
        self.text.render_to(self.sub.screen)


