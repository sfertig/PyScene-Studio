from PyScene import *
import os
import pygame
import sys
from importlib.metadata import version
from ..utils.files import gen_project_lists, get_save_dir_path


class ProjectManager:
    def __init__(self):
        #create objs
        Game.bg = Assets.colors["bg"]
        Text(Assets.get_font("default-35"), "PyScene-Studio", "white", Vector2D(5, 5), "topleft", 5)
        Text(Assets.get_font("default-23"), f"GUI Version: {Game.version} | PyScene Version: {version("PyScene")}", "white", Vector2D(5, Game.height-20), "topleft", 5)
        Rect(5, 40, Game.width-10,  Game.height-75, Assets.colors["pannel"], -6)

        Game.projects = gen_project_lists() #name: path
        Game.RELOAD = False

        TopBar()
        ProjectList()

        Game.Run(False)

class TopBar(GameObj):
    def __init__(self):
        super().__init__(Vector2D(5, 40), 1)
        self.sub = SubScreen(self.pos.x, self.pos.y, Game.width-10, 50, Assets.colors["pannel"], Game.screen)

        self.create = None

        self.btns: dict[str, btn] = {
            "create": btn(5, 5, 75, 40, "+ Create", self.sub),
            "rescan": btn(90, 5, 75, 40, "Rescan", self.sub),
            "import": btn(175, 5, 75, 40, "Import", self.sub),
        }

    def update(self):
        Game.RELOAD = False
        if self.create is None:
            for btn in self.btns.values():
                btn.update()
        elif self.create.DONE:
            self.create = None
            Game.RELOAD = True

        if self.btns["create"].pressed and not self.create: 
            self.btns["create"].pressed = False
            self.create = CreateMenue()
            Game.RELOAD = True
        elif self.btns["rescan"].pressed: 
            Game.RELOAD = True
            print("[TopBar] - Rescanning projects...")

        if Game.RELOAD:
            Game.projects = gen_project_lists()

    def render(self):
        self.sub.clear()
        for btn in self.btns.values():
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

class TextInput(GameObj):
    def __init__(self, x, y, w, h, font, text="", sub=None, _input=True):
        super().__init__(Vector2D(x, y), 3)
        self.size = Vector2D(w, h)
        s = Game.screen
        if sub: s = sub.screen
        self.sub = SubScreen(x, y, w, h, Assets.colors["bg"], s, sub)
        self.rect = pygame.Rect((0, 0), self.size.to_int())
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
        mpos = self.sub.local_mouse_pos().to_int()
        self.hovered = self.rect.collidepoint(mpos)
        if not self.active:
            if self.hovered: self.w = 5
            else: self.w = 2

        if Game.click:
            if not self.hovered:
                Game.click = False
                self.active = False
            else:
                Game.click = False
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
                    self.buffer = 15
                elif not Keys.is_held(Keys.backspace): self.buffer = 0
                if text != self.text.text: self.text.set_text(text)

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Assets.colors["btn_around"], self.rect, self.w)
        self.text.render_to(self.sub.screen)
        self.sub.render()

class CreateMenue(GameObj):
    def __init__(self):
        self.size = Vector2D(500, 400)
        super().__init__(Vector2D(Game.width/2-self.size.x/2, Game.height/2-self.size.y/2), 100)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Assets.colors["pannel"], Game.screen)
        self.text = Text(Assets.get_font("default-35"), "Create New Project", "white", Vector2D(self.size.x/2, 20), "center", 5, visible=False)

        self.nameText = Text(Assets.get_font("default-35"), "Name:", "white", Vector2D(5, 60), "topleft", 5, visible=False)

        self.nameInput = TextInput(5, 100, self.size.x-10, 50, Assets.get_font("default-23"), sub=self.sub)
        self.input_active = False

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
        self.child(self.nameInput) 

    def update(self):
        self.create.update()
        self.cancel.update()

        if self.cancel.pressed:
            self.destroy()
            self.DONE = True
            return

        if self.create.pressed and len(self.nameInput.text.text) > 0:
            self.nameInput.text.set_text(self.check_name())
            if self.nameInput.text.text in Game.projects.keys(): return
            self.DONE = True
            self.destroy()
            self.gen()
            return

        if self.input_active and not self.nameInput.active:
            self.nameInput.text.set_text(self.check_name())
        self.input_active = self.nameInput.active

    def gen(self):
        name = self.nameInput.text.text
        print("[Create] - Generating project: "+name)
        path = get_save_dir_path()+"/"+name
        #gen project
        Game.projects[name] = path
        #gen folder
        os.makedirs(path)

    def check_name(self):
        text = self.nameInput.text.text
        #make the text folder safe
        for char in ["\\", "/", ":", "*", "?", "\"", "<", ">", "|", ".", " ", "#", "%", "$", "&", "@", "!", "^"]:
            text = text.replace(char, "_")
        return text

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Assets.colors["btn_around"], self.rect, 2)
        pygame.draw.line(self.sub.screen, Assets.colors["btn_around"], (10, 35), (self.size.x-10, 35), 2)
        self.text.render_to(self.sub.screen)

        self.nameText.render_to(self.sub.screen)
        self.nameInput.render()

        pygame.draw.line(self.sub.screen, Assets.colors["btn_around"], (10, self.size.y-90), (self.size.x-10, self.size.y-90), 2)
        self.create.render()
        self.cancel.render()

        self.sub.render()


class ProjectList(GameObj):
    def __init__(self):
        super().__init__(Vector2D(10, 90))
        self.size = Vector2D(Game.width-110,  Game.height-130)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Assets.colors["sub"], Game.screen)

        self.gen()

    def gen(self):
        #projects
        self.projects: list[Project] = []

        y = 10
        for key, value in Game.projects.items():
            self.projects.append(Project(y, key, value, self.sub))
            y += self.projects[0].rect.height+15


    def update(self):
        if Game.RELOAD:
            for project in self.projects:
                project.destroy()
            self.gen()
            Game.RELOAD = False

    def render(self):
        self.sub.clear()
        for project in self.projects:
            project.render()
        self.sub.render()


class Project(GameObj):
    def __init__(self, y, name, path, sub):
        super().__init__(Vector2D(10, y), visible=False)
        self.rect = pygame.Rect((0, 0), (Game.width-130, 50))
        self.parentSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.rect.width, self.rect.height, Assets.colors["pannel"], sub.screen, sub)
        self.subRect = pygame.Rect(self.pos.to_int(), self.rect.size)

        self.name = Text(Assets.get_font("default-23"), name, "white", Vector2D(5, self.rect.centery), "midleft", 5, visible=False)
        self.child(self.name)
        self.path = path

        self.hovered = False
        self.active = False
        self.w = 2

    def update(self):
        mpos = self.parentSub.local_mouse_pos().to_int()
        self.hovered = self.subRect.collidepoint(mpos)
        if not self.active:
            if self.hovered: self.w = 5
            else: self.w = 2

        if Game.click:
            if not self.hovered:
                self.active = False
            else:
                self.active = True


    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Assets.colors["btn_around"], self.rect, self.w)
        self.name.render_to(self.sub.screen)

        self.sub.render()



