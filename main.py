from PyScene import *
import os
import pygame
from manager.ProjectManager import ProjectManager
from utils.load_assets import load_manager_assets

#file for launching the project manager and some basic init stuff
width, height = 1024, 600
Game.init(width, height, "PyScene-Studio Project Manager", "black", 60, False, False)

Game.version = "0.0.1"

Assets.colors = {}

print("PyScene loaded successfully\n")
load_manager_assets()
print("[Studio] - Manager Assets Loaded")


ProjectManager()
