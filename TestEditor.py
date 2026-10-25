from PyScene import *
from src.editor.Run import RunEditor
from src.manager.ProjectManager import ProjectManager
width, height = 1024, 600
Game.init(width, height, "PyScene-Studio Project Manager", "black", 60, False, True)
Game.version = "0.1.1"
Game._project_manager = ProjectManager
RunEditor("OBJECT_TEST")
#this file is for launching the editor directly for testing and developement