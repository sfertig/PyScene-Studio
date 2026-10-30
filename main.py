from PyScene import *
from src.manager.ProjectManager import ProjectManager
from src.utils.files import init_save_dir
from src.Runner import get_python_command
import pygame
import webbrowser

#check if user has python installed
py = get_python_command()
if not py:
    print("[Runner Error] - Python is not installed or not found in system PATH!")
    Game.init(300, 200, "PYSCENE ERROR", "black", 60, False, True)
    webbrowser.open("https://www.python.org/downloads/")
    Text(pygame.font.Font(pygame.font.get_default_font(), 20), "Python is not installed or not\n found in system PATH!", "red", Vector2D(Game.width/2, Game.height/2))
    Game.Run(False, True) #will quick pyscene once window is closed
#install and uplly upgrade pyscene
print("Loading PyScene")
#os.system("python -m pip install --upgrade --no-cache-dir PyScene")

Game.version = "0.2.2"

Assets.colors = {}

print("PyScene loaded successfully\n")

print("[Files] - Checking save directory\n")

if not init_save_dir():
    print("[Files] - Save directory created")
else:
    print("[Files] - Save directory already exists")

Game._project_manager = ProjectManager
ProjectManager()

