from PyScene import Assets
import pygame
import json

def load_manager_assets():
    #default sys fonts
    _default(35)
    _default(23)
    #colors
    with open("assets/Manager_colors.json", "r") as f:
        Assets.colors = json.load(f)

def _default(size):
    Assets.fonts[f"default-{size}"] = pygame.font.Font(None, size)
    

