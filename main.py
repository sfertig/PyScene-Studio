from PyScene import *
import os
import pygame
from src.manager.ProjectManager import ProjectManager
from src.utils.load_assets import load_manager_assets
from src.utils.files import init_save_dir

#file for launching the project manager and some basic init stuff
width, height = 1024, 600
Game.init(width, height, "PyScene-Studio Project Manager", "black", 60, False, False)

Game.version = "0.0.1"

Assets.colors = {}

print("PyScene loaded successfully\n")
load_manager_assets()
print("[Studio] - Manager Assets Loaded\n")

print("[Files] - Checking save directory\n")

if init_save_dir():
    print("[Files] - Save directory created")
else:
    print("[Files] - Save directory already exists")


ProjectManager()

