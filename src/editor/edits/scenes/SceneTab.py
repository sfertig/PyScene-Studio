import colorsys

from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

from .Inputs import *
from .Objs import *
from .Create import *
from .VisualPannel import VisualEditor
from ..objs.LeftPannel import LeftPannel
from ..objs.CodePannel import CodePannel

class VisualSceneTabEdit(GameObj):
    def __init__(self, name):
        print(name)
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], Game.screen)
        self.name = name

        with open(get_save_dir_path()+f"/{Game.project}/scenes/{self.name}.json", "r") as f: self.data: dict = json.load(f)

        self.script_mode = False
        self.mode_btn = btn(
            (self.size.x - 200) // 2,
            0,
            200,
            30,
            "Visual Mode",
            self.sub,
            -1,
            5,
            Colors["pannel"],
        )
        self.script_left = self.child(LeftPannel(self.sub, self.data))
        self.script_code_sub = SubScreen(
            420,
            0,
            self.size.x - 420,
            self.size.y,
            Colors["pannel"],
            self.sub.screen,
            self.sub,
        )
        self.script_code_title = self.child(
            Text(
                Assets.get_font("default-35"),
                "__init__",
                "white",
                Vector2D(self.script_code_sub.dim.x // 2, 50),
                visible=False,
            )
        )
        self.script = self.child(
            CodePannel(
                self.script_code_sub,
                self.data,
                pos=Vector2D(10, 80),
                height=self.size.y - 90,
            )
        )
        self.gen()

    def gen(self):
        #components

        self.r = pygame.Rect(self.sub.dim.x-400, 35, 400, self.sub.dim.y-35)
        self.test = pygame.Rect(420, 35, self.sub.dim.x-840, self.sub.dim.y-35)
        self.objs = self.child(ObjectsMenue(self.name, self.data, self.sub))
        self.create = self.child(CreateObj(self.sub, self.data.copy(), self.test))
        self.visual_editor = self.child(
            VisualEditor(self.test, self.sub, self.data)
        )

    def save(self):
        self.objs.save()
        self.script.save()
        with open(get_save_dir_path()+f"/{Game.project}/scenes/{self.name}.json", "w") as f: json.dump(self.data, f, indent=4)

    def update(self):
        self.mode_btn.update()
        if self.mode_btn.pressed:
            self.script_mode = not self.script_mode
            self.mode_btn.text.set_text(
                "Script Mode" if self.script_mode else "Visual Mode"
            )
            self.save()

        if self.script_mode:
            self.script_left.update()
            if self.script_left.OPEN is not None:
                self.script_code_title.set_text(self.script_left.OPEN)
            self.script.update(self.script_left.OPEN)
            return

        if self.create.update():
            self.data["objects"] = self.create.data.copy()
            self.gen()
            self.save()
            return

        self.visual_editor.update()

        if self.objs.update():
            self.gen()
            self.save()
            return

    def print_dict(self, data): #debug func
        for k, v in data.items():
            print(k, v)
            print("\n")

    def render(self):
        self.sub.clear()

        if self.script_mode:
            pygame.draw.rect(self.sub.screen, Colors["pannel"], (0, 0, 400, self.size.y))
            self.script_left.render()
            self.script_code_sub.clear()
            self.script_code_title.render_to(self.script_code_sub.screen)
            pygame.draw.line(
                self.script_code_sub.screen,
                "black",
                (10, 75),
                (self.script_code_sub.dim.x - 10, 75),
            )
            self.script.render()
            self.script_code_sub.render()
        else:
            pygame.draw.rect(self.sub.screen, Colors["pannel"], self.r)
            self.visual_editor.render()
            #pygame.draw.rect(self.sub.screen, Colors["pannel"], self.test)
            self.objs.render()
            self.create.render()

        self.mode_btn.render()
        self.sub.render()
