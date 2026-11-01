from PyScene import Assets, Game
import pygame
import json

Colors = {
    "bg": [29, 34, 41],
    "pannel": [54, 61, 74],
    "b": [0, 0, 0],
}


def load_manager_assets():
    #default sys fonts
    _default(35)
    _default(23)
    #colors
    Assets.colors = {
    "bg": [29, 34, 41],
    "pannel": [54, 61, 74],
    "btn_around": [0, 0, 0],
    "sub": [33, 38, 46]
}
def load_editor_assets():
    #default sys fonts
    _default(45)
    _default(35)
    _default(25)

def _default(size):
    Assets.fonts[f"default-{size}"] = pygame.font.Font(None, size)
    

