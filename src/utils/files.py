import os

####################
#  Folder / file initalisation
####################

def get_save_dir_path() -> str:
    """Stores save data in C:/Users/<Username>/.tearfultilling_saveData"""
    user_home = os.path.expanduser("~")
    return os.path.join(user_home, ".pyscene_studio_projects")

def init_save_dir():
    
    path = get_save_dir_path()
    exists = os.path.exists(path)
    
    # 1. Safe folder creation
    os.makedirs(path, exist_ok=True)

    return exists

def gen_project_lists():
    path = get_save_dir_path()
    folders =  os.listdir(path)
    projects = {}
    for folder in folders:
        projects[folder] = path+"/"+folder
    print(projects)
    return projects

