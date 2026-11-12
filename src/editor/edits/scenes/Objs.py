import copy

from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import TextInput, btn
from .Inputs import _types

class ObjectsMenue(GameObj):
    def __init__(self, name: str, data: dict, sub: SubScreen):
        super().__init__(Vector2D(0, 35), visible=False, active=False)
        self.scene_name = name
        self.data = data

        self.size = Vector2D(400, sub.dim.y-35)
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)

        self.title = self.child(Text(Assets.get_font("default-35"), self.scene_name+" Scene Objects:", "white", Vector2D(10, 5), "topleft", visible=False))

        self.sub = SubScreen(self.pos.x, self.pos.y+37, self.size.x, self.size.y-37, Colors["pannel"], self._sub.screen, self._sub)
        self.PSub = sub
        self.screen = self.sub.screen

        self.objs: list[_SceneObject] = []
        self.visual_editor = None
        self.shared_props = None
        self.shared_selection_signature = ()

        self.gen()

    def gen(self):
        y = 0
        for name in self.data["objects"]:
            self.objs.append(self.child(_SceneObject(y, name, self.data["objects"][name], self.sub, self.PSub)))
            y += self.objs[-1].size.y+10

    def reload(self):
        if self.shared_props is not None:
            self.shared_props.destroy()
            self.shared_props = None
            self.shared_selection_signature = ()
        for obj in self.objs.copy():
            obj.destroy()
        self.objs.clear()
        self.gen()

    def save(self):
        for obj in self.objs: obj.save()
        if self.shared_props is not None:
            self.shared_props.save()
        self.data["objects"] = {} #"reconstruct" objects
        for obj in self.objs:
            self.data["objects"][obj.obj_name] = obj.data

    def update(self):
        for obj in self.objs: 
            obj.update()
            if obj.DEL: 
                self.objs.remove(obj)
                #remove from data
                del self.data["objects"][obj.obj_name]
                self.save()
                return True

        if self.visual_editor is not None:
            selected = self.visual_editor.selected_names
            signature = tuple(
                name for name in self.data["objects"] if name in selected
            )
            if len(signature) > 1:
                if signature != self.shared_selection_signature:
                    if self.shared_props is not None:
                        self.shared_props.destroy()
                    for obj in self.objs:
                        if obj.props is not None:
                            obj.props.save()
                            obj.props.destroy()
                            obj.props = None
                            obj.btn.pressed = False
                    shared_objects = [
                        (name, self.data["objects"][name]) for name in signature
                    ]
                    self.shared_props = self.child(
                        PropertiesPannel(
                            self.PSub,
                            "Shared",
                            shared_objects[0][1],
                            shared_objects=shared_objects,
                        )
                    )
                    self.shared_selection_signature = signature
                self.shared_props.update()
            elif self.shared_props is not None:
                self.shared_props.save()
                self.shared_props.destroy()
                self.shared_props = None
                self.shared_selection_signature = ()

        return False

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.line(self._sub.screen, "black", (5, 35), (self.size.x-5, 35))

        for obj in self.objs: obj.render()
        if self.shared_props is not None:
            self.shared_props.render()

        self.sub.render()

        self._sub.render()

class _SceneObject(GameObj):
    def __init__(self, y, name, data, sub: SubScreen, display: SubScreen):
        super().__init__(Vector2D(10, y), 0, visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 30)

        self.obj_name = name
        self.data = data

        #update self data
        if not hasattr(PySceneObjectVarDef, self.data["obj_type"]):
            with open(f"{get_save_dir_path()}/{Game.project}/objects/{self.data['obj_type']}.json", "r") as f: obj_init = json.load(f)
            for arg in obj_init["functions"]["__init__"]["args"]:
                k = arg["name"]
                v = arg["default"]
                if k not in self.data["variables"]:
                    self.data["variables"][k] = v

        self.display = display
        self.PSub = sub
        pos = sub.get_absolute_pos().to_int()
        r = pygame.Rect(pos, sub.dim.to_int())
        self.btn = btn(self.pos.x, self.pos.y, self.size.x, self.size.y, f"{self.obj_name}  |   ({self.data['obj_type']})", sub, -1, 5, Colors["bg"], True, r)
        self.child(self.btn.text)
        self.props: PropertiesPannel = None
        self.DEL = False

    def save(self):
        if self.props: self.props.save()
        

    def update(self):
        self.btn.update()
        if self.btn.pressed and not self.props:
            self.props = self.child(PropertiesPannel(self.display, self.obj_name, self.data))
        elif not self.btn.pressed and self.props:
            self.props.save()
            self.props.destroy()
            self.props = None

        if self.props: self.props.update()
        if self.props and self.props.Del.pressed:
            self.destroy()
            self.props.destroy()
            self.props = None
            self.DEL = True

        #name
        if self.props:
            name = self.props.attr[0].input.get_value()
            if name != self.obj_name:
                self.obj_name = name
                self.btn.text.set_text(f"{self.obj_name}  |   ({self.data['obj_type']})")

    def render(self):
        self.btn.render()
        if self.props: self.props.render()

