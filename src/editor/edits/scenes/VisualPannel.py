from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

class VisualEditor(GameObj):
    def __init__(self, rect, sub: SubScreen, data):
        super().__init__(Vector2D(rect.x, rect.y), visible=False, active=False)
        self.PSub = sub
        self.rect = rect
        self.data = data

        #load game bg
        with open(get_save_dir_path()+f"/{Game.project}/project.json", "r") as f:
            game_data: dict = json.load(f)

        self.sub = SubScreen(rect.x, rect.y, rect.width, rect.height, game_data["window"]["bg_color"], sub.screen, sub)

    def update(self):
        pass

    def render(self):
        self.sub.clear()
        pygame.draw.rect(
            self.sub.screen,
            Colors["pannel"],
            (0, 0, self.rect.width, self.rect.height),
            2,
        )

        self.sub.render()
