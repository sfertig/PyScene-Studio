from PyScene import *
import pygame
import json
import os

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput, _types

from .LeftPannel import Item
from..scenes.Objs import Attribute as _attr

#This file contains both functions and import manager

def remove_scene_object_argument(project, object_type, argument_name):
    tabs = getattr(getattr(Game, "_tabs", None), "tabs", [])
    for tab in tabs:
        scene_editor = getattr(tab, "obj", None)
        scene_data = getattr(scene_editor, "data", None)
        if not isinstance(scene_data, dict):
            continue

        changed = False
        for scene_object in scene_data.get("objects", {}).values():
            if scene_object.get("obj_type") != object_type:
                continue

            variables = scene_object.get("variables", {})
            if argument_name in variables:
                del variables[argument_name]
                changed = True

            objects_menu = getattr(scene_editor, "objs", None)
            for scene_object_editor in getattr(objects_menu, "objs", []):
                if scene_object_editor.data is not scene_object:
                    continue
                properties = scene_object_editor.props
                if properties is None:
                    continue
                removed_attributes = [
                    attr for attr in properties.attr if attr.name == argument_name
                ]
                properties.attr = [
                    attr for attr in properties.attr if attr.name != argument_name
                ]
                for attr in removed_attributes:
                    attr.destroy()

        if changed:
            scene_editor.save()

    scenes_path = os.path.join(get_save_dir_path(), project, "scenes")
    for filename in os.listdir(scenes_path):
        if not filename.endswith(".json"):
            continue

        scene_path = os.path.join(scenes_path, filename)
        with open(scene_path, "r") as f:
            scene_data = json.load(f)

        changed = False
        for scene_object in scene_data.get("objects", {}).values():
            if scene_object.get("obj_type") == object_type:
                variables = scene_object.get("variables", {})
                if argument_name in variables:
                    del variables[argument_name]
                    changed = True

        if changed:
            with open(scene_path, "w") as f:
                json.dump(scene_data, f, indent=4)