class PropertiesPannel(GameObj):
    def __init__(self, sub: SubScreen, name, data, shared_objects=None):
        super().__init__(Vector2D(sub.dim.x-400, 35), visible=False, active=False)
        self.size = Vector2D(400, sub.dim.y-35)
        self.name = name
        self.type = data["obj_type"]
        self.data = data
        self.shared_objects = shared_objects or []

        self.Psub = sub
        self._sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], sub.screen, sub)

        title = (
            f"Shared Properties ({len(self.shared_objects)} objects):"
            if self.shared_objects
            else "Object Properties:"
        )
        self.title = self.child(Text(Assets.get_font("default-35"), title, "white", Vector2D(10, 5), "topleft", visible=False))

        self.sub = SubScreen(0, 37, self.size.x, self.size.y-37, Colors["pannel"], self._sub.screen, self._sub)
        self.screen = self.sub.screen
        self.open = btn(10, self.sub.dim.y-80, self.size.x-20, 30, "Open", self.sub, -1, 3, Colors["b"])
        self.Del = btn(10, self.sub.dim.y-40, self.size.x-20, 30, "Remove", self.sub, -1, 3, (255, 0, 0))
        self.search = self.child(
            TextInput(
                10,
                5,
                self.sub.dim.x - 20,
                28,
                Assets.get_font("default-25"),
                "",
                self.sub,
            )
        )

        self.attr: list[Attribute] = []

        self.gen()

    def save(self):
        if self.shared_objects:
            for attr in self.attr:
                if attr.input is None:
                    continue
                valid, value = attr.current_value()
                if not valid:
                    continue
                if not attr.changed and not attr.force_apply and value == attr.initial_value:
                    continue
                for _, object_data in self.shared_objects:
                    object_data["variables"][attr.name] = copy.deepcopy(value)
                attr.initial_value = copy.deepcopy(value)
                attr.changed = False
                attr.force_apply = False
            return

        for attr in self.attr[1:]:
            if attr.input:
                valid, value = attr.current_value()
                if not valid:
                    continue
                if attr.changed or value != attr.initial_value:
                    self.data["variables"][attr.name] = value
                    attr.initial_value = copy.deepcopy(value)
                    attr.changed = False

    def _argument_definitions(self, object_data):
        object_type = object_data["obj_type"]
        if hasattr(PySceneObjectVarDef, object_type):
            return getattr(PySceneObjectVarDef, object_type)
        path = get_save_dir_path() + f"/{Game.project}/objects/{object_type}.json"
        with open(path, "r") as f:
            definition = json.load(f)
        return definition["functions"]["__init__"]["args"]

    def gen(self):
        self.attr.clear()
        y = 40
        if not self.shared_objects:
            self.attr.append(
                self.child(Attribute(y, "Name", "str", self.name, self.sub))
            )
            y += 40
            definitions = {
                argument["name"]: argument
                for argument in self._argument_definitions(self.data)
            }
            for variable, value in self.data["variables"].items():
                argument = definitions.get(variable)
                if argument is None:
                    continue
                self.attr.append(
                    self.child(
                        Attribute(
                            y,
                            variable,
                            argument["type"],
                            value,
                            self.sub,
                            default=argument.get("default"),
                            has_default="default" in argument,
                        )
                    )
                )
                y += 40
            return

        object_definitions = [
            (
                object_data,
                {
                    argument["name"]: argument
                    for argument in self._argument_definitions(object_data)
                },
            )
            for _, object_data in self.shared_objects
        ]
        common_variables = set(self.shared_objects[0][1]["variables"])
        for _, object_data in self.shared_objects[1:]:
            common_variables.intersection_update(object_data["variables"])
        for variable in self.shared_objects[0][1]["variables"]:
            if variable not in common_variables:
                continue
            arguments = [
                definitions.get(variable)
                for _, definitions in object_definitions
            ]
            if any(argument is None for argument in arguments):
                continue
            if len({argument["type"] for argument in arguments}) != 1:
                continue
            first_argument = arguments[0]
            self.attr.append(
                self.child(
                    Attribute(
                        y,
                        variable,
                        first_argument["type"],
                        self.shared_objects[0][1]["variables"][variable],
                        self.sub,
                        default=first_argument.get("default"),
                        has_default="default" in first_argument,
                    )
                )
            )
            y += 40

    def update(self):
        self.search.update()
        query = self.search.text.text.strip().lower()
        for attr in self.attr:
            if not query or query in attr.name.lower():
                attr.update()
                if attr.input is None:
                    continue
                valid, value = attr.current_value()
                if not valid:
                    continue
                if attr.changed or attr.force_apply or value != attr.initial_value:
                    if self.shared_objects:
                        for _, object_data in self.shared_objects:
                            object_data["variables"][attr.name] = copy.deepcopy(value)
                    elif attr.name != "Name":
                        self.data["variables"][attr.name] = value
                    attr.initial_value = copy.deepcopy(value)
                    attr.changed = False
                    attr.force_apply = False
        if self.shared_objects:
            return
        self.Del.update()
        self.open.update()
        if self.open.pressed or (Keys.is_held(Keys.control) and Keys.is_pressed(Keys.tab)):
            if not hasattr(PySceneObjectVarDef, self.type): Game._tabs.open_tab(self.type, "_object_", "object")

    def render(self):
        self._sub.clear()
        self.sub.clear()

        self.title.render_to(self._sub.screen)
        pygame.draw.line(self._sub.screen, "black", (5, 35), (self.size.x-5, 35))

        self.search.render()
        if not self.search.text.text:
            search_hint = Assets.get_font("default-25").render(
                "Search properties",
                True,
                (150, 150, 150),
            )
            self.sub.screen.blit(search_hint, (15, 9))
        query = self.search.text.text.strip().lower()
        for attr in self.attr:
            if not query or query in attr.name.lower():
                attr.render()
        if not self.shared_objects:
            self.Del.render()
            self.open.render()

        self.sub.render()
        self._sub.render()

