from PyScene import *
import pygame
import json
import time
from importlib.metadata import version


from ..utils.load_assets import Colors, load_editor_assets
from ..utils.files import *

from .Tabs import TabMenue

BREAK = False

def RunEditor(project_name):
    print("[Editor] - Running Editor")
    Game.init(1920, 1080, "PyScene-Studio Editor", Colors["bg"], 60, True, True)
    pygame.font.init()
    load_editor_assets()

    Game.project = project_name
    Game.always_global = True

    WINDOW_HEAD(project_name)
    TabMenue(40)

    while True:
        Game.Tick()
        if Keys.is_pressed(Keys.escape) or BREAK: break
    Game.quit(False)
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
        self.btn_rect = pygame.Rect(Game.width-40, 5, 30, 30)
        self.closeText = self.child(Text(Assets.get_font("default-35"), "X", "white", Vector2D(self.btn_rect.centerx, self.btn_rect.centery), visible=False))
        self.w = 2
        self.hovered = False

        r = self.child(Rect(0, Game.height-30, Game.width, 30, Colors["pannel"], 10))
        self.child(Text(Assets.get_font("default-25"), f"GUI Version: {Game.version} | PyScene Version: {version("PyScene")}", "white", Vector2D(5, r.pos.y+r.rect.height/2), "midleft", 100))

    def update(self):
        global BREAK

        mpos = self.sub.local_mouse_pos().to_int()
        self.hovered = self.btn_rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = 2

        if Game.click and self.hovered:
            Game.click = False
            BREAK = True

    def render(self):
        self.sub.clear()

        self.title.render_to(self.sub.screen)

        pygame.draw.rect(self.sub.screen, Colors["b"], self.rect, 2)

        #btn
        pygame.draw.rect(self.sub.screen, Colors["b"], self.btn_rect, self.w)
        self.closeText.render_to(self.sub.screen)

        self.sub.render()


