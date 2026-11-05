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

        ensure_project_tilemaps_dir(self.path)
        self.gen_assets()
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
                print("[Build] - Object File Built: "+file[:-5]) 
        print("[Build] - Project Built Successfully: "+self.name)

    def gen_main(self):
        p = self.path+"/_python/main.py"
        i = self.project["window"]
        #generates the code in the main.py file
        exists(p)
        data = ""
        data += "from PyScene import *\n"
        data += "from load_assets import load_assets\n"
        #create pyscene window
        data += f"Game.init({i['width']}, {i['height']}, \"{i['title']}\", \"{i['bg_color']}\", {i['fps']}, {i['fullscreen']}, True)\n"
        data += "load_assets()\n"
        data += "from data.main import main\n" #this is the main scene
        data += "main()\n"
        data += "Game.Run()\n"
        with open(p, "w") as f:
            f.write(data)

    def gen_assets(self):
        assets_dir = ensure_project_assets_dir(self.path)
        manifest_path = os.path.join(assets_dir, "manifest.json")
        if os.path.isfile(manifest_path):
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        else:
            manifest = {"definitions": []}

        lines = [
            "import os",
            "from PyScene import Assets",
            "",
            "_ASSET_DIR = os.path.join(os.path.dirname(__file__), \"assets\")",
            "",
            "def load_assets():",
        ]
        definitions = manifest.get("definitions", [])
        if not definitions:
            lines.append("    pass")

        for definition in definitions:
            name = definition["name"]
            if not isinstance(name, str) or not name.isidentifier():
                raise ValueError(f"Invalid asset name: {name!r}")

            asset_path = definition.get("file")
            if not isinstance(asset_path, str) or not asset_path:
                raise ValueError(f"Asset {name!r} must have a source file.")
            normalized_path = os.path.normpath(asset_path.replace("/", os.sep))
            assets_root = os.path.abspath(assets_dir)
            full_path = os.path.abspath(os.path.join(assets_root, normalized_path))
            try:
                contained = os.path.commonpath((assets_root, full_path)) == assets_root
            except ValueError:
                contained = False
            if not contained or normalized_path == os.curdir:
                raise ValueError(f"Asset path must point inside the assets directory: {asset_path!r}")
            path_expression = f"os.path.join(_ASSET_DIR, {normalized_path.replace(os.sep, '/')!r})"

            kind = definition["type"]
            if kind == "image":
                options = definition.get("options", {})
                rect = options.get("rect")
                lines.append(
                    f"    Assets.new_image({name!r}, {path_expression}, "
                    f"rect={rect!r}, scale={options.get('scale', 1.0)!r})"
                )
            elif kind == "animation":
                options = definition["options"]
                lines.append(
                    f"    Assets.new_image({name!r}, {path_expression})"
                )
                lines.append(
                    f"    Assets.new_animation({name!r}, Assets.get_image({name!r}), "
                    f"size={options['frame_size']!r}, fps={options['fps']!r}, "
                    f"loop={options['loop']!r})"
                )
            elif kind == "tilemap":
                options = definition["options"]
                lines.append(
                    f"    Assets.new_tileset({path_expression}, {name!r}, "
                    f"width={options['width']!r}, height={options['height']!r}, "
                    f"scale={options.get('scale', 1.0)!r})"
                )
            elif kind == "font":
                lines.append(
                    f"    Assets.new_font({name!r}, {path_expression}, "
                    f"{definition['options']['size']!r})"
                )
            elif kind == "sound":
                lines.append(f"    Assets.new_sound({name!r}, {path_expression})")
            else:
                raise ValueError(f"Unsupported asset type: {kind!r}")

        with open(os.path.join(self.path, "_python", "load_assets.py"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def gen_object(self, name):
        p = self.path+"/objects/"+name+".json"
        i = json.load(open(p, "r"))
        path = self.path+f"/_python/data/{name}.py"
        exists(path)
        data = ""
        #create imports
        data += "from PyScene import *\n"
        data += "import pygame\n"
        #other imports
        imports: list[str] = i["imports"]
        for _i in imports:
            data += f"{_i}\n"

        vars: list[str] = i["variables"]
        init = f"Vector2D({vars["pos"][0]}, {vars["pos"][1]}), {vars["z_index"]}, {vars["active"]}, {vars["visible"]}, {vars["Global"]}"
        #create object and basic functions

        #args
        dict_args = i["functions"]["__init__"]["args"]
        _args = []
        for _i in dict_args: _args.append(_i["name"])
        args = ""
        #turn args into a string
        for _i in _args: args += f"{_i}, "
        #add comma at brginning and remove from end
        args = args[:-2]
        if len(_args) > 0: args = f", {args}"

        data += "class "+name+"(GameObj):\n"
        data += f"    def __init__(self{args}):\n" 
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
        data += "import pygame\n"
        #other imports
        imports: list[str] = i["imports"]
        for _i in imports:
            data += f"{_i}\n"

        #create scene and basic functions
        data += "class "+name+"(Scene):\n"
        data = self._gen_init_scene(p, i, path, data)
        #code
        code: list[str] = i["functions"]["__init__"]["code"]
        for _i in code:
            data += f"        {_i}\n"

        #funcs
        data = self.createFuncs(data, name, i)

        #write to file
        with open(path, "w") as f:
            f.write(data)

    def _gen_init_scene(self, p: str, i: dict, path: str, data: str):
        data += "    def __init__(self):\n" 
        data += f"        super().__init__(\"{i['name']}\")\n"

        #create objects
        objs: dict[str: dict] = i["objects"]
        for obj in objs:
            _type = objs[obj]["obj_type"]
            vars: dict = objs[obj]["variables"]
            arg_definitions = getattr(PySceneObjectVarDef, _type, None)
            if arg_definitions is None:
                object_path = os.path.join(self.path, "objects", f"{_type}.json")
                with open(object_path, "r") as f:
                    object_data = json.load(f)
                arg_definitions = object_data["functions"]["__init__"]["args"]

            arguments = []
            for arg in arg_definitions:
                name = arg["name"]
                value = vars.get(name, arg["default"])
                input_type = arg.get("type")
                if input_type in ASSET_INPUT_TYPES:
                    asset_names = {
                        definition["name"]
                        for definition in get_project_asset_definitions(self.path, input_type)
                    }
                    if value not in asset_names:
                        raise ValueError(
                            f"Object {obj!r} requires a valid {input_type} asset for {name!r}; "
                            f"received {value!r}."
                        )
                    getter = {
                        "image": "get_image",
                        "font": "get_font",
                        "animation": "get_animation",
                        "tileset": "get_tileset",
                    }[input_type]
                    arguments.append(f"Assets.{getter}({value!r})")
                elif input_type == "Vector2D" and isinstance(value, (list, tuple)) and len(value) == 2:
                    arguments.append(f"Vector2D(*{value!r})")
                else:
                    arguments.append(repr(value))
            args = ", ".join(arguments)
            data += f"        self.{obj} = {_type}({args})\n"

        return data

    def createFuncs(self, data, name, i):
        for func in i["functions"]:
            if func == "__init__":
                continue
            _args_: list[str] = i["functions"][func]["args"]
            _args = []
            for _i in _args_: _args.append(_i["name"]) 
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
