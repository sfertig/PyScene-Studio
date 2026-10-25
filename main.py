from PyScene import *
from src.manager.ProjectManager import ProjectManager
from src.utils.files import init_save_dir

#install and uplly upgrade pyscene
print("Loading PyScene")
#os.system("python -m pip install --upgrade --no-cache-dir PyScene")

Game.version = "0.1.1"

Assets.colors = {}

print("PyScene loaded successfully\n")

print("[Files] - Checking save directory\n")

if not init_save_dir():
    print("[Files] - Save directory created")
else:
    print("[Files] - Save directory already exists")

Game._project_manager = ProjectManager
ProjectManager()