class RightPannel(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(sub.dim.x-400, 0), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.attr = self.child(Attributes(self.sub, data))
        self.args = self.child(Arguments(self.sub, data))

        self.OPEN = None

    def update(self):
        self.attr.update()
        self.args.update()

    def render(self):
        self.sub.clear()

        self.attr.render()
        self.args.render()

        self.sub.render()


class Attributes(GameObj):
    def __init__(self, sub: SubScreen, data):
        super().__init__(Vector2D(0, sub.dim.y//2+5), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y//2-5)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)
        self.sub = SubScreen(5, 40, self.size.x-10, self.size.y-50, Colors["bg"], self._sub.screen, self._sub)
        self.data = data

        self.title = self.child(Text(Assets.get_font("default-35"), "Object Attributes:", "white", Vector2D(self.size.x//2, 20), visible=False))
        i = data["variables"]
        self.attrs: list[_attr] = [
            _attr(10, "pos", "Vector2D", i["pos"], self.sub),
            _attr(50, "z_index", "int", i["z_index"], self.sub),
            _attr(90, "active", "bool", i["active"], self.sub),
            _attr(130, "visible", "bool", i["visible"], self.sub),
            _attr(170, "Global", "bool", i["Global"], self.sub),
        ]

    def save(self):
        for attr in self.attrs:
            if attr.input: self.data["variables"][attr.name] = attr.input.get_value()

    def update(self):
        for attr in self.attrs:
            attr.update()

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)

        for attr in self.attrs:
            attr.render()

        self.sub.render()
        self._sub.render()

class Arguments(GameObj):
    def __init__(
        self,
        sub: SubScreen,
        data,
        pos: Vector2D | None = None,
        height: int | None = None,
    ):
        position = pos if pos is not None else Vector2D(0, 0)
        super().__init__(position, visible=False, active=False)
        panel_height = height if height is not None else sub.dim.y//2-5
        self.size = Vector2D(400, panel_height)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)
        self.sub = SubScreen(5, 40, self.size.x-10, self.size.y-50, Colors["pannel"], self._sub.screen, self._sub)
        self.show_sub = SubScreen(5, 50, self.size.x-10, self.size.y-60, Colors["bg"], self.sub.screen, self.sub)
        self.data = data
        self.func = "__init__"

        self._type = TypesBox(265, 5, 150, 40, self.sub)
        self.input = self.child(StrInput(5, 5, 200, 40, "", self.sub))
        self.input_rect = pygame.Rect((3, 3), (203, 43))
        self.add_btn = btn(215, 5, 40, 40, "+", self.sub, -1, 5, Colors["b"])

        self.title = self.child(Text(Assets.get_font("default-35"), "Func Args:", "white", Vector2D(self.size.x//2, 20), visible=False))

        self.items: list[Item] = []
        self.gen()

    def gen(self):
        self.items.clear()
        y = 5
        for attr in self.data["functions"][self.func]["args"]:
            name = f"{attr['name']} ({attr['type']})"
            self.items.append(self.child(Item(y, name, self.show_sub, False)))
            self.items[-1]._name = attr["name"]
            y += self.items[-1].size.y+10

    def set_func(self, func):
        self.func = func
        self.gen()

    def save(self):
        pass

    def persist_argument_removal(self, argument_name):
        object_type = self.data["name"]
        remove_scene_object_argument(Game.project, object_type, argument_name)

        tabs = getattr(getattr(Game, "_tabs", None), "tabs", [])
        for tab in tabs:
            object_editor = getattr(tab, "obj", None)
            if getattr(object_editor, "data", None) is self.data:
                object_editor.save()
                return

        object_path = os.path.join(
            get_save_dir_path(),
            Game.project,
            "objects",
            f"{object_type}.json",
        )
        with open(object_path, "w") as f:
            json.dump(self.data, f, indent=4)

    def update(self):
        self.input.update()
        self.add_btn.update()
        self._type.update()

        for item in self.items:
            item.update()
            if item.Del.hovered and Keys.is_pressed(Keys.enter):
                index = None
                for i in range(len(self.data["functions"][self.func]["args"])):
                    if self.data["functions"][self.func]["args"][i]["name"] == item._name:
                        index = i
                        break
                if index == None: return
                removed_arg = self.data["functions"][self.func]["args"].pop(index)
                if self.func == "__init__":
                    self.persist_argument_removal(removed_arg["name"])
                self.gen()

        if self.add_btn.pressed:
            text = self.input.get_value()
            for attr in self.data["functions"][self.func]["args"]:
                if attr["name"] == text: return
            self.data["functions"][self.func]["args"].append({"name": text, "type": self._type._value, "default": self.get_default(self._type._value)})
            self.gen()
            self.input = self.child(StrInput(5, 5, 200, 40, "", self.sub))

    def get_default(self, _type):
        if _type == "int": return 0
        elif _type == "float": return 0.0
        elif _type == "str": return ""
        elif _type == "bool": return True
        elif _type == "color": return [0, 0, 0]
        elif _type == "Vector2D": return [0, 0]
        elif _type == "screen": return None
        return None

    def render(self):
        self._sub.clear()
        self.sub.clear()
        self.show_sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.rect(self.sub.screen, Colors["bg"], self.input_rect)
        self.input.render()
        self.add_btn.render()
        self._type.render()

        for item in self.items:
            item.render()

        self.show_sub.render()
        self.sub.render()
        self._sub.render()

class TypesBox(GameObj):
    def __init__(self, x, y, w, h, sub: SubScreen):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        self.PSub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.rect = pygame.Rect((0, 0), self.size.to_int())

        self.value = self.child(Text(Assets.get_font("default-25"), "int", "white", Vector2D(self.size.x//2, self.size.y//2), visible=False))
        self._value = "int"
        self.types = []
        for var in vars(_types):
            self.types.append(var)
        print(self.types)
        self.index = self.types.index(self._value)

    def update(self):
        mpos = self._sub.local_mouse_pos().to_int()
        if not self.rect.collidepoint(mpos): return
        change = 0
        for event in Game.events:
            if event.type == pygame.MOUSEWHEEL: change = event.y
        if change != 0:
            self.index = (self.index + change) % len(self.types)
            self._value = self.types[self.index]
            self.value.set_text(self._value)

    def render(self):
        self._sub.clear()

        self.value.render_to(self._sub.screen)

        self._sub.render()
        
