from PyScene import *
import PyScene
import pygame
import json
import os

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
        self.dragging = False
        self.game_size = Vector2D(0, 0)
        self.preview_objects = []
        self.preview_variables = {}
        self.preview_signature = None
        self.preview_custom_definitions = {}
        self.dragged_object = None
        self.dragged_variables = None
        self.axis_font = pygame.font.Font(None, 18)

        #load game bg
        with open(get_save_dir_path()+f"/{Game.project}/project.json", "r") as f:
            game_data: dict = json.load(f)

        self.game_size = Vector2D(game_data["window"]["width"], game_data["window"]["height"])
        self.sub = SubScreen(rect.x, rect.y, rect.width, rect.height, game_data["window"]["bg_color"], sub.screen, sub)

    def center_camera(self):
        Game.cam.pos = Vector2D(
            (self.game_size.x - self.sub.dim.x) / 2,
            (self.game_size.y - self.sub.dim.y) / 2,
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

        signature = json.dumps(
            {"objects": self.data["objects"], "custom_objects": custom_definitions},
            sort_keys=True,
        )
        if signature == self.preview_signature:
            return

        self.preview_objects = []
        self.preview_variables = {}
        queue_length = len(Game.queue_creation)
        game_id = Game.id
        always_global = Game.always_global
        Game.always_global = True
        try:
            for object_data in self.data["objects"].values():
                obj_type = object_data["obj_type"]
                obj_class = getattr(PyScene, obj_type, None)
                if obj_class is not None:
                    if not callable(getattr(obj_class, "render_to", None)):
                        continue
                    obj = obj_class(*object_data["variables"].values())
                else:
                    obj_definition = custom_definitions[obj_type]
                    functions = obj_definition["functions"]
                    render_to = functions.get("render_to")
                    if render_to is None or len(render_to["args"]) != 1:
                        continue

                    namespace = {"__name__": f"{obj_type}_preview"}
                    source = "from PyScene import *\nimport pygame\n"
                    source += "".join(f"{line}\n" for line in obj_definition["imports"])
                    source += f"\nclass {obj_type}(GameObj):\n"

                    init_args = functions["__init__"]["args"]
                    arg_names = [arg["name"] for arg in init_args]
                    source += f"    def __init__(self{', ' if arg_names else ''}{', '.join(arg_names)}):\n"
                    variables = obj_definition["variables"]
                    position = variables["pos"]
                    source += (
                        "        super().__init__(Vector2D("
                        f"{position[0]!r}, {position[1]!r}), "
                        f"{variables['z_index']!r}, "
                        f"{variables['active']!r}, "
                        f"{variables['visible']!r}, "
                        f"{variables['Global']!r})\n"
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
                        object_data["variables"].get(arg["name"], arg["default"])
                        for arg in init_args
                    ]
                    obj = obj_class(*obj_args)

                if callable(getattr(obj, "render_to", None)):
                    self.preview_objects.append(obj)
                    self.preview_variables[id(obj)] = object_data["variables"]
        finally:
            del Game.queue_creation[queue_length:]
            Game.id = game_id
            Game.always_global = always_global

        self.preview_objects.sort(key=lambda obj: getattr(obj, "z_index", 0))
        self.preview_custom_definitions = custom_definitions
        self.preview_signature = signature

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
            for axis in ("x", "y")
        )
        return has_pos or has_axis

    def _preview_object_hit(self, obj, variables, point):
        rect = getattr(obj, "rect", None)
        if isinstance(rect, pygame.Rect):
            return rect.collidepoint(point.to_int())

        pos = getattr(obj, "pos", None)
        if isinstance(pos, Vector2D) and (
            self._is_position_number(variables.get("x"))
            or self._is_position_number(variables.get("y"))
        ):
            pos = Vector2D(
                variables.get("x", pos.x),
                variables.get("y", pos.y),
            )
        end = getattr(obj, "end", None)
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

        size = getattr(obj, "dim", None)
        if isinstance(pos, Vector2D) and isinstance(size, Vector2D):
            return pygame.Rect(pos.to_int(), size.to_int()).collidepoint(point.to_int())

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
        position = variables.get("pos")
        if isinstance(position, (list, tuple)) and len(position) >= 2:
            moved_position = list(position)
            if self._is_position_number(moved_position[0]):
                moved_position[0] += dx
            if self._is_position_number(moved_position[1]):
                moved_position[1] += dy
            variables["pos"] = moved_position

        for axis, delta in (("x", dx), ("y", dy)):
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
            },
            sort_keys=True,
        )

    def render_preview_object(self, obj):
        camera_pos = Game.cam.pos
        original_pos = getattr(obj, "pos", None)
        original_rect = getattr(obj, "rect", None)
        original_end = getattr(obj, "end", None)
        original_axes = {
            axis: getattr(obj, axis)
            for axis in ("x", "y")
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
            obj.end = original_end - camera_pos
        for axis, offset in (("x", camera_pos.x), ("y", camera_pos.y)):
            if axis in original_axes:
                setattr(obj, axis, original_axes[axis] - offset)

        try:
            obj.render_to(self.sub.screen)
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
        self.refresh_preview_objects()

        for event in Game.events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                self.center_camera()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = Vector2D(*event.pos) - absolute_pos
                if viewport.collidepoint(mouse_pos.to_int()):
                    world_pos = mouse_pos + Game.cam.pos
                    self.dragged_object, self.dragged_variables = self._find_draggable_object(world_pos)
                    self.dragging = self.dragged_object is None
            elif event.type == pygame.MOUSEMOTION and self.dragging:
                Game.cam.pos.x -= event.rel[0]
                Game.cam.pos.y -= event.rel[1]
            elif event.type == pygame.MOUSEMOTION and self.dragged_object is not None:
                self._move_object(
                    self.dragged_object,
                    self.dragged_variables,
                    event.rel[0],
                    event.rel[1],
                )
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging = False
                self.dragged_object = None
                self.dragged_variables = None

    def render(self):
        self.sub.clear()
        self.refresh_preview_objects()

        grid_color = Colors["pannel"]
        grid_size = self.GridSize

        first_x = int(-Game.cam.pos.x % grid_size)
        for x in range(first_x, self.rect.width, grid_size):
            pygame.draw.line(self.sub.screen, grid_color, (x, 0), (x, self.rect.height))

        first_y = int(-Game.cam.pos.y % grid_size)
        for y in range(first_y, self.rect.height, grid_size):
            pygame.draw.line(self.sub.screen, grid_color, (0, y), (self.rect.width, y))

        for obj in self.preview_objects:
            if getattr(obj, "visible", True):
                self.render_preview_object(obj)

        pygame.draw.rect(
            self.sub.screen,
            Colors["pannel"],
            (0, 0, self.rect.width, self.rect.height),
            2,
        )

        camera_rect = pygame.Rect(
            int(-Game.cam.pos.x),
            int(-Game.cam.pos.y),
            int(self.game_size.x),
            int(self.game_size.y),
        )
        pygame.draw.rect(self.sub.screen, (235, 190, 80), camera_rect, 2)

        axis_x = int(-Game.cam.pos.x)
        axis_y = int(-Game.cam.pos.y)
        x_axis_color = (220, 90, 90)
        y_axis_color = (90, 190, 130)
        if 0 <= axis_y < self.rect.height:
            pygame.draw.line(self.sub.screen, x_axis_color, (0, axis_y), (self.rect.width, axis_y), 2)
            self.sub.screen.blit(self.axis_font.render("X", True, x_axis_color), (self.rect.width - 18, max(0, axis_y - 18)))
        if 0 <= axis_x < self.rect.width:
            pygame.draw.line(self.sub.screen, y_axis_color, (axis_x, 0), (axis_x, self.rect.height), 2)
            self.sub.screen.blit(self.axis_font.render("Y", True, y_axis_color), (min(self.rect.width - 14, axis_x + 4), 2))

        self.sub.render()
