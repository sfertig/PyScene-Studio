from PyScene import *
import pygame
class Splash(Scene):
    def __init__(self):
        super().__init__("__splash__screen__")
        self.bg = Game.bg
        Game.bg = "black"
        self.t = Timer(2.3)
        self.done = False
        Text(pygame.font.Font(None, 40), "Made in PyScene-Studio", "white", Vector2D(Game.screen.get_width()//2, Game.screen.get_height()//2))

    def update(self):
        if self.t.is_done(): self.done = True