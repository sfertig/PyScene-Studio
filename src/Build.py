from PyScene import *
import os
import json
import math
import shutil

from src.utils.files import *

class Build:
    def __init__(self, project_name, project_path=None, web=False, is_export=False):
        self.name = project_name #the project that is getting built
        self.path = project_path or os.path.join(get_save_dir_path(), self.name)
        self.web = web
        self.is_export = is_export
        print("[Build] - Building project: "+self.name)

        self.project = json.load(open(self.path+"/project.json", "r")) #project details

        ensure_project_tilemaps_dir(self.path)
        self.gen_assets()
        self.gen_main()
        print("[Build] - Project File Built: "+self.name)

        #loop over all files in scenes
        for file in os.listdir(self.path+"/scenes/"):
            if file.endswith(".json"):
                self._build_source_file("scenes", file, self.gen_scene)
        #gen objects
        for file in os.listdir(self.path+"/objects/"):
            if file.endswith(".json"):
                self._build_source_file("objects", file, self.gen_object)
        print("[Build] - Project Built Successfully: "+self.name)

    def _build_source_file(self, source_dir, filename, generator):
        name = filename[:-5]
        source_path = os.path.join(self.path, source_dir, filename)
        output_path = os.path.join(self.path, "_python", "data", f"{name}.py")
        with open(source_path, "r") as f:
            source_data = json.load(f)

        if source_data.get("dirty") is False and os.path.isfile(output_path):
            print(f"[Build] - {source_dir[:-1].capitalize()} File Skipped: {name}")
            return

        generator(name)
        source_data["dirty"] = False
        save_source_json(source_data, source_path)
        print(f"[Build] - {source_dir[:-1].capitalize()} File Built: {name}")

    def gen_main(self):
        p = self.path+"/_python/main.py"
        i = self.project["window"]
        exists(p)
        include_splashscreen = (
            self.is_export and self.project.get("include_splashscreen", False)
        )
        data = [
            "from PyScene import *",
            "from load_assets import load_assets",
            f"Game.init({i['width']!r}, {i['height']!r}, {i['title']!r}, "
            f"{i['bg_color']!r}, {i['fps']!r}, {i['fullscreen']!r}, True)",
            "load_assets()",
            "from data.main import main",
        ]
        splash_path = os.path.join(self.path, "_python", "splash.py")
        if include_splashscreen:
            splash_source = os.path.join(os.path.dirname(__file__), "utils", "splash.py")
            shutil.copy2(splash_source, splash_path)
            data.extend(["from splash import Splash", "_splash = Splash()"])
        elif os.path.isfile(splash_path):
            os.remove(splash_path)

        if self.web:
            data = [
                "import asyncio",
                "import pygame",
                *data,
                *(["main()"] if not include_splashscreen else []),
                "",
                "class _WebClock:",
                "    def tick(self, fps):",
                "        return 1000 / max(fps, 1)",
                "",
                "def _web_quit(_quit_program=True):",
                "    Game._game__on = False",
                "    pygame.quit()",
                "",
                "Game.clock = _WebClock()",
                "Game.quit = _web_quit",
                "",
                "async def _run_game():",
                *(
                    [
                        "    while not _splash.done and Game._game__on:",
                        "        Game.Tick()",
                        "        await asyncio.sleep(1 / max(Game.fps, 1))",
                        "    if Game._game__on:",
                        "        Game.bg = _splash.bg",
                        "        main()",
                    ]
                    if include_splashscreen
                    else []
                ),
                "    while Game._game__on:",
                "        Game.Tick()",
                "        await asyncio.sleep(1 / max(Game.fps, 1))",
                "",
                "asyncio.run(_run_game())",
            ]
        else:
            if include_splashscreen:
                data.extend(
                    [
                        "while not _splash.done:",
                        "    Game.Tick()",
                        "Game.bg = _splash.bg",
                    ]
                )
            data.append("main()")
            data.append("Game.Run()")
        with open(p, "w") as f:
            f.write("\n".join(data) + "\n")

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

            kind = definition["type"]
            options = definition.get("options", {})
            system_default_font = kind == "font" and definition.get("source") == "system_default"
            if system_default_font:
                path_expression = "None"
            else:
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

            if kind == "image":
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
                lines.append(f"    Assets.new_font({name!r}, {path_expression}, {options['size']!r})")
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
            custom_object = arg_definitions is None
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
            editor_scale = vars.get("editor_scale", 1.0)
            if editor_scale != 1.0:
                if (
                    not isinstance(editor_scale, (int, float))
                    or isinstance(editor_scale, bool)
                    or not math.isfinite(editor_scale)
                    or editor_scale <= 0
                ):
                    raise ValueError(
                        f"Object {obj!r} has an invalid editor scale: {editor_scale!r}."
                    )
                data += (
                    f"        if isinstance(getattr(self.{obj}, 'image', None), pygame.Surface):\n"
                    f"            self.{obj}.image = pygame.transform.scale_by("
                    f"self.{obj}.image, {editor_scale!r})\n"
                )
            if custom_object:
                position = vars.get(
                    "pos",
                    object_data.get("variables", {}).get("pos", [0, 0]),
                )
                if (
                    isinstance(position, (list, tuple))
                    and len(position) >= 2
                    and all(
                        isinstance(value, (int, float)) and not isinstance(value, bool)
                        for value in position[:2]
                    )
                ):
                    data += f"        self.{obj}.pos = Vector2D(*{list(position[:2])!r})\n"

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
