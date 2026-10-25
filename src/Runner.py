import subprocess
import sys
from .utils.files import *

def Runner(project_name):
    # just start the _main.py file
    path = get_save_dir_path() + "/" + project_name + "/_python/_main.py"
    
    # Pass -Xfrozen_modules=off right after the python executable
    subprocess.Popen(
    [sys.executable, "-Xfrozen_modules=off", path],
    creationflags=subprocess.CREATE_NEW_CONSOLE
    )

    print("[Runner] - Project running: "+project_name)