class Attribute(GameObj):
    def __init__(self, y, name, _type, value, sub, default=None, has_default=False):
        super().__init__(Vector2D(10, y), 0, visible=False, active=False)
        self.size = Vector2D(sub.dim.x-20, 30)

        self.PSub: SubScreen = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.title = self.child(Text(Assets.get_font("default-25"), name+":", "white", Vector2D(10, 5), "topleft", visible=False))

        self.name = name
        self.type = _type
        self.value = value
        self.default = copy.deepcopy(default)
        self.has_default = has_default
        self.initial_value = copy.deepcopy(value)
        self.changed = False
        self.force_apply = False
        self.input_error = False

        self.input = None
        self.input_x = self.size.x - 205
        self.input_width = 145
        if hasattr(_types, self.type):
            self.input = getattr(_types, self.type)(
                self.input_x,
                0,
                self.input_width,
                30,
                copy.deepcopy(self.value),
                self.sub,
            )
        self.reset = (
            btn(self.size.x - 55, 0, 50, 30, "Reset", self.sub, -1, 2, Colors["bg"])
            if self.has_default
            else None
        )

    def update(self):
        if self.input: self.input.update()
        if self.reset is not None:
            self.reset.update()
            if self.reset.pressed:
                self.input = getattr(_types, self.type)(
                    self.input_x,
                    0,
                    self.input_width,
                    30,
                    copy.deepcopy(self.default),
                    self.sub,
                )
                if hasattr(self.input, "value"):
                    self.input.value = copy.deepcopy(self.default)
                self.force_apply = True
        if self.input:
            valid, value = self.current_value()
            self.changed = valid and (
                self.force_apply or value != self.initial_value
            )

    def current_value(self):
        try:
            value = copy.deepcopy(self.input.get_value())
            self.input_error = False
            return True, value
        except (TypeError, ValueError):
            self.input_error = True
            return False, None

    def render(self):
        self.sub.clear()

        self.title.render_to(self.screen)
        if self.input: self.input.render()
        if self.reset is not None: self.reset.render()
        if self.input_error:
            pygame.draw.rect(
                self.screen,
                (255, 100, 100),
                pygame.Rect(self.input_x, 0, self.input_width, 30),
                1,
            )

        self.sub.render()
