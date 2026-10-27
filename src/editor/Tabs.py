from PyScene import *
import pygame
import json

from ..utils.load_assets import Colors
from ..utils.files import *

from .edits import *

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

    def new_scene(self, name):
        for tab in self.tabs:
            if tab.active: 
                tab.active = False
                tab.on_non_active()
        self.tabs.append(SceneTab(self.tabs[-1].pos.x+self.tabs[-1].size.x+5, name, self.sub, self.r))
        self.tabs[-1].active = True
        self.tabs[-1].on_active()

    def gen(self):
        self.tabs.clear()
        self.tabs.append(Tab(10, "Settings", self.sub, self.r))
        self.tabs.append(Tab(self.tabs[-1].pos.x+self.tabs[-1].size.x+5, "Assets", self.sub, self.r))
        self.tabs.append(TabManager_tab(self.tabs[-1].pos.x+self.tabs[-1].size.x+5, self.sub, self.r, self))
        self.LPos = (self.tabs[-1].pos.x+self.tabs[-1].size.x+2.5, 5)
        self.tabs.append(SceneTab(self.tabs[-1].pos.x+self.tabs[-1].size.x+5, "main", self.sub, self.r)) #main scene
        #self.tabs[-1].active = True #auto load main scene
        #self.tabs[-1].on_active() commented out for debug and working on tab manager rn
        self.tabs[2].active = True
        self.tabs[2].on_active()

    def update(self):
        active = False
        for t in self.tabs:
            t.update_tab()
            if t.active: active = True
        if not active: 
            self.tabs[2].active = True #Tab Manager
            self.tabs[2].on_active()

        mpos = self.sub.local_mouse_pos().to_int()
        self.hovered = self.btn_rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = -1
        if Game.click and self.btn_rect.collidepoint(mpos): 
            Game.click = False
            self.remove_active()

    def remove_active(self):
        index = 0
        for t in self.tabs[3:]:
            if t.active: index = self.tabs.index(t)
        if index == 0: return
        self.tabs[index].close()
        self.tabs[index].on_close()
        self.tabs.remove(self.tabs[index])
        #move tabs to the left
        tabs: list[Tab] = []
        for t in self.tabs[index:]:
            tabs.append(t)
            self.tabs.remove(t)
        if len(tabs) > 0: tabs[0].active = True
        else: 
            self.tabs[-1].active = True #Tab Manager
            self.tabs[-1].on_active()
        for t in tabs:
            t.move(self.tabs[-1].pos.x+self.tabs[-1].size.x+5)
            self.tabs.append(t)


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

#region Tab
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

    #functions all tabs will later have
    def on_active(self): pass
    def on_non_active(self): pass
    def on_close(self): pass
    def update(self): pass
    def render(self): pass

    def move(self, amount):
        self.pos.x = amount
        self.sub.pos.x = amount
    
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
                self.on_active()
            elif self.active and not self.hovered:
                self.active = False
                self.on_non_active()

        self.update()

    def render_tab(self):
        self.render()
        self.sub.clear()
        pygame.draw.rect(self.screen, Colors["b"], self.rect, self.w)
        self.text.render_to(self.screen)
        self.sub.render()

    def close(self):
        self.destroy()

    def destroy(self):
        self.text.destroy()

#endregion

#region Tab Types

#Tab Manager
class TabManager_tab(Tab):
    def __init__(self, x, sub, rect, tabs):
        super().__init__(x, "Tab Manager", sub, rect)
        self.obj = TabManagerEdit(tabs)
        self.obj.active = False
        self.obj.visible = False

    def on_active(self):
        self.obj.visible = True
        self.obj._active = True

    def on_non_active(self):
        self.obj.visible = False
        self.obj._active = False

    def on_close(self):
        if self.obj: self.obj.destroy()
        self.obj = None


#Scene Tab
class SceneTab(Tab):
    def __init__(self, x, scene_name, sub, rect):
        super().__init__(x, scene_name+" Scene", sub, rect)


#Object Tab
class ObjTab(Tab):
    def __init__(self, x, obj_name, sub, rect):
        super().__init__(x, obj_name + " Object", sub, rect)


#endregion

