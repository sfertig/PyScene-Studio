from PyScene import *
import pygame
import json
import time
import collections.abc
import copy
from importlib.metadata import version
from ..Build import Build
from ..Runner import Runner


from ..utils.load_assets import Colors, load_editor_assets
from ..utils.files import *

from .Tabs import TabMenue

def RunEditor(project_name, new=False):
    if not new: update_project_files(project_name)
    print("[Editor] - Running Editor")
    Game.init(1920, 1080, "PyScene-Studio Editor", Colors["bg"], 60, True, True)
    pygame.font.init()
    load_editor_assets()

    Game.project = project_name
    Game.always_global = True
    Game.BREAK = False
    Game.click = False
    Game.RENAMETITLE = False

    Game._usableEdit = pygame.Rect(0, 100, Game.width, Game.height-140)

    tabs = TabMenue(40, new)
    w = WINDOW_HEAD(project_name, tabs)
    w._active = False

    while True:
        Game.RENAMETITLE = False
        Game.Tick()
        w.update()
        if Keys.is_held(Keys.shift) and Keys.is_pressed(Keys.escape): Game.quit() #debug / developement exit
        if Game.BREAK: break

    Game.quit(False)
    print("[Editor] - Editor Closed")
    time.sleep(TIME)
    Game._project_manager()
    

class WINDOW_HEAD(GameObj): #window head for quick options (and bottom versions bar)
    def __init__(self, project_name, tabs):
        super().__init__(Vector2D(0, 0), 100)
        self.size = Vector2D(Game.width, 40)
        self.sub = SubScreen(0, 0, self.size.x, self.size.y, Colors["pannel"], Game.screen)
        self.rect = pygame.Rect((0, 0), self.size.to_int())
        t = f"PyScene-Studio Editor - {project_name}"
        self.title = self.child(Text(Assets.get_font("default-35"), t, "white", Vector2D(10, self.size.y/2), "midleft", visible=False))
        self.tabs: TabMenue = tabs

        #btns
        self.close = btn(Game.width-40, 30, "X", self.sub)
        self.build = btn(Game.width-160, 100, "Build", self.sub)
        self.run = btn(Game.width-270, 100, "Run", self.sub)

        r = self.child(Rect(0, Game.height-30, Game.width, 30, Colors["pannel"], 0, 10))
        self.child(Text(Assets.get_font("default-25"), f"GUI Version: {Game.version} | PyScene Version: {version("PyScene")}", "white", Vector2D(5, r.pos.y+r.rect.height/2), "midleft", 100))

    def update(self):
        if Game.RENAMETITLE:
            t = f"PyScene-Studio Editor - {Game.project}"
            self.title.set_text(t)

        self.close.update()
        self.build.update()
        self.run.update()

        if self.close.pressed: 
            self.tabs.save()
            Game.BREAK = True
        elif self.build.pressed: 
            self.tabs.save()
            Build(Game.project)
        elif self.run.pressed or Keys.is_pressed(Keys.f5): 
            self.tabs.save()
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

def update_project_files(name):
    print("[Editor] - Updating Project Files "+name)
    p = get_save_dir_path()+f"/{name}/"
    #project file
    with open(p+"project.json", "r") as f: data = json.load(f)
    data = update_dict(data, DEFAULTPROJECT.copy())
    with open(p+"project.json", "w") as f: json.dump(data, f, indent=4)

    #scenes
    for scene_name in os.listdir(p+"scenes/"):
        if not scene_name.endswith(".json"): continue
        with open(p+"scenes/"+scene_name, "r") as f: data = json.load(f)
        data = update_dict(data, DEFAULTSCENE.copy())
        with open(p+"scenes/"+scene_name, "w") as f: json.dump(data, f, indent=4)

    #objects
    for object_name in os.listdir(p+"objects/"):
        if not object_name.endswith(".json"): continue
        with open(p+"objects/"+object_name, "r") as f: data = json.load(f)
        data = update_dict(data, DEFAULTOBJECT.copy())
        with open(p+"objects/"+object_name, "w") as f: json.dump(data, f, indent=4)

def update_dict(old, new):
    for k, v in new.items():
        if k not in old:
            # Safely clone the new feature/setting so the player owns their own copy
            old[k] = copy.deepcopy(v)
        elif isinstance(old[k], collections.abc.Mapping) and isinstance(v, collections.abc.Mapping):
            # Recursively fill in missing settings inside existing menus
            update_dict(old[k], v)
        # If it exists in old as a scalar (e.g., player's high score), it's left completely alone
            
    return old



