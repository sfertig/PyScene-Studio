import colorsys
from PyScene import *
import PyScene
import pygame
import json
import os
from functools import partial

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

class _input(GameObj):
    def __init__(self, x, y, w, h, value, sub: SubScreen):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        self.value = value

        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.r = pygame.Rect((0, 0), self.size.to_int())
        self._rect = pygame.Rect(self.pos.to_int(), self.size.to_int())

    def get_value(self): return None
    def update(self): pass
    def render(self): pass
        
class IntInput(_input):
    def __init__(self, x, y, w, h, value, sub: SubScreen):
        super().__init__(x, y, w, h, value, sub)
        self.text = self.child(Text(Assets.get_font("default-25"), str(self.value), "white", Vector2D(self.r.centerx, self.r.centery), visible=False))
        self.w = 0
        self.hovered = False
        self.pressed = False
        self.buffer = 0
        self.default = 0

    def get_value(self) -> int:
        return int(format_int(self.text.text) or "0")

    def update(self):
        if self.buffer < 0: self.buffer = 0
        mpos = self.PSub.local_mouse_pos().to_int()
        self.hovered = self._rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = -1

        if self.pressed: self.w = 5

        if Game.click:
            if self.hovered: self.pressed = not self.pressed
            else: self.pressed = False
            if not self.pressed: 
                self.text.set_text(format_int(self.text.text))

        if not self.pressed: return
        #text input and format
        text = self.text.text
        for event in Game.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE: continue #text = text[:-1]
                elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE: 
                    self.pressed = False
                    text = str(format_int(self.text.text))
                    break
                else: text += event.unicode
        if Keys.is_held(Keys.backspace) and self.buffer == 0: 
            text = text[:-1]
            self.buffer = 15
        elif not Keys.is_held(Keys.backspace): self.buffer = 0
        if text != self.text.text: self.text.set_text(text)
        

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["b"], self.r, self.w)
        self.text.render_to(self.sub.screen)

        self.sub.render()

class BoolInput(_input):
    def __init__(self, x, y, w, h, value, sub: SubScreen):
        super().__init__(x+(w//2-12.5), y, 25, 25, value, sub)
        self.size = Vector2D(25, 25)
        self.value = value

        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.r = pygame.Rect((0, 0), self.size.to_int())
        self._rect = pygame.Rect(self.pos.to_int(), self.size.to_int())
        self.w = 2
        self.hovered = False
        self.default = True

    def get_value(self): return self.value

    def update(self):
        mpos = self.PSub.local_mouse_pos().to_int()
        self.hovered = self._rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = 2

        if self.value: self.w = 0

        if Game.click and self.hovered:
            self.value = not self.value

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["b"], self.r, self.w)

        self.sub.render()

class StrInput(_input):
    def __init__(self, x, y, w, h, value, sub: SubScreen):
        super().__init__(x, y, w, h, value, sub)
        self.text = self.child(Text(Assets.get_font("default-25"), str(self.value), "white", Vector2D(self.r.centerx, self.r.centery), visible=False))
        self.w = 0
        self.hovered = False
        self.pressed = False
        self.buffer = 0
        self.default = ""

    def get_value(self) -> str:
        return self.text.text or ""

    def update(self):
        if self.buffer < 0: self.buffer = 0
        mpos = self.PSub.local_mouse_pos().to_int()
        self.hovered = self._rect.collidepoint(mpos)
        if self.hovered: self.w = 5
        else: self.w = -1

        if self.pressed: self.w = 5

        if Game.click:
            if self.hovered: self.pressed = not self.pressed
            else: self.pressed = False
            #if not self.pressed: self.text.set_text(format_int(self.text.text))

        if not self.pressed: return
        #text input and format
        text = self.text.text
        for event in Game.events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE: continue #text = text[:-1]
                elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE: 
                    self.pressed = False
                    text = self.text.text#str(format_int(self.text.text))
                    break
                else: text += event.unicode
        if Keys.is_held(Keys.backspace) and self.buffer == 0: 
            text = text[:-1]
            self.buffer = 15
        elif not Keys.is_held(Keys.backspace): self.buffer = 0
        if text != self.text.text: self.text.set_text(text)
        

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, Colors["b"], self.r, self.w)
        self.text.render_to(self.sub.screen)

        self.sub.render()

