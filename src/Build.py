from PyScene import *
import os
import json

from src.utils.files import *

class Build:
    def __init__(self, project_name):
        self.name = project_name #the project that is getting built
        self.path = get_save_dir_path()+"/"+self.name
        print("[Build] - Building project: "+self.name)

        self.project = json.load(open(self.path+"/project.json", "r")) #project details

        self.gen_main()
        print("[Build] - Project File Built: "+self.name)

        #loop over all files in scenes
        for file in os.listdir(self.path+"/scenes/"):
            if file.endswith(".json"):
                self.gen_scene(file[:-5])
                print("[Build] - Scene File Built: "+file[:-5]) 
        #gen objects
        for file in os.listdir(self.path+"/objects/"):
            if file.endswith(".json"):
                self.gen_object(file[:-5])
                print("[Build] - Scene File Built: "+file[:-5]) 
        print("[Build] - Project Built Successfully: "+self.name)

    def gen_main(self):
        p = self.path+"/_python/_main.py"
        i = self.project["window"]
        #generates the code in the _main.py file
        exists(p)
        data = ""
        data += "from PyScene import *\n"
        data += "from data.main import main\n" #this is the main scene
        #create pyscene window
        data += f"Game.init({i['width']}, {i['height']}, \"{i['title']}\", \"{i['bg_color']}\", {i['fps']}, {i['fullscreen']}, True)\n"
        data += "main()\n"
        data += "Game.Run()\n"
        with open(p, "w") as f:
            f.write(data)

    def gen_object(self, name):
        p = self.path+"/objects/"+name+".json"
        i = json.load(open(p, "r"))
        path = self.path+f"/_python/data/{name}.py"
        exists(path)
        data = ""
        #create imports
        data += "from PyScene import *\n"
        #other imports
        imports: list[str] = i["imports"]
        for _i in imports:
            data += f"{_i}\n"

        vars: list[str] = i["variables"]
        init = f"Vector2D({vars["pos"][0]}, {vars["pos"][1]}), {vars["z_index"]}, {vars["active"]}, {vars["visible"]}, {vars["Global"]}"
        #create object and basic functions
        data += "class "+name+"(GameObj):\n"
        data += "    def __init__(self):\n" 
        data += f"        super().__init__({init})\n"
        #code
        code: list[str] = i["functions"]["__init__"]["code"]
        for _i in code:
            data += f"        {_i}\n"

        #funcs            
        data = self.createFuncs(data, name, i)

        #write to file
        with open(path, "w") as f:
            f.write(data)

    def gen_scene(self, name):
        p = self.path+"/scenes/"+name+".json"
        i = json.load(open(p, "r"))
        path = self.path+f"/_python/data/{name}.py"
        exists(path)
        data = ""
        #create imports
        data += "from PyScene import *\n"
        #other imports
        imports: list[str] = i["imports"]
        for _i in imports:
            data += f"{_i}\n"

        #create scene and basic functions
        data += "class "+name+"(Scene):\n"
        data += "    def __init__(self):\n" 
        data += f"        super().__init__(\"{i['name']}\")\n"
        #code
        code: list[str] = i["functions"]["__init__"]["code"]
        for _i in code:
            data += f"        {_i}\n"

        #funcs
        data = self.createFuncs(data, name, i)

        #write to file
        with open(path, "w") as f:
            f.write(data)

    def createFuncs(self, data, name, i):
        for func in i["functions"]:
            if func == "__init__":
                continue
            _args: list[str] = i["functions"][func]["args"]
            args = ""
            #turn args into a string
            for _i in _args: args += f"{_i}, "
            #add comma at brginning and remove from end
            args = args[:-2]
            if len(_args) > 0: args = f", {args}"
            data += f"    def {func}(self{args}):\n"
            code: list[str] = i["functions"][func]["code"]
            for _i in code:
                data += f"        {_i}\n"

        data += "\n"
        return data



def exists(path, write=""):
    #checks if a file exists, if not create it
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(write)

