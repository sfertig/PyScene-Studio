from PyScene import *
import pygame
import json

from ..utils.load_assets import Colors
from ..utils.files import *

class TabMenue(GameObj):
    def __init__(self, y):
        super().__init__(Vector2D(0, y), 50)
        self.size = Vector2D(Game.width, 40)
        self.sub = SubScreen(0, y, self.size.x, self.size.y, Colors["pannel"], Game.screen)
        self.rect = pygame.Rect((0, 0), self.size.to_int())
        self.r = pygame.Rect((0, 0), (self.size.x-110, self.size.y))
        self.tabs: list[Tab] = []

        self.gen()

        self.btn_rect = pygame.Rect(Game.width-110, 5, 100, 30)
        self.closeText = self.child(Text(Assets.get_font("default-35"), "CLOSE", "white", Vector2D(self.btn_rect.centerx, self.btn_rect.centery), visible=False))
        self.hovered = False
        self.w = 2

    def gen(self):
        self.tabs.clear()
        self.tabs.append(Tab(10, "Settings", self.sub, self.r))
        self.tabs.append(Tab(self.tabs[-1].pos.x+self.tabs[-1].size.x+5, "Assets", self.sub, self.r))
        self.tabs.append(Tab(self.tabs[-1].pos.x+self.tabs[-1].size.x+5, "Create", self.sub, self.rect))
        self.LPos = (self.tabs[-1].pos.x+self.tabs[-1].size.x+5, 5)
        self.tabs.append(SceneTab(self.tabs[-1].pos.x+self.tabs[-1].size.x+10, "main", self.sub, self.r)) #main scene
        self.tabs[-1].active = True #auto load main scene

    def update(self):
        for t in self.tabs:
            t.update_tab()

        mpos = self.sub.local_mouse_pos().to_int()
        self.hovered = self.btn_rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = -1
        if Game.click and self.btn_rect.collidepoint(mpos): 
            Game.click = False
            self.remove_active()

    def remove_active(self):
        index = 0
        for t in self.tabs:
            if t.name in ["Settings", "Assets", "Create"]: continue
            if t.active: index = self.tabs.index(t)
        if index == 0: return
        width = self.tabs[index].pos.x - self.tabs[index-1].pos.x
        self.tabs.remove(self.tabs[index])
        #move tabs to the left -10
        for t in self.tabs[index:]:
            t.move(-width)


    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Colors["b"], self.rect, 2)
        for t in self.tabs:
            t.render_tab()
        #render line and close btn
        pygame.draw.line(self.sub.screen, Colors["b"], self.LPos, (self.LPos[0], self.size.y-5))
        pygame.draw.rect(self.sub.screen, Colors["b"], self.btn_rect, self.w)
        self.closeText.render_to(self.sub.screen)

        self.sub.render()


class Tab:
    def __init__(self, x, name, sub, rect):
        self.pos = Vector2D(x, 5)
        self.name = name
        self.text = Text(Assets.get_font("default-35"), name, "white", Vector2D(self.pos.x + 10, self.pos.y), visible=False)
        self.size = Vector2D(self.text.rect.width+20, sub.dim.y - 10)
        self.rect = pygame.Rect((0, 0), self.size.to_int())
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen
        self.text.set_pos(Vector2D(self.rect.centerx, self.rect.centery))
        self.P_Sub: SubScreen = sub
        self._rect = rect

        self.hovered = False
        self.w = -1
        self.active = False

    def move(self, amount):
        self.pos.x += amount
        self.sub.pos.x += amount
    
    def update_tab(self):
        mpos = self.sub.local_mouse_pos().to_int()
        _mpos = self.P_Sub.local_mouse_pos().to_int()
        self.hovered = self.rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = -1

        if self.active: self.w = 5
        if Game.click and self._rect.collidepoint(_mpos):
            if not self.active and self.hovered:
                self.active = True
            elif self.active and not self.hovered:
                self.active = False

    def render_tab(self):
        self.sub.clear()
        pygame.draw.rect(self.screen, Colors["b"], self.rect, self.w)
        self.text.render_to(self.screen)
        self.sub.render()

    def close(self):
        self.destroy()

    def destroy(self):
        self.text.destroy()

#region Tab Types

#Scene Tab
class SceneTab(Tab):
    def __init__(self, x, scene_name, sub, rect):
        super().__init__(x, scene_name+" Scene", sub, rect)

    def update(self):
        pass

    def render(self):
        pass

#Object Tab
class ObjTab(Tab):
    def __init__(self, x, obj_name, sub, rect):
        super().__init__(x, obj_name + " Object", sub, rect)

    def update(self):
        pass

    def render(self):
        pass