class ColorInput(_input):
    def __init__(self, x, y, w, h, value: list[int], sub: SubScreen):
        super().__init__(x, y, w, h, value, sub)
        self._r = pygame.Rect(self.r.topleft, (20, self.r.height))
        self.display = value
        self.bar_rect = pygame.Rect(22, 0, w-22, h)
        self.gradient_surface = pygame.Surface((self.bar_rect.width, self.bar_rect.height))
        for x in range(self.bar_rect.width):
            hue = x / self.bar_rect.width  # Hue goes from 0.0 to 1.0
            # Convert HSV to RGB (Saturation=1.0, Value=1.0)
            rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))
            pygame.draw.line(self.gradient_surface, color, (x, 0), (x, self.bar_rect.height))
        self.default = [0, 255, 0]

    def get_value(self): return self.value

    def update(self):
        self.display = self.value
        mpos = self.PSub.local_mouse_pos().to_int()
        if self._rect.collidepoint(mpos):
            #set display to color at mouse pos
            pos = self.sub.local_mouse_pos().to_int()
            pos = (pos[0]-22, pos[1])
            if pos[0] < 0 or pos[0] >= self.bar_rect.width or pos[1] < 0 or pos[1] >= self.bar_rect.height:
                return
            self.display = self.gradient_surface.get_at(pos)
            if Game.click:
                self.value = list(self.display)
        

    def render(self):
        self.sub.clear()

        pygame.draw.rect(self.sub.screen, self.display, self._r)
        #pygame.draw.rect(self.sub.screen, Colors["b"], self.r, self.w)
        self.sub.screen.blit(self.gradient_surface, self.bar_rect.topleft)
        pygame.draw.line(self.sub.screen, Colors["b"], (20, 0), (20, self.bar_rect.height), 2)

        self.sub.render()

class AssetInput(_input):
    def __init__(self, x, y, w, h, value, sub: SubScreen, asset_type: str):
        super().__init__(x, y, w, h, value, sub)
        project_path = os.path.join(get_save_dir_path(), Game.project)
        self.asset_type = asset_type
        self.assets = [
            definition["name"]
            for definition in get_project_asset_definitions(project_path, asset_type)
        ]
        if not self.value and self.assets:
            self.value = self.assets[0]
        self.hovered = False

    def get_value(self) -> str:
        return self.value

    def update(self):
        self.hovered = self._rect.collidepoint(self.PSub.local_mouse_pos().to_int())
        if not Game.click or not self.hovered or not self.assets:
            return

        mouse_x = self.PSub.local_mouse_pos().x - self._rect.x
        if self.value in self.assets:
            index = self.assets.index(self.value)
        else:
            index = -1
        if mouse_x < self.size.x / 2:
            index = (index - 1) % len(self.assets)
        else:
            index = (index + 1) % len(self.assets)
        self.value = self.assets[index]

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Colors["b"], self.r, 2 if not self.hovered else 4)
        font = Assets.get_font("default-25")
        if not self.assets:
            label = "No assets"
        elif self.value not in self.assets:
            label = f"Missing: {self.value}"
        else:
            label = self.value

        max_width = max(0, self.r.width - 44)
        while label and font.size(label)[0] > max_width:
            label = label[:-1]
        if label != self.value and self.value in self.assets:
            while label and font.size(label + "...")[0] > max_width:
                label = label[:-1]
            label += "..."

        self.sub.screen.blit(font.render("<", True, "white"), (5, 2))
        self.sub.screen.blit(font.render(">", True, "white"), (self.r.width - 18, 2))
        rendered_label = font.render(label, True, "white")
        self.sub.screen.blit(rendered_label, rendered_label.get_rect(center=self.r.center))
        self.sub.render()

class Vector2DInput:
    def __init__(self, x, y, w, h, value: list[int], sub: SubScreen):
        self.pos = Vector2D(x, y)
        self.size = Vector2D(w, h)
        self.value = value
        self.sub = sub
        self.default = [0, 0]

        self.x = IntInput(x, y, w//2-5, h, value[0], sub)
        self.y = IntInput(x+w//2+5, y, w//2-5, h, value[1], sub)
        

    def get_value(self): 
        self.value[0] = self.x.get_value()
        self.value[1] = self.y.get_value()
        return self.value

    def update(self):
        self.x.update()
        self.y.update()

    def render(self):
        self.x.render()
        self.y.render()

class _types_:
    def __init__(self):
        self.int = IntInput
        self.bool = BoolInput
        self.str = StrInput
        self.color = ColorInput
        self.Vector2D = Vector2DInput
        self.image = partial(AssetInput, asset_type="image")
        self.font = partial(AssetInput, asset_type="font")
        self.animation = partial(AssetInput, asset_type="animation")
        self.tileset = partial(AssetInput, asset_type="tileset")

        self.screen = SubScreen

_types = _types_()

def format_int(text):
    #print("formatting...")
    for char in text:
        if not char.isdigit() and char != "-" and char != ".":
            text = text.replace(char, "")
    if text == "": text = "0"
    return text
