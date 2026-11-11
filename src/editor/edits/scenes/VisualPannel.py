from PyScene import *
import PyScene
import pygame
import json
import math
import os
from PyScene.utils.Assets import load_tileset

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

class VisualEditor(GameObj):
    def __init__(self, rect, sub: SubScreen, data):
        super().__init__(Vector2D(rect.x, rect.y), visible=False, active=False)
        self.PSub = sub
        self.rect = rect
        self.data = data
        self.GridSize = 32
        self.zoom = 1.0
        self.min_zoom = 0.25
        self.max_zoom = 4.0
        self.dragging = False
        self.drag_remainder = [0.0, 0.0]
        self.game_size = Vector2D(0, 0)
        self.preview_objects = []
        self.preview_render_methods = {}
        self.preview_surface = None
        self.preview_surface_size = None
        self.preview_variables = {}
        self.preview_object_names = {}
        self.preview_original_images = {}
        self.preview_signature = None
        self.preview_custom_definitions = {}
        self.preview_asset_definitions = []
        self.preview_asset_cache = {}
        self.dragged_object = None
        self.dragged_variables = None
        self.drag_mode = None
        self.drag_changed = False
        self.drag_total = [0.0, 0.0]
        self.drag_applied = [0.0, 0.0]
        self.drag_anchor = [0.0, 0.0]
        self.drag_start_size = None
        self.drag_start_scale = 1.0
        self.selected_name = None
        self.tool = "Move"
        self.snap_enabled = True
        self.grid_visible = True
        self.needs_save = False
        self.grid_sizes = (8, 16, 32, 64)
        self.grid_index = self.grid_sizes.index(self.GridSize)
        self.grid_dropdown_open = False
        self.axis_font = pygame.font.Font(None, 18)
        self.toolbar_font = pygame.font.Font(None, 20)
        self.toolbar_rects = {}

        #load game bg
        with open(get_save_dir_path()+f"/{Game.project}/project.json", "r") as f:
            game_data: dict = json.load(f)

        self.game_size = Vector2D(game_data["window"]["width"], game_data["window"]["height"])
        self.sub = SubScreen(rect.x, rect.y, rect.width, rect.height, game_data["window"]["bg_color"], sub.screen, sub)
        self._layout_toolbar()

    def _layout_toolbar(self):
        x = 8
        y = 8
        for label, width in (
            ("Move", 52),
            ("Scale", 52),
            ("Snap", 64),
            ("Lines", 62),
            ("Grid", 76),
        ):
            self.toolbar_rects[label] = pygame.Rect(x, y, width, 26)
            x += width + 4

    def _handle_toolbar_click(self, position):
        for label, rect in self.toolbar_rects.items():
            if not rect.collidepoint(position):
                continue
            if label in ("Move", "Scale"):
                self.tool = label
            elif label == "Snap":
                self.snap_enabled = not self.snap_enabled
            elif label == "Lines":
                self.grid_visible = not self.grid_visible
            else:
                self.grid_dropdown_open = not self.grid_dropdown_open
            return True
        return False

    def _grid_dropdown_rect(self):
        button_rect = self.toolbar_rects["Grid"]
        return pygame.Rect(
            button_rect.x,
            button_rect.bottom,
            button_rect.width,
            len(self.grid_sizes) * 24,
        )

    def _handle_grid_dropdown_click(self, position):
        if not self.grid_dropdown_open:
            return False
        dropdown_rect = self._grid_dropdown_rect()
        if dropdown_rect.collidepoint(position):
            option_index = (position[1] - dropdown_rect.y) // 24
            self.grid_index = option_index
            self.GridSize = self.grid_sizes[option_index]
            self.grid_dropdown_open = False
            return True
        self.grid_dropdown_open = False
        return False

    def _object_name(self, obj):
        return self.preview_object_names.get(id(obj))

    def _selected_object(self):
        for obj in self.preview_objects:
            if self._object_name(obj) == self.selected_name:
                return obj, self.preview_variables.get(id(obj))
        return None, None

    def _object_bounds(self, obj, variables):
        rect = getattr(obj, "rect", None)
        if isinstance(rect, pygame.Rect):
            return rect.copy()

        pos = getattr(obj, "pos", None)
        if not isinstance(pos, Vector2D):
            position = variables.get("pos")
            if (
                isinstance(position, (list, tuple))
                and len(position) >= 2
                and all(self._is_position_number(value) for value in position[:2])
            ):
                pos = Vector2D(*position[:2])
            elif all(self._is_position_number(variables.get(axis)) for axis in ("x", "y")):
                pos = Vector2D(variables["x"], variables["y"])
            elif all(self._is_position_number(variables.get(axis)) for axis in ("x1", "y1")):
                pos = Vector2D(variables["x1"], variables["y1"])

        if all(self._is_position_number(variables.get(axis)) for axis in ("x2", "y2")):
            x1 = variables.get("x1", pos.x if isinstance(pos, Vector2D) else 0)
            y1 = variables.get("y1", pos.y if isinstance(pos, Vector2D) else 0)
            return pygame.Rect(
                round(min(x1, variables["x2"])),
                round(min(y1, variables["y2"])),
                max(1, round(abs(variables["x2"] - x1))),
                max(1, round(abs(variables["y2"] - y1))),
            )

        if not isinstance(pos, Vector2D):
            return None

        if self._is_position_number(variables.get("r")):
            radius = max(1, int(variables["r"]))
            return pygame.Rect(pos.x - radius, pos.y - radius, radius * 2, radius * 2)

        image = getattr(obj, "image", None)
        if isinstance(image, pygame.Surface):
            return pygame.Rect(pos.to_int(), image.get_size())

        size = getattr(obj, "dim", None)
        if isinstance(size, Vector2D):
            return pygame.Rect(pos.to_int(), size.to_int())

        if all(self._is_position_number(variables.get(axis)) for axis in ("w", "h")):
            return pygame.Rect(pos.to_int(), (max(1, variables["w"]), max(1, variables["h"])))
        return pygame.Rect(pos.to_int(), (16, 16))

    def _scale_kind(self, obj, variables):
        if all(self._is_position_number(variables.get(key)) for key in ("w", "h")):
            return "rect"
        if self._is_position_number(variables.get("r")):
            return "circle"
        if (
            isinstance(getattr(obj, "image", None), pygame.Surface)
            and not isinstance(obj, PyScene.Animation)
        ):
            return "image"
        return None

    def _selection_handle_rect(self):
        obj, variables = self._selected_object()
        if obj is None or variables is None or self._scale_kind(obj, variables) is None:
            return None
        bounds = self._object_bounds(obj, variables)
        if bounds is None:
            return None
        scale_x, scale_y = self._view_scale()
        right = (bounds.right - Game.cam.pos.x) * scale_x
        bottom = (bounds.bottom - Game.cam.pos.y) * scale_y
        return pygame.Rect(round(right - 5), round(bottom - 5), 10, 10)

    def _drag_anchor(self, variables):
        position = variables.get("pos")
        if (
            isinstance(position, (list, tuple))
            and len(position) >= 2
            and all(self._is_position_number(value) for value in position[:2])
        ):
            return [float(position[0]), float(position[1])]
        for x_key, y_key in (("x", "y"), ("x1", "y1")):
            if all(self._is_position_number(variables.get(key)) for key in (x_key, y_key)):
                return [float(variables[x_key]), float(variables[y_key])]
        return [0.0, 0.0]

    def _apply_move_drag(self, dx, dy):
        self.drag_total[0] += dx
        self.drag_total[1] += dy
        target = list(self.drag_total)
        if self.snap_enabled:
            target = [
                round((self.drag_anchor[axis] + target[axis]) / self.GridSize) * self.GridSize
                - self.drag_anchor[axis]
                for axis in (0, 1)
            ]
        delta = [target[0] - self.drag_applied[0], target[1] - self.drag_applied[1]]
        if delta != [0, 0]:
            self._move_object(
                self.dragged_object,
                self.dragged_variables,
                delta[0],
                delta[1],
            )
            self.drag_applied = target
            self.drag_changed = True

    def _start_scale_drag(self, obj, variables):
        self.drag_mode = "scale"
        self.dragged_object = obj
        self.dragged_variables = variables
        self.drag_total = [0.0, 0.0]
        self.drag_anchor = self._drag_anchor(variables)
        self.drag_start_size = None
        if self._scale_kind(obj, variables) == "rect":
            self.drag_start_size = (variables["w"], variables["h"])
        elif self._scale_kind(obj, variables) == "circle":
            self.drag_start_size = variables["r"]
        else:
            self.drag_start_scale = variables.get("editor_scale", 1.0)
            if (
                not self._is_position_number(self.drag_start_scale)
                or not math.isfinite(self.drag_start_scale)
                or self.drag_start_scale <= 0
            ):
                raise ValueError(
                    f"Object {self._object_name(obj)!r} has an invalid editor scale."
                )
        self.drag_changed = False

    def _apply_scale_drag(self, dx, dy):
        self.drag_total[0] += dx
        self.drag_total[1] += dy
        kind = self._scale_kind(self.dragged_object, self.dragged_variables)
        variables = self.dragged_variables
        if kind == "rect":
            start_w, start_h = self.drag_start_size
            width = start_w + self.drag_total[0]
            height = start_h + self.drag_total[1]
            if self.snap_enabled:
                width = round(
                    (self.drag_anchor[0] + width) / self.GridSize
                ) * self.GridSize - self.drag_anchor[0]
                height = round(
                    (self.drag_anchor[1] + height) / self.GridSize
                ) * self.GridSize - self.drag_anchor[1]
            width = max(1, round(width))
            height = max(1, round(height))
            changed = width != variables["w"] or height != variables["h"]
            variables["w"], variables["h"] = width, height
            if hasattr(self.dragged_object, "w"):
                self.dragged_object.w = width
            if hasattr(self.dragged_object, "h"):
                self.dragged_object.h = height
            if hasattr(self.dragged_object, "dim"):
                self.dragged_object.dim = Vector2D(width, height)
            rect = getattr(self.dragged_object, "rect", None)
            if isinstance(rect, pygame.Rect):
                rect.size = (width, height)
        elif kind == "circle":
            radius = self.drag_start_size + (self.drag_total[0] + self.drag_total[1]) / 2
            if self.snap_enabled:
                radius = (
                    round((self.drag_anchor[0] + radius) / self.GridSize)
                    * self.GridSize
                    - self.drag_anchor[0]
                )
            radius = max(1, round(radius))
            changed = radius != variables["r"]
            variables["r"] = radius
            self.dragged_object.radius = radius
        elif kind == "image":
            original = self.preview_original_images[id(self.dragged_object)]
            width = max(1, original.get_width())
            scaled_width = width * self.drag_start_scale + self.drag_total[0]
            if self.snap_enabled:
                scaled_width = (
                    round((self.drag_anchor[0] + scaled_width) / self.GridSize)
                    * self.GridSize
                    - self.drag_anchor[0]
                )
            scale = max(0.1, scaled_width / width)
            changed = scale != variables.get("editor_scale", 1.0)
            variables["editor_scale"] = scale
            self.dragged_object.image = pygame.transform.scale_by(original, scale)
        else:
            return
        if changed:
            self.drag_changed = True
            self.preview_signature = json.dumps(
                {
                    "objects": self.data["objects"],
                    "custom_objects": self.preview_custom_definitions,
                    "assets": self.preview_asset_definitions,
                },
                sort_keys=True,
            )

    def _load_preview_asset(self, input_type, name):
        cache_key = (input_type, name)
        if cache_key in self.preview_asset_cache:
            return self.preview_asset_cache[cache_key]

        definition_type = ASSET_INPUT_TYPES[input_type]
        definition = next(
            (
                item for item in self.preview_asset_definitions
                if item.get("type") == definition_type and item.get("name") == name
            ),
            None,
        )
        if definition is None:
            raise ValueError(f"Missing {input_type} asset definition: {name!r}")

        project_path = os.path.join(get_save_dir_path(), Game.project)
        assets_path = ensure_project_assets_dir(project_path)
        options = definition.get("options", {})
        system_default_font = input_type == "font" and definition.get("source") == "system_default"
        if system_default_font:
            asset_path = None
        else:
            asset_path = os.path.abspath(
                os.path.join(assets_path, definition["file"].replace("/", os.sep))
            )
            assets_root = os.path.abspath(assets_path)
            try:
                contained = os.path.commonpath((assets_root, asset_path)) == assets_root
            except ValueError:
                contained = False
            if not contained:
                raise ValueError(f"Asset path escapes the assets directory: {definition['file']!r}")

        if input_type == "image":
            asset = pygame.image.load(asset_path)
            if options.get("rect") is not None:
                asset = asset.subsurface(options["rect"])
            if options.get("scale", 1.0) != 1.0:
                asset = pygame.transform.scale_by(asset, options["scale"])
            asset = asset.convert()
        elif input_type == "font":
            asset = pygame.font.Font(None if system_default_font else asset_path, options["size"])
        elif input_type == "tileset":
            asset = pygame.image.load(asset_path).convert_alpha()
            scale = options.get("scale", 1.0)
            if scale != 1.0:
                asset = pygame.transform.scale(
                    asset,
                    (int(asset.get_width() * scale), int(asset.get_height() * scale)),
                )
            asset, _ = load_tileset(
                asset,
                options.get("width", 16) * scale,
                options.get("height", 16) * scale,
            )
        elif input_type == "animation":
            image = pygame.image.load(asset_path).convert()
            asset = Animation(
                image,
                size=options.get("frame_size", 16),
                fps=options.get("fps", 3),
                loop=options.get("loop", True),
                Global=True,
            )
        else:
            raise ValueError(f"Unsupported asset input type: {input_type!r}")

        self.preview_asset_cache[cache_key] = asset
        return asset

    def _preview_argument(self, arg, value):
        input_type = arg.get("type")
        if input_type in ASSET_INPUT_TYPES:
            return self._load_preview_asset(input_type, value)
        if input_type == "Vector2D" and isinstance(value, (list, tuple)) and len(value) == 2:
            return Vector2D(*value)
        return value

    def _has_preview_assets(self, arg_definitions, variables):
        for arg in arg_definitions:
            input_type = arg.get("type")
            if input_type not in ASSET_INPUT_TYPES:
                continue
            name = variables.get(arg["name"], arg["default"])
            if not name or not any(
                definition.get("type") == ASSET_INPUT_TYPES[input_type]
                and definition.get("name") == name
                for definition in self.preview_asset_definitions
            ):
                return False
        return True

    def _instantiate_preview_object(self, obj_class, obj_type, obj_args):
        if obj_type != "Tilemap":
            return obj_class(*obj_args)

        project_path = os.path.join(get_save_dir_path(), Game.project)
        python_path = os.path.join(project_path, "_python")
        ensure_project_tilemaps_dir(project_path)
        previous_cwd = os.getcwd()
        try:
            os.chdir(python_path)
            return obj_class(*obj_args)
        finally:
            os.chdir(previous_cwd)

    def center_camera(self):
        view_width, view_height = self._world_view_size()
        Game.cam.pos = Vector2D(
            (self.game_size.x - view_width) / 2,
            (self.game_size.y - view_height) / 2,
        )

    def _world_view_size(self):
        return (
            max(1, math.ceil(self.sub.dim.x / self.zoom)),
            max(1, math.ceil(self.sub.dim.y / self.zoom)),
        )

    def _view_scale(self):
        view_width, view_height = self._world_view_size()
        return self.sub.dim.x / view_width, self.sub.dim.y / view_height

    def _zoom_at(self, mouse_pos, wheel_steps):
        old_scale_x, old_scale_y = self._view_scale()
        world_x = Game.cam.pos.x + mouse_pos.x / old_scale_x
        world_y = Game.cam.pos.y + mouse_pos.y / old_scale_y
        self.zoom = max(
            self.min_zoom,
            min(self.max_zoom, self.zoom * (1.1 ** wheel_steps)),
        )
        new_scale_x, new_scale_y = self._view_scale()
        Game.cam.pos = Vector2D(
            world_x - mouse_pos.x / new_scale_x,
            world_y - mouse_pos.y / new_scale_y,
        )

    def refresh_preview_objects(self):
        custom_definitions = {}
        for object_data in self.data["objects"].values():
            obj_type = object_data["obj_type"]
            if hasattr(PyScene, obj_type):
                continue
            object_path = os.path.join(
                get_save_dir_path(),
                Game.project,
                "objects",
                f"{obj_type}.json",
            )
            with open(object_path, "r") as f:
                custom_definitions[obj_type] = json.load(f)

        project_path = os.path.join(get_save_dir_path(), Game.project)
        assets_path = ensure_project_assets_dir(project_path)
        manifest_path = os.path.join(assets_path, "manifest.json")
        if os.path.isfile(manifest_path):
            with open(manifest_path, "r") as f:
                asset_manifest = json.load(f)
        else:
            asset_manifest = {"definitions": []}
        asset_definitions = asset_manifest.get("definitions", [])

        for object_data in self.data["objects"].values():
            definition = custom_definitions.get(object_data["obj_type"])
            if definition is None:
                continue
            variables = object_data["variables"]
            position = definition.get("variables", {}).get("pos")
            if (
                "pos" not in variables
                and isinstance(position, (list, tuple))
                and len(position) >= 2
                and all(self._is_position_number(value) for value in position[:2])
            ):
                variables["pos"] = list(position[:2])

        signature = json.dumps(
            {
                "objects": self.data["objects"],
                "custom_objects": custom_definitions,
                "assets": asset_definitions,
            },
            sort_keys=True,
        )
        if signature == self.preview_signature:
            return

        self.preview_objects = []
        self.preview_render_methods = {}
        self.preview_variables = {}
        self.preview_object_names = {}
        self.preview_original_images = {}
        self.preview_asset_definitions = asset_definitions
        self.preview_asset_cache = {}
        queue_length = len(Game.queue_creation)
        game_id = Game.id
        always_global = Game.always_global
        Game.always_global = True
        try:
            for object_name, object_data in self.data["objects"].items():
                obj_type = object_data["obj_type"]
                obj_class = getattr(PyScene, obj_type, None)
                render_method = "render_to"
                variables = object_data["variables"]
                if obj_class is not None:
                    if not callable(getattr(obj_class, "render_to", None)) and obj_type != "Tilemap":
                        continue
                    arg_definitions = getattr(PySceneObjectVarDef, obj_type)
                    if not self._has_preview_assets(arg_definitions, variables):
                        continue
                    obj_args = [
                        self._preview_argument(
                            arg,
                            variables.get(arg["name"], arg["default"]),
                        )
                        for arg in arg_definitions
                    ]
                    obj = self._instantiate_preview_object(obj_class, obj_type, obj_args)
                else:
                    obj_definition = custom_definitions[obj_type]
                    functions = obj_definition["functions"]
                    render_to = functions.get("render_to")
                    render = functions.get("render")
                    if render_to is not None and len(render_to["args"]) == 1:
                        render_method = "render_to"
                    elif render is not None and not render["args"]:
                        render_method = "render"
                    else:
                        continue

                    namespace = {"__name__": f"{obj_type}_preview"}
                    source = "from PyScene import *\nimport pygame\n"
                    source += "".join(f"{line}\n" for line in obj_definition["imports"])
                    source += f"\nclass {obj_type}(GameObj):\n"

                    init_args = functions["__init__"]["args"]
                    scene_variables = variables
                    if not self._has_preview_assets(init_args, scene_variables):
                        continue
                    arg_names = [arg["name"] for arg in init_args]
                    source += f"    def __init__(self{', ' if arg_names else ''}{', '.join(arg_names)}):\n"
                    definition_variables = obj_definition.get("variables", {})
                    position = definition_variables.get("pos", [0, 0])
                    source += (
                        "        super().__init__(Vector2D("
                        f"{position[0]!r}, {position[1]!r}), "
                        f"{definition_variables.get('z_index', 0)!r}, "
                        f"{definition_variables.get('active', True)!r}, "
                        f"{definition_variables.get('visible', True)!r}, "
                        f"{definition_variables.get('Global', False)!r})\n"
                    )
                    init_code = functions["__init__"]["code"] or ["pass"]
                    source += "".join(f"        {line}\n" for line in init_code)

                    for function_name, function in functions.items():
                        if function_name == "__init__":
                            continue
                        function_args = [arg["name"] for arg in function["args"]]
                        source += (
                            f"    def {function_name}(self"
                            f"{', ' if function_args else ''}{', '.join(function_args)}):\n"
                        )
                        function_code = function["code"] or ["pass"]
                        source += "".join(f"        {line}\n" for line in function_code)

                    exec(compile(source, object_path, "exec"), namespace)
                    obj_class = namespace[obj_type]
                    obj_args = [
                        self._preview_argument(
                            arg,
                            scene_variables.get(arg["name"], arg["default"]),
                        )
                        for arg in init_args
                    ]
                    obj = self._instantiate_preview_object(obj_class, obj_type, obj_args)
                    position = scene_variables.get(
                        "pos",
                        definition_variables.get("pos"),
                    )
                    if (
                        isinstance(position, (list, tuple))
                        and len(position) >= 2
                        and all(self._is_position_number(value) for value in position[:2])
                    ):
                        obj.pos = Vector2D(*position[:2])

                if (
                    callable(getattr(obj, "render_to", None))
                    or obj_type == "Tilemap"
                    or render_method == "render"
                ):
                    image = getattr(obj, "image", None)
                    if (
                        isinstance(image, pygame.Surface)
                        and not isinstance(obj, PyScene.Animation)
                    ):
                        self.preview_original_images[id(obj)] = image.copy()
                        scale = variables.get("editor_scale", 1.0)
                        if self._is_position_number(scale) and scale > 0 and scale != 1.0:
                            obj.image = pygame.transform.scale_by(image, scale)
                    self.preview_objects.append(obj)
                    self.preview_render_methods[id(obj)] = render_method
                    self.preview_variables[id(obj)] = object_data["variables"]
                    self.preview_object_names[id(obj)] = object_name
        finally:
            del Game.queue_creation[queue_length:]
            Game.id = game_id
            Game.always_global = always_global

        self.preview_objects.sort(key=lambda obj: getattr(obj, "z_index", 0))
        self.preview_custom_definitions = custom_definitions
        self.preview_signature = signature
        if self.selected_name not in self.data["objects"]:
            self.selected_name = None

    @staticmethod
    def _is_position_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    def _has_position(self, variables):
        position = variables.get("pos")
        has_pos = (
            isinstance(position, (list, tuple))
            and len(position) >= 2
            and all(self._is_position_number(value) for value in position[:2])
        )
        has_axis = any(
            axis in variables and self._is_position_number(variables[axis])
            for axis in ("x", "y", "x1", "y1", "x2", "y2")
        )
        return has_pos or has_axis

    def _preview_object_hit(self, obj, variables, point):
        rect = getattr(obj, "rect", None)
        if isinstance(rect, pygame.Rect):
            return rect.collidepoint(point.to_int())

        pos = getattr(obj, "pos", None)
        if not isinstance(pos, Vector2D) and all(
            self._is_position_number(variables.get(axis))
            for axis in ("x1", "y1")
        ):
            pos = Vector2D(variables["x1"], variables["y1"])
        if isinstance(pos, Vector2D) and (
            self._is_position_number(variables.get("x"))
            or self._is_position_number(variables.get("y"))
        ):
            pos = Vector2D(
                variables.get("x", pos.x),
                variables.get("y", pos.y),
            )
        end = getattr(obj, "end", None)
        if not isinstance(end, Vector2D) and all(
            self._is_position_number(variables.get(axis))
            for axis in ("x2", "y2")
        ):
            end = Vector2D(variables["x2"], variables["y2"])
        if isinstance(pos, Vector2D) and isinstance(end, Vector2D):
            start_point = pygame.Vector2(pos.x, pos.y)
            end_point = pygame.Vector2(end.x, end.y)
            mouse_point = pygame.Vector2(point.x, point.y)
            segment = end_point - start_point
            if segment.length_squared() == 0:
                distance = (mouse_point - start_point).length()
            else:
                amount = max(0, min(1, (mouse_point - start_point).dot(segment) / segment.length_squared()))
                distance = (mouse_point - (start_point + segment * amount)).length()
            return distance <= max(5, getattr(obj, "width", 1))

        radius = getattr(obj, "radius", None)
        if isinstance(pos, Vector2D) and self._is_position_number(radius):
            delta = point - pos
            return delta.x * delta.x + delta.y * delta.y <= radius * radius

        image = getattr(obj, "image", None)
        if image is None and callable(getattr(obj, "get_image", None)):
            image = obj.get_image()
        if isinstance(pos, Vector2D) and isinstance(image, pygame.Surface):
            return pygame.Rect(pos.to_int(), image.get_size()).collidepoint(point.to_int())

        size = getattr(obj, "dim", None)
        if isinstance(pos, Vector2D) and isinstance(size, Vector2D):
            return pygame.Rect(pos.to_int(), size.to_int()).collidepoint(point.to_int())

        surface = getattr(obj, "screen", None)
        if isinstance(pos, Vector2D) and isinstance(surface, pygame.Surface):
            return pygame.Rect(pos.to_int(), surface.get_size()).collidepoint(point.to_int())

        if isinstance(pos, Vector2D):
            delta = point - pos
            return delta.x * delta.x + delta.y * delta.y <= 8 * 8
        return False

    def _find_draggable_object(self, point):
        for obj in reversed(self.preview_objects):
            variables = self.preview_variables.get(id(obj))
            if (
                variables is not None
                and self._has_position(variables)
                and getattr(obj, "visible", True)
                and self._preview_object_hit(obj, variables, point)
            ):
                return obj, variables
        return None, None

    def _move_object(self, obj, variables, dx, dy):
        self.drag_remainder[0] += dx
        self.drag_remainder[1] += dy
        dx = int(self.drag_remainder[0])
        dy = int(self.drag_remainder[1])
        self.drag_remainder[0] -= dx
        self.drag_remainder[1] -= dy
        if dx == 0 and dy == 0:
            return

        position = variables.get("pos")
        if isinstance(position, (list, tuple)) and len(position) >= 2:
            moved_position = list(position)
            if self._is_position_number(moved_position[0]):
                moved_position[0] += dx
            if self._is_position_number(moved_position[1]):
                moved_position[1] += dy
            variables["pos"] = moved_position

        for axis, delta in (
            ("x", dx),
            ("y", dy),
            ("x1", dx),
            ("y1", dy),
            ("x2", dx),
            ("y2", dy),
        ):
            if axis in variables and self._is_position_number(variables[axis]):
                variables[axis] += delta
            value = getattr(obj, axis, None)
            if self._is_position_number(value):
                setattr(obj, axis, value + delta)

        position = getattr(obj, "pos", None)
        if isinstance(position, Vector2D):
            obj.pos = position + Vector2D(dx, dy)

        rect = getattr(obj, "rect", None)
        if isinstance(rect, pygame.Rect):
            obj.rect = rect.move(dx, dy)

        end = getattr(obj, "end", None)
        if isinstance(end, Vector2D):
            obj.end = end + Vector2D(dx, dy)

        self.preview_signature = json.dumps(
            {
                "objects": self.data["objects"],
                "custom_objects": self.preview_custom_definitions,
                "assets": self.preview_asset_definitions,
            },
            sort_keys=True,
        )

    def render_preview_object(self, obj, target_surface=None):
        if target_surface is None:
            target_surface = self.sub.screen

        if isinstance(obj, PyScene.Tilemap):
            project_path = os.path.join(get_save_dir_path(), Game.project)
            python_path = os.path.join(project_path, "_python")
            previous_cwd = os.getcwd()
            try:
                os.chdir(python_path)
                obj.update()
            finally:
                os.chdir(previous_cwd)
            if not obj.tilemap:
                return

        camera_pos = Game.cam.pos
        original_pos = getattr(obj, "pos", None)
        original_rect = getattr(obj, "rect", None)
        original_end = getattr(obj, "end", None)
        original_axes = {
            axis: getattr(obj, axis)
            for axis in ("x", "y", "x1", "y1", "x2", "y2")
            if self._is_position_number(getattr(obj, axis, None))
        }

        if isinstance(original_pos, Vector2D):
            obj.pos = original_pos - camera_pos
        elif (
            isinstance(original_pos, (list, tuple))
            and len(original_pos) >= 2
            and all(self._is_position_number(value) for value in original_pos[:2])
        ):
            obj.pos = Vector2D(original_pos[0], original_pos[1]) - camera_pos
        if isinstance(original_rect, pygame.Rect):
            obj.rect = original_rect.move(-camera_pos.x, -camera_pos.y)
        if original_end is not None:
            if isinstance(original_end, Vector2D):
                obj.end = original_end - camera_pos
        for axis, offset in (
            ("x", camera_pos.x),
            ("y", camera_pos.y),
            ("x1", camera_pos.x),
            ("y1", camera_pos.y),
            ("x2", camera_pos.x),
            ("y2", camera_pos.y),
        ):
            if axis in original_axes:
                setattr(obj, axis, original_axes[axis] - offset)

        try:
            if isinstance(obj, PyScene.Tilemap):
                target_surface.blit(obj.screen, obj.pos.to_int())
            elif self.preview_render_methods.get(id(obj)) == "render":
                original_screen = Game.screen
                Game.screen = target_surface
                try:
                    obj.render()
                finally:
                    Game.screen = original_screen
            else:
                obj.render_to(target_surface)
        finally:
            if original_pos is not None:
                obj.pos = original_pos
            if original_rect is not None:
                obj.rect = original_rect
            if original_end is not None:
                obj.end = original_end
            for axis, value in original_axes.items():
                setattr(obj, axis, value)

    def update(self):
        viewport = pygame.Rect((0, 0), self.sub.dim.to_int())
        absolute_pos = self.sub.get_absolute_pos()
        scale_x, scale_y = self._view_scale()
        self.refresh_preview_objects()
        for obj in self.preview_objects:
            if isinstance(obj, PyScene.Animation):
                obj.update()

        for event in Game.events:
            scale_x, scale_y = self._view_scale()
            mouse_screen_pos = pygame.mouse.get_pos()
            pointer_pos = Vector2D(*mouse_screen_pos) - absolute_pos
            pointer_in_viewport = viewport.collidepoint(pointer_pos.to_int())
            if event.type == pygame.KEYDOWN and pointer_in_viewport:
                if event.key == pygame.K_f:
                    self.center_camera()
                elif event.key == pygame.K_w:
                    self.tool = "Move"
                elif event.key == pygame.K_r:
                    self.tool = "Scale"
                elif event.key == pygame.K_g:
                    self.snap_enabled = not self.snap_enabled
                elif event.key == pygame.K_h:
                    self.grid_visible = not self.grid_visible
                elif event.key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
                    direction = -1 if event.key == pygame.K_LEFTBRACKET else 1
                    self.grid_index = (self.grid_index + direction) % len(self.grid_sizes)
                    self.GridSize = self.grid_sizes[self.grid_index]
            elif event.type == pygame.MOUSEWHEEL and event.y:
                if pointer_in_viewport:
                    self._zoom_at(pointer_pos, event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = Vector2D(*event.pos) - absolute_pos
                if viewport.collidepoint(mouse_pos.to_int()):
                    if self._handle_grid_dropdown_click(mouse_pos.to_int()):
                        continue
                    if self._handle_toolbar_click(mouse_pos.to_int()):
                        continue
                    world_pos = Vector2D(
                        Game.cam.pos.x + mouse_pos.x / scale_x,
                        Game.cam.pos.y + mouse_pos.y / scale_y,
                    )
                    handle = self._selection_handle_rect()
                    selected_object, selected_variables = self._selected_object()
                    if (
                        self.tool == "Scale"
                        and selected_object is not None
                        and handle is not None
                        and handle.collidepoint(mouse_pos.to_int())
                    ):
                        self._start_scale_drag(selected_object, selected_variables)
                    else:
                        obj, variables = self._find_draggable_object(world_pos)
                        if obj is None:
                            self.selected_name = None
                            self.drag_mode = "pan"
                        else:
                            self.selected_name = self._object_name(obj)
                            if self.tool == "Move":
                                self.drag_mode = "move"
                                self.dragged_object = obj
                                self.dragged_variables = variables
                                self.drag_anchor = self._drag_anchor(variables)
                                self.drag_total = [0.0, 0.0]
                                self.drag_applied = [0.0, 0.0]
                                self.drag_changed = False
                            elif self.tool == "Scale":
                                handle = self._selection_handle_rect()
                                if handle is not None and handle.collidepoint(mouse_pos.to_int()):
                                    self._start_scale_drag(obj, variables)
                            else:
                                self.drag_mode = None
                    self.dragging = self.drag_mode == "pan"
                    self.drag_remainder = [0.0, 0.0]
                else:
                    self.grid_dropdown_open = False
            elif event.type == pygame.MOUSEMOTION and self.drag_mode == "pan":
                Game.cam.pos.x -= event.rel[0] / scale_x
                Game.cam.pos.y -= event.rel[1] / scale_y
            elif event.type == pygame.MOUSEMOTION and self.drag_mode == "move":
                self._apply_move_drag(event.rel[0] / scale_x, event.rel[1] / scale_y)
            elif event.type == pygame.MOUSEMOTION and self.drag_mode == "scale":
                self._apply_scale_drag(event.rel[0] / scale_x, event.rel[1] / scale_y)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if self.drag_changed:
                    self.needs_save = True
                self.drag_mode = None
                self.dragging = False
                self.dragged_object = None
                self.dragged_variables = None
                self.drag_remainder = [0.0, 0.0]
                self.drag_changed = False

    def render(self):
        self.sub.clear()
        self.refresh_preview_objects()
        world_width, world_height = self._world_view_size()
        surface_size = (world_width, world_height)
        if self.preview_surface_size != surface_size:
            self.preview_surface = pygame.Surface(surface_size, pygame.SRCALPHA)
            self.preview_surface_size = surface_size
        world_surface = self.preview_surface
        world_surface.fill((0, 0, 0, 0))

        if self.grid_visible:
            grid_color = Colors["pannel"]
            grid_size = self.GridSize

            first_x = int(-Game.cam.pos.x % grid_size)
            for x in range(first_x, world_width, grid_size):
                pygame.draw.line(world_surface, grid_color, (x, 0), (x, world_height))

            first_y = int(-Game.cam.pos.y % grid_size)
            for y in range(first_y, world_height, grid_size):
                pygame.draw.line(world_surface, grid_color, (0, y), (world_width, y))

        for obj in self.preview_objects:
            if getattr(obj, "visible", True):
                self.render_preview_object(obj, world_surface)

        camera_rect = pygame.Rect(
            int(-Game.cam.pos.x),
            int(-Game.cam.pos.y),
            int(self.game_size.x),
            int(self.game_size.y),
        )
        pygame.draw.rect(
            world_surface,
            (235, 190, 80),
            camera_rect,
            2,
        )

        scaled_surface = pygame.transform.scale(world_surface, self.sub.dim.to_int())
        self.sub.screen.blit(scaled_surface, (0, 0))

        selected_object, selected_variables = self._selected_object()
        if selected_object is not None and selected_variables is not None:
            bounds = self._object_bounds(selected_object, selected_variables)
            if bounds is not None:
                scale_x, scale_y = self._view_scale()
                selection_rect = pygame.Rect(
                    round((bounds.x - Game.cam.pos.x) * scale_x),
                    round((bounds.y - Game.cam.pos.y) * scale_y),
                    max(1, round(bounds.width * scale_x)),
                    max(1, round(bounds.height * scale_y)),
                )
                pygame.draw.rect(self.sub.screen, (95, 190, 255), selection_rect, 2)
                if self._scale_kind(selected_object, selected_variables) is not None:
                    handle = self._selection_handle_rect()
                    if handle is not None:
                        pygame.draw.rect(self.sub.screen, (245, 245, 245), handle)
                        pygame.draw.rect(self.sub.screen, (35, 90, 150), handle, 1)

        pygame.draw.rect(
            self.sub.screen,
            Colors["pannel"],
            (0, 0, self.rect.width, self.rect.height),
            2,
        )

        scale_x, scale_y = self._view_scale()
        axis_x = int(-Game.cam.pos.x * scale_x)
        axis_y = int(-Game.cam.pos.y * scale_y)
        x_axis_color = (220, 90, 90)
        y_axis_color = (90, 190, 130)
        if 0 <= axis_y < self.rect.height:
            pygame.draw.line(self.sub.screen, x_axis_color, (0, axis_y), (self.rect.width, axis_y), 2)
            self.sub.screen.blit(self.axis_font.render("X", True, x_axis_color), (self.rect.width - 18, max(0, axis_y - 18)))
        if 0 <= axis_x < self.rect.width:
            pygame.draw.line(self.sub.screen, y_axis_color, (axis_x, 0), (axis_x, self.rect.height), 2)
            self.sub.screen.blit(self.axis_font.render("Y", True, y_axis_color), (min(self.rect.width - 14, axis_x + 4), 2))
        zoom_label = self.axis_font.render(
            f"{round(self.zoom * 100)}%  |  F center  G snap  H grid  [ ] grid size",
            True,
            "white",
        )
        self.sub.screen.blit(
            zoom_label,
            (max(8, self.rect.width - zoom_label.get_width() - 8), 38),
        )

        toolbar_labels = {
            "Move": "Move",
            "Scale": "Scale",
            "Snap": "Snap ON" if self.snap_enabled else "Snap OFF",
            "Lines": "Lines ON" if self.grid_visible else "Lines OFF",
            "Grid": f"Grid {self.GridSize} v",
        }
        for label, rect in self.toolbar_rects.items():
            active = label == self.tool or (
                (label == "Snap" and self.snap_enabled)
                or (label == "Lines" and self.grid_visible)
            )
            fill = (48, 98, 145) if active else Colors["bg"]
            pygame.draw.rect(self.sub.screen, fill, rect)
            pygame.draw.rect(self.sub.screen, (150, 165, 180), rect, 1)
            text = self.toolbar_font.render(toolbar_labels[label], True, "white")
            self.sub.screen.blit(text, text.get_rect(center=rect.center))

        if self.grid_dropdown_open:
            dropdown_rect = self._grid_dropdown_rect()
            pygame.draw.rect(self.sub.screen, Colors["bg"], dropdown_rect)
            pygame.draw.rect(self.sub.screen, (150, 165, 180), dropdown_rect, 1)
            for index, grid_size in enumerate(self.grid_sizes):
                option_rect = pygame.Rect(
                    dropdown_rect.x,
                    dropdown_rect.y + index * 24,
                    dropdown_rect.width,
                    24,
                )
                if index == self.grid_index:
                    pygame.draw.rect(self.sub.screen, (48, 98, 145), option_rect)
                option = self.toolbar_font.render(str(grid_size), True, "white")
                self.sub.screen.blit(
                    option,
                    option.get_rect(center=option_rect.center),
                )

        selected_object, _ = self._selected_object()
        if selected_object is not None:
            selected_type = self.data["objects"][self.selected_name]["obj_type"]
            status = f"{self.tool}: {self.selected_name} ({selected_type})"
        else:
            status = f"{self.tool}: no object selected"
        max_status_width = max(0, self.rect.width - 16)
        while status and self.axis_font.size(status)[0] > max_status_width:
            status = status[:-1]
        selected_label = self.axis_font.render(status, True, (150, 210, 255))
        self.sub.screen.blit(selected_label, (8, self.rect.height - 22))

        self.sub.render()
