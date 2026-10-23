from PyScene import *
import os
import pygame
import json
import sys
from importlib.metadata import version


class ProjectManager:
    def __init__(self):
        #create objs
        Game.bg = Assets.colors["bg"]
        Text(Assets.get_font("default-35"), "PyScene-Studio", "white", Vector2D(5, 5), "topleft", 5)
        Text(Assets.get_font("default-23"), f"GUI Version: {Game.version} | PyScene Version: {version("PyScene")}", "white", Vector2D(5, Game.height-20), "topleft", 5)
        Rect(5, 40, Game.width-10,  Game.height-75, Assets.colors["pannel"], -6)
        Rect(10, 90, Game.width-110,  Game.height-130, Assets.colors["sub"], -5)

        with open("data/projects.json", "r") as f:
            self.prjData = json.load(f)

        TopBar()

        Game.Run(True)

class TopBar(GameObj):
    def __init__(self):
        super().__init__(Vector2D(5, 40), 1)
        self.sub = SubScreen(self.pos.x, self.pos.y, Game.width-10, 50, Assets.colors["pannel"], Game.screen)

        self.create = None

        self.btns: list[btn] = [
            btn(5, 5, 75, 40, "+ Create", self.sub),
            btn(90, 5, 75, 40, "Rescan", self.sub),
            btn(175, 5, 75, 40, "Import", self.sub),
        ]

    def update(self):
        if self.create is None:
            for btn in self.btns:
                btn.update()
                if btn.pressed: 
                    self.create = CreatMenue()
                    btn.pressed = False
        elif self.create.DONE:
            self.create = None

    def render(self):
        self.sub.clear()
        for btn in self.btns:
            btn.render()
        self.sub.render()

class btn:
    def __init__(self, x, y, w, h, text, sub):
        self.pos = Vector2D(x, y)
        self.size = Vector2D(w, h)
        self.rect = pygame.Rect(self.pos.to_int(), self.size.to_int())
        self.text = Text(Assets.get_font("default-23"), text, "white", Vector2D(self.rect.centerx, self.rect.centery), "center", 5, visible=False)
        self.sub: SubScreen = sub
        self.bg = Assets.colors["bg"]
        self.border = Assets.colors["btn_around"]
        self.w = 2

        self.hovered = False
        self.pressed = False
        self.active = True

    def update(self):
        self.pressed = False
        self.bg = Assets.colors["bg"]
        if not self.active: return
        mpos = self.sub.local_mouse_pos().to_int()
        self.hovered = self.rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = 2
        if Game.click and self.hovered:
            self.pressed = True
            Game.click = False
            self.bg = self.border

    def render(self):
        pygame.draw.rect(self.sub.screen, self.bg, self.rect)
        pygame.draw.rect(self.sub.screen, self.border, self.rect, self.w)
        self.text.render_to(self.sub.screen)

class CreatMenue(GameObj):
    def __init__(self):
        self.size = Vector2D(500, 400)
        super().__init__(Vector2D(Game.width/2-self.size.x/2, Game.height/2-self.size.y/2), 3)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Assets.colors["pannel"], Game.screen)
        self.text = Text(Assets.get_font("default-35"), "Create New Project", "white", Vector2D(self.size.x/2, 20), "center", 5, visible=False)
        self.nameText = Text(Assets.get_font("default-23"), "Name", "white", Vector2D(self.size.x/2, 50), "center", 5, visible=False)
        self.rect = pygame.Rect((0, 0), self.size.to_int())

        #btns
        self.create = btn(self.size.x/8, self.size.y-75, self.size.x/3, 50, "Create", self.sub)
        self.cancel = btn(self.size.x/2, self.size.y-75, self.size.x/3, 50, "Cancel", self.sub)

        self.DONE = False

        #add to children
        self.child(self.text)
        self.child(self.nameText)    
        self.child(self.create.text)
        self.child(self.cancel.text) #to destroy text when create 'win' closes    

    def update(self):
        self.create.update()
        self.cancel.update()

        if self.cancel.pressed:
            self.destroy()
            self.DONE = True

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Assets.colors["btn_around"], self.rect, 2)
        pygame.draw.line(self.sub.screen, Assets.colors["btn_around"], (10, 35), (self.size.x-10, 35), 2)
        self.text.render_to(self.sub.screen)

        self.nameText.render_to(self.sub.screen)

        pygame.draw.line(self.sub.screen, Assets.colors["btn_around"], (10, self.size.y-90), (self.size.x-10, self.size.y-90), 2)
        self.create.render()
        self.cancel.render()

        self.sub.render()


