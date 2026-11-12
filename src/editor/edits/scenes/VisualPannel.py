from PyScene import *
import PyScene
import pygame
import json
import math
import os
import copy
import keyword
from PyScene.utils.Assets import load_tileset

from ....utils.load_assets import Colors
from ....utils.files import *

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
        self.dragged_objects = []
        self.drag_mode = None
        self.drag_changed = False
        self.drag_total = [0.0, 0.0]
        self.drag_applied = [0.0, 0.0]
        self.drag_anchor = [0.0, 0.0]
        self.drag_remainders = {}
        self.drag_start_size = None
        self.drag_start_scale = 1.0
        self.drag_group_start = None
        self.drag_group_state = []
        self.drag_move_bounds = None
        self.drag_scale_bounds = None
        self.selected_name = None
        self.selected_names = set()
        self.duplicate_name_map = {}
        self.history_action = None
        self.refresh_object_list = False
        self.rename_target = None
        self.rename_buffer = ""
        self.rename_error = ""
        self.rename_select_all = False
        self.interaction_message = ""
        self.tool = "Move"
        self.snap_enabled = True
        self.smart_snap_enabled = True
        self.snap_guides = {"x": None, "y": None}
        self.grid_visible = True
        self.needs_save = False
        self.grid_sizes = (8, 16, 32, 64)
        self.grid_index = self.grid_sizes.index(self.GridSize)
        self.grid_dropdown_open = False
        self.context_menu_open = False
        self.context_menu_pos = (0, 0)
        self.context_menu_actions = (
            "Duplicate",
            "Delete",
            "Rename",
            "Raise Layer",
            "Lower Layer",
        )
        self.context_menu_row_height = 26
        self.tooltip_hints = {
            "Move": "Move selected objects (W)",
            "Scale": "Resize selection (R)",
            "Snap": "Toggle grid snapping (G)",
            "Smart": "Toggle object snapping",
            "Lines": "Toggle grid lines (H)",
            "Grid": "Choose grid spacing",
        }
        self.hovered_toolbar = None
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
            ("Smart", 58),
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
            elif label == "Smart":
                self.smart_snap_enabled = not self.smart_snap_enabled
            elif label == "Lines":
                self.grid_visible = not self.grid_visible
            else:
                self.grid_dropdown_open = not self.grid_dropdown_open
            return True
        return False

    def _unique_object_name(self, base_name):
        names = self.data["objects"]
        candidate = f"{base_name}_copy"
        suffix = 2
        while candidate in names:
            candidate = f"{base_name}_copy_{suffix}"
            suffix += 1
        return candidate

    def _duplicate_selection(self, save=True):
        selected_names = [
            name for name in self.data["objects"]
            if name in self.selected_names
        ]
        if not selected_names:
            return False

        duplicates = {}
        self.duplicate_name_map = {}
        for name in selected_names:
            new_name = self._unique_object_name(name)
            object_data = copy.deepcopy(self.data["objects"][name])
            duplicates[new_name] = object_data
            self.duplicate_name_map[name] = new_name
        self.data["objects"].update(duplicates)
        self.selected_names = set(duplicates)
        self.selected_name = next(reversed(duplicates))
        self.preview_signature = None
        self.refresh_preview_objects()
        self.refresh_object_list = True
        self.needs_save = save
        return True

    def _delete_selection(self):
        if not self.selected_names:
            return False
        for name in self.selected_names:
            self.data["objects"].pop(name, None)
        self.selected_names.clear()
        self.selected_name = None
        self.preview_signature = None
        self.refresh_preview_objects()
        self.refresh_object_list = True
        self.needs_save = True
        return True

    def _rename_selected(self):
        old_name = self.rename_target
        new_name = self.rename_buffer.strip()
        if not old_name or old_name not in self.data["objects"]:
            self.rename_target = None
            self.rename_select_all = False
            return
        if not new_name.isidentifier() or keyword.iskeyword(new_name):
            self.rename_error = "Use a non-keyword Python identifier."
            return
        if new_name != old_name and new_name in self.data["objects"]:
            new_name = self._unique_object_name(new_name)

        object_data = self.data["objects"].pop(old_name)
        self.data["objects"][new_name] = object_data
        self.selected_names = {new_name}
        self.selected_name = new_name
        self.rename_target = None
        self.rename_select_all = False
        self.rename_error = ""
        self.preview_signature = None
        self.refresh_preview_objects()
        self.refresh_object_list = True
        self.needs_save = True

    def _change_selected_layer(self, direction):
        selected = self._selected_objects()
        if not selected:
            return
        layers = []
        for obj, variables in selected:
            layer = variables.get("z_index", getattr(obj, "z_index", 0))
            if not self._is_position_number(layer):
                self.interaction_message = (
                    f"Cannot change layer: {self._object_name(obj)!r} has an invalid z_index."
                )
                return
            layers.append(layer)
        for (obj, variables), layer in zip(selected, layers):
            variables["z_index"] = layer + direction
            obj.z_index = layer + direction
        self.preview_objects.sort(key=lambda obj: getattr(obj, "z_index", 0))
        self.interaction_message = ""
        self.needs_save = True
        self.preview_signature = None

    def _open_context_menu(self, local_pos, obj=None):
        if obj is not None and self._object_name(obj) not in self.selected_names:
            self.selected_names = {self._object_name(obj)}
            self.selected_name = self._object_name(obj)
        x, y = local_pos
        width = 150
        height = len(self.context_menu_actions) * self.context_menu_row_height
        x = max(0, min(x, self.rect.width - width))
        y = max(0, min(y, self.rect.height - height))
        self.context_menu_pos = (x, y)
        self.context_menu_open = True

    def _context_menu_rect(self):
        return pygame.Rect(
            self.context_menu_pos,
            (150, len(self.context_menu_actions) * self.context_menu_row_height),
        )

    def _handle_context_menu_click(self, position):
        if not self.context_menu_open:
            return False
        menu_rect = self._context_menu_rect()
        if not menu_rect.collidepoint(position):
            self.context_menu_open = False
            return False
        index = (position[1] - menu_rect.y) // self.context_menu_row_height
        action = self.context_menu_actions[index]
        self.context_menu_open = False
        if action == "Duplicate":
            self._duplicate_selection()
        elif action == "Delete":
            self._delete_selection()
        elif action == "Rename" and self.selected_name:
            self.rename_target = self.selected_name
            self.rename_buffer = self.selected_name
            self.rename_error = ""
            self.rename_select_all = True
        elif action == "Raise Layer":
            self._change_selected_layer(1)
        elif action == "Lower Layer":
            self._change_selected_layer(-1)
        return True

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

    def _selected_objects(self):
        return [
            (obj, self.preview_variables[id(obj)])
            for obj in self.preview_objects
            if self._object_name(obj) in self.selected_names
            and id(obj) in self.preview_variables
        ]

    def _select_object(self, obj, additive=False):
        name = self._object_name(obj)
        if additive and name in self.selected_names:
            self.selected_names.remove(name)
            if self.selected_name == name:
                self.selected_name = next(iter(self.selected_names), None)
            return False
        if not additive and name not in self.selected_names:
            self.selected_names = {name}
        else:
            self.selected_names.add(name)
        self.selected_name = name
        return True

    def _selected_bounds(self, view=False):
        bounds = []
        for obj, variables in self._selected_objects():
            object_bounds = (
                self._object_view_bounds(obj, variables)
                if view
                else self._object_bounds(obj, variables)
            )
            if object_bounds is not None:
                bounds.append(object_bounds)
        if not bounds:
            return None
        return bounds[0].unionall(bounds[1:])

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
        if callable(getattr(obj, "get_image", None)):
            image = obj.get_image()
        if isinstance(image, pygame.Surface):
            return pygame.Rect(pos.to_int(), image.get_size())

        size = getattr(obj, "dim", None)
        if isinstance(size, Vector2D):
            return pygame.Rect(pos.to_int(), size.to_int())

        surface = getattr(obj, "screen", None)
        if isinstance(surface, pygame.Surface):
            return pygame.Rect(pos.to_int(), surface.get_size())

        if all(self._is_position_number(variables.get(axis)) for axis in ("w", "h")):
            return pygame.Rect(pos.to_int(), (max(1, variables["w"]), max(1, variables["h"])))
        return pygame.Rect(pos.to_int(), (16, 16))

    def _object_view_bounds(self, obj, variables):
        bounds = self._object_bounds(obj, variables)
        if bounds is None:
            return None

        camera_pos = Game.cam.pos
        rect = getattr(obj, "rect", None)
        if isinstance(rect, pygame.Rect):
            return rect.move(-camera_pos.x, -camera_pos.y)

        pos = getattr(obj, "pos", None)
        if not isinstance(pos, Vector2D):
            position = variables.get("pos")
            if isinstance(position, (list, tuple)) and len(position) >= 2:
                pos = Vector2D(*position[:2])
            elif all(self._is_position_number(variables.get(axis)) for axis in ("x", "y")):
                pos = Vector2D(variables["x"], variables["y"])
            elif all(self._is_position_number(variables.get(axis)) for axis in ("x1", "y1")):
                pos = Vector2D(variables["x1"], variables["y1"])
        if not isinstance(pos, Vector2D):
            return bounds.move(-camera_pos.x, -camera_pos.y)

        end = getattr(obj, "end", None)
        if not isinstance(end, Vector2D) and all(
            self._is_position_number(variables.get(axis))
            for axis in ("x2", "y2")
        ):
            end = Vector2D(variables["x2"], variables["y2"])
        view_pos = (pos - camera_pos).to_int()
        if isinstance(end, Vector2D):
            view_end = (end - camera_pos).to_int()
            return pygame.Rect(
                min(view_pos[0], view_end[0]),
                min(view_pos[1], view_end[1]),
                max(1, abs(view_end[0] - view_pos[0])),
                max(1, abs(view_end[1] - view_pos[1])),
            )

        radius = getattr(obj, "radius", None)
        if self._is_position_number(radius):
            radius = max(1, int(radius))
            return pygame.Rect(
                view_pos[0] - radius,
                view_pos[1] - radius,
                radius * 2,
                radius * 2,
            )

        return pygame.Rect(view_pos, bounds.size)

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
        if not any(
            self._scale_kind(obj, variables) is not None
            for obj, variables in self._selected_objects()
        ):
            return None
        bounds = self._selected_bounds(view=True)
        if bounds is None:
            return None
        scale_x, scale_y = self._view_scale()
        right = round(bounds.right * scale_x)
        bottom = round(bounds.bottom * scale_y)
        return pygame.Rect(right - 5, bottom - 5, 10, 10)

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
        if self.smart_snap_enabled:
            target = self._smart_snap_move(target)
        else:
            self.snap_guides = {"x": None, "y": None}
        delta = [target[0] - self.drag_applied[0], target[1] - self.drag_applied[1]]
        if delta != [0, 0]:
            for obj, variables in self.dragged_objects or [
                (self.dragged_object, self.dragged_variables)
            ]:
                remainder = self.drag_remainders.setdefault(id(obj), [0.0, 0.0])
                self._move_object(
                    obj,
                    variables,
                    delta[0],
                    delta[1],
                    remainder,
                )
            self.drag_applied = target
            self.drag_changed = True

    def _smart_snap_move(self, target):
        bounds = self.drag_move_bounds
        if bounds is None:
            self.snap_guides = {"x": None, "y": None}
            return target

        scale_x, scale_y = self._view_scale()
        thresholds = (8 / max(scale_x, 0.01), 8 / max(scale_y, 0.01))
        moving_features = (
            (bounds.left, bounds.centerx, bounds.right),
            (bounds.top, bounds.centery, bounds.bottom),
        )
        stationary_features = [[], []]
        for obj in self.preview_objects:
            if self._object_name(obj) in self.selected_names:
                continue
            if not getattr(obj, "visible", True):
                continue
            variables = self.preview_variables.get(id(obj))
            if variables is None:
                continue
            other_bounds = self._object_bounds(obj, variables)
            if other_bounds is None:
                continue
            stationary_features[0].extend(
                (other_bounds.left, other_bounds.centerx, other_bounds.right)
            )
            stationary_features[1].extend(
                (other_bounds.top, other_bounds.centery, other_bounds.bottom)
            )

        self.snap_guides = {"x": None, "y": None}
        snapped = list(target)
        for axis, (leading, center, trailing) in enumerate(moving_features):
            best = None
            for moving in (leading, center, trailing):
                for fixed in stationary_features[axis]:
                    offset = fixed - (moving + target[axis])
                    candidate = (abs(offset), offset, fixed)
                    if abs(offset) <= thresholds[axis] and (
                        best is None or candidate[0] < best[0]
                    ):
                        best = candidate
            if best is not None:
                snapped[axis] += best[1]
                self.snap_guides["x" if axis == 0 else "y"] = best[2]
        return snapped

    def _smart_snap_resize(self, bounds, width, height):
        if not self.smart_snap_enabled:
            self.snap_guides = {"x": None, "y": None}
            return width, height

        scale_x, scale_y = self._view_scale()
        thresholds = (8 / max(scale_x, 0.01), 8 / max(scale_y, 0.01))
        stationary_features = [[], []]
        for obj in self.preview_objects:
            if self._object_name(obj) in self.selected_names:
                continue
            if not getattr(obj, "visible", True):
                continue
            variables = self.preview_variables.get(id(obj))
            if variables is None:
                continue
            other_bounds = self._object_bounds(obj, variables)
            if other_bounds is None:
                continue
            stationary_features[0].extend(
                (other_bounds.left, other_bounds.centerx, other_bounds.right)
            )
            stationary_features[1].extend(
                (other_bounds.top, other_bounds.centery, other_bounds.bottom)
            )

        self.snap_guides = {"x": None, "y": None}
        sizes = [width, height]
        origins = (bounds.left, bounds.top)
        for axis in (0, 1):
            edge = origins[axis] + sizes[axis]
            best = min(
                (
                    (abs(fixed - edge), fixed)
                    for fixed in stationary_features[axis]
                    if abs(fixed - edge) <= thresholds[axis]
                ),
                default=None,
            )
            if best is not None:
                sizes[axis] = max(1, best[1] - origins[axis])
                self.snap_guides["x" if axis == 0 else "y"] = best[1]
        return sizes[0], sizes[1]

    def _smart_snap_width(self, bounds, width):
        if not self.smart_snap_enabled:
            self.snap_guides = {"x": None, "y": None}
            return width

        scale_x, _ = self._view_scale()
        threshold = 8 / max(scale_x, 0.01)
        stationary_features = []
        for obj in self.preview_objects:
            if self._object_name(obj) in self.selected_names:
                continue
            if not getattr(obj, "visible", True):
                continue
            variables = self.preview_variables.get(id(obj))
            if variables is None:
                continue
            other_bounds = self._object_bounds(obj, variables)
            if other_bounds is not None:
                stationary_features.extend(
                    (other_bounds.left, other_bounds.centerx, other_bounds.right)
                )

        edge = bounds.left + width
        best = min(
            (
                (abs(fixed - edge), fixed)
                for fixed in stationary_features
                if abs(fixed - edge) <= threshold
            ),
            default=None,
        )
        self.snap_guides = {"x": None, "y": None}
        if best is not None:
            self.snap_guides["x"] = best[1]
            return max(1, best[1] - bounds.left)
        return width

    def _start_scale_drag(self, obj, variables):
        self.drag_mode = "scale"
        self.dragged_object = obj
        self.dragged_variables = variables
        self.drag_total = [0.0, 0.0]
        self.drag_anchor = self._drag_anchor(variables)
        self.drag_start_size = None
        self.drag_group_start = None
        self.drag_group_state = []
        self.drag_scale_bounds = None
        self.dragged_objects = self._selected_objects()
        if len(self.dragged_objects) > 1:
            self.drag_group_start = self._selected_bounds()
            self.drag_group_state = [
                (selected_obj, selected_vars, copy.deepcopy(selected_vars), self._object_bounds(selected_obj, selected_vars))
                for selected_obj, selected_vars in self.dragged_objects
            ]
            self.drag_changed = False
            return

        self.drag_scale_bounds = self._object_bounds(obj, variables)
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
        if self.drag_group_start is not None:
            self._apply_group_scale_drag()
            return

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
            if self.drag_scale_bounds is not None:
                width, height = self._smart_snap_resize(
                    self.drag_scale_bounds,
                    width,
                    height,
                )
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
            if self.drag_scale_bounds is not None:
                scaled_width = self._smart_snap_width(
                    self.drag_scale_bounds,
                    scaled_width,
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

    def _apply_group_scale_drag(self):
        bounds = self.drag_group_start
        width = bounds.width + self.drag_total[0]
        height = bounds.height + self.drag_total[1]
        if self.snap_enabled:
            width = round((bounds.left + width) / self.GridSize) * self.GridSize - bounds.left
            height = round((bounds.top + height) / self.GridSize) * self.GridSize - bounds.top
        width, height = self._smart_snap_resize(bounds, width, height)
        width = max(1, width)
        height = max(1, height)
        scale_x = width / max(1, bounds.width)
        scale_y = height / max(1, bounds.height)
        uniform_scale = min(scale_x, scale_y)

        for obj, variables, initial_variables, initial_bounds in self.drag_group_state:
            if initial_bounds is None:
                continue
            for x_key, y_key in (("x", "y"), ("x1", "y1"), ("x2", "y2")):
                if all(
                    self._is_position_number(initial_variables.get(key))
                    for key in (x_key, y_key)
                ):
                    variables[x_key] = bounds.left + (
                        initial_variables[x_key] - bounds.left
                    ) * scale_x
                    variables[y_key] = bounds.top + (
                        initial_variables[y_key] - bounds.top
                    ) * scale_y

            position = initial_variables.get("pos")
            if isinstance(position, (list, tuple)) and len(position) >= 2:
                variables["pos"] = [
                    bounds.left + (position[0] - bounds.left) * scale_x,
                    bounds.top + (position[1] - bounds.top) * scale_y,
                    *list(position[2:]),
                ]
                object_x, object_y = variables["pos"][:2]
            elif all(
                self._is_position_number(initial_variables.get(key))
                for key in ("x", "y")
            ):
                object_x, object_y = variables["x"], variables["y"]
            elif all(
                self._is_position_number(initial_variables.get(key))
                for key in ("x1", "y1")
            ):
                object_x, object_y = variables["x1"], variables["y1"]
            else:
                initial_pos = getattr(obj, "pos", None)
                if isinstance(initial_pos, Vector2D):
                    object_x = bounds.left + (
                        initial_pos.x - bounds.left
                    ) * scale_x
                    object_y = bounds.top + (
                        initial_pos.y - bounds.top
                    ) * scale_y
                else:
                    object_x, object_y = None, None

            if object_x is not None and object_y is not None:
                obj.pos = Vector2D(object_x, object_y)
                rect = getattr(obj, "rect", None)
                if isinstance(rect, pygame.Rect):
                    rect.topleft = obj.pos.to_int()
            if (
                hasattr(obj, "end")
                and all(
                    self._is_position_number(variables.get(key))
                    for key in ("x2", "y2")
                )
            ):
                obj.end = Vector2D(variables["x2"], variables["y2"])

            if all(
                self._is_position_number(initial_variables.get(key))
                for key in ("w", "h")
            ):
                new_width = max(1, round(initial_variables["w"] * scale_x))
                new_height = max(1, round(initial_variables["h"] * scale_y))
                variables["w"], variables["h"] = new_width, new_height
                if hasattr(obj, "w"):
                    obj.w = new_width
                if hasattr(obj, "h"):
                    obj.h = new_height
                if hasattr(obj, "dim"):
                    obj.dim = Vector2D(new_width, new_height)
                rect = getattr(obj, "rect", None)
                if isinstance(rect, pygame.Rect):
                    rect.size = (new_width, new_height)
            elif self._is_position_number(initial_variables.get("r")):
                obj.radius = max(1, round(initial_variables["r"] * uniform_scale))
                variables["r"] = obj.radius

            if self._is_position_number(initial_variables.get("editor_scale")) or (
                isinstance(getattr(obj, "image", None), pygame.Surface)
                and not isinstance(obj, PyScene.Animation)
            ):
                original = self.preview_original_images.get(id(obj))
                if original is not None:
                    image_scale = initial_variables.get("editor_scale", 1.0) * uniform_scale
                    image_scale = max(0.1, image_scale)
                    variables["editor_scale"] = image_scale
                    obj.image = pygame.transform.scale_by(original, image_scale)

        self.drag_changed = self.drag_changed or any(
            variables != initial_variables
            for _, variables, initial_variables, _ in self.drag_group_state
        )
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

    def frame_selection(self):
        bounds = self._selected_bounds()
        if bounds is None:
            self.center_camera()
            return
        if bounds.width <= 0 or bounds.height <= 0:
            self.center_camera()
            return
        self.zoom = max(
            self.min_zoom,
            min(
                self.max_zoom,
                min(
                    self.sub.dim.x / bounds.width,
                    self.sub.dim.y / bounds.height,
                ) * 0.8,
            ),
        )
        view_width, view_height = self._world_view_size()
        Game.cam.pos = Vector2D(
            bounds.centerx - view_width / 2,
            bounds.centery - view_height / 2,
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
        self._zoom_to(
            mouse_pos,
            self.zoom * (1.1 ** wheel_steps),
        )

    def _zoom_to(self, mouse_pos, zoom):
        old_scale_x, old_scale_y = self._view_scale()
        world_x = Game.cam.pos.x + mouse_pos.x / old_scale_x
        world_y = Game.cam.pos.y + mouse_pos.y / old_scale_y
        self.zoom = max(
            self.min_zoom,
            min(self.max_zoom, zoom),
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
        self.selected_names.intersection_update(self.data["objects"])
        if self.selected_name not in self.data["objects"]:
            self.selected_name = None
        if self.selected_name is None and self.selected_names:
            self.selected_name = next(iter(self.selected_names))

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
        if callable(getattr(obj, "get_image", None)):
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

    def _move_object(self, obj, variables, dx, dy, remainder=None):
        if remainder is None:
            remainder = self.drag_remainder
        remainder[0] += dx
        remainder[1] += dy
        dx = int(remainder[0])
        dy = int(remainder[1])
        remainder[0] -= dx
        remainder[1] -= dy
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
        self.history_action = None
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
            if event.type == pygame.KEYDOWN and self.rename_target is not None:
                if event.key == pygame.K_ESCAPE:
                    self.rename_target = None
                    self.rename_error = ""
                    self.rename_select_all = False
                elif event.key == pygame.K_RETURN:
                    self._rename_selected()
                elif (
                    event.key == pygame.K_a
                    and getattr(event, "mod", 0) & pygame.KMOD_CTRL
                ):
                    self.rename_select_all = True
                elif event.key == pygame.K_BACKSPACE:
                    self.rename_buffer = (
                        ""
                        if self.rename_select_all
                        else self.rename_buffer[:-1]
                    )
                    self.rename_select_all = False
                elif event.unicode and not (
                    getattr(event, "mod", 0) & pygame.KMOD_CTRL
                ):
                    if self.rename_select_all:
                        self.rename_buffer = ""
                    self.rename_buffer += event.unicode
                    self.rename_select_all = False
            elif event.type == pygame.KEYDOWN and pointer_in_viewport:
                modifiers = getattr(event, "mod", 0)
                if modifiers & pygame.KMOD_CTRL and event.key == pygame.K_z:
                    self.history_action = (
                        "redo" if modifiers & pygame.KMOD_SHIFT else "undo"
                    )
                elif modifiers & pygame.KMOD_CTRL and event.key == pygame.K_y:
                    self.history_action = "redo"
                elif modifiers & pygame.KMOD_CTRL and event.key == pygame.K_d:
                    self._duplicate_selection()
                elif event.key in (
                    pygame.K_LEFT,
                    pygame.K_RIGHT,
                    pygame.K_UP,
                    pygame.K_DOWN,
                ):
                    amount = self.GridSize if modifiers & pygame.KMOD_SHIFT else 1
                    dx = amount if event.key == pygame.K_RIGHT else -amount if event.key == pygame.K_LEFT else 0
                    dy = amount if event.key == pygame.K_DOWN else -amount if event.key == pygame.K_UP else 0
                    selected = self._selected_objects()
                    if selected:
                        for obj, variables in selected:
                            self._move_object(obj, variables, dx, dy, [0.0, 0.0])
                        self.needs_save = True
                elif event.key == pygame.K_f:
                    self.frame_selection()
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    preset = {
                        pygame.K_1: 0.5,
                        pygame.K_2: 1.0,
                        pygame.K_3: 2.0,
                    }[event.key]
                    self._zoom_to(
                        Vector2D(self.sub.dim.x / 2, self.sub.dim.y / 2),
                        preset,
                    )
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
                elif event.key == pygame.K_ESCAPE:
                    self.context_menu_open = False
            elif event.type == pygame.MOUSEWHEEL and event.y:
                if pointer_in_viewport:
                    self._zoom_at(pointer_pos, event.y)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                mouse_pos = Vector2D(*event.pos) - absolute_pos
                if viewport.collidepoint(mouse_pos.to_int()):
                    world_pos = Vector2D(
                        Game.cam.pos.x + mouse_pos.x / scale_x,
                        Game.cam.pos.y + mouse_pos.y / scale_y,
                    )
                    obj, _ = self._find_draggable_object(world_pos)
                    self._open_context_menu(mouse_pos.to_int(), obj)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:
                mouse_pos = Vector2D(*event.pos) - absolute_pos
                if viewport.collidepoint(mouse_pos.to_int()):
                    self.context_menu_open = False
                    self.drag_mode = "pan"
                    self.dragging = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = Vector2D(*event.pos) - absolute_pos
                if viewport.collidepoint(mouse_pos.to_int()):
                    if self._handle_context_menu_click(mouse_pos.to_int()):
                        continue
                    if self._handle_grid_dropdown_click(mouse_pos.to_int()):
                        continue
                    if self._handle_toolbar_click(mouse_pos.to_int()):
                        continue
                    self.context_menu_open = False
                    if pygame.key.get_pressed()[pygame.K_SPACE]:
                        self.drag_mode = "pan"
                        self.dragging = True
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
                        modifiers = getattr(event, "mod", 0) | pygame.key.get_mods()
                        additive_selection = bool(modifiers & pygame.KMOD_SHIFT)
                        if obj is None:
                            if not additive_selection:
                                self.selected_names.clear()
                                self.selected_name = None
                            self.drag_mode = "pan"
                        else:
                            is_selected = self._select_object(
                                obj,
                                additive=additive_selection,
                            )
                            if not is_selected:
                                self.drag_mode = None
                            elif self.tool == "Move" or (
                                modifiers & pygame.KMOD_ALT
                            ):
                                if modifiers & pygame.KMOD_ALT:
                                    original_name = self._object_name(obj)
                                    if self._duplicate_selection(save=False):
                                        duplicate_name = self.duplicate_name_map.get(
                                            original_name
                                        )
                                        self.selected_name = duplicate_name
                                        obj, variables = self._selected_object()
                                        self.drag_changed = True
                                self.drag_mode = "move"
                                self.dragged_object = obj
                                self.dragged_variables = variables
                                self.dragged_objects = self._selected_objects()
                                self.drag_anchor = self._drag_anchor(variables)
                                self.drag_move_bounds = self._selected_bounds()
                                self.drag_total = [0.0, 0.0]
                                self.drag_applied = [0.0, 0.0]
                                self.drag_changed = bool(
                                    modifiers & pygame.KMOD_ALT
                                )
                                self.drag_remainders = {}
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
                    self.context_menu_open = False
            elif event.type == pygame.MOUSEMOTION and self.drag_mode == "pan":
                Game.cam.pos.x -= event.rel[0] / scale_x
                Game.cam.pos.y -= event.rel[1] / scale_y
            elif event.type == pygame.MOUSEMOTION and self.drag_mode == "move":
                self._apply_move_drag(event.rel[0] / scale_x, event.rel[1] / scale_y)
            elif event.type == pygame.MOUSEMOTION and self.drag_mode == "scale":
                self._apply_scale_drag(event.rel[0] / scale_x, event.rel[1] / scale_y)
            elif event.type == pygame.MOUSEBUTTONUP and event.button in (1, 2):
                if self.drag_changed:
                    self.needs_save = True
                self.drag_mode = None
                self.dragging = False
                self.dragged_object = None
                self.dragged_variables = None
                self.dragged_objects = []
                self.drag_group_start = None
                self.drag_group_state = []
                self.drag_move_bounds = None
                self.drag_scale_bounds = None
                self.drag_remainder = [0.0, 0.0]
                self.drag_remainders = {}
                self.drag_changed = False
                self.snap_guides = {"x": None, "y": None}

        pointer_pos = Vector2D(*pygame.mouse.get_pos()) - absolute_pos
        self.hovered_toolbar = next(
            (
                label for label, rect in self.toolbar_rects.items()
                if rect.collidepoint(pointer_pos.to_int())
            ),
            None,
        )

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

        selected_objects = self._selected_objects()
        for selected_object, selected_variables in selected_objects:
            bounds = self._object_view_bounds(selected_object, selected_variables)
            if bounds is not None:
                scale_x, scale_y = self._view_scale()
                left = round(bounds.left * scale_x)
                top = round(bounds.top * scale_y)
                right = round(bounds.right * scale_x)
                bottom = round(bounds.bottom * scale_y)
                selection_rect = pygame.Rect(
                    left,
                    top,
                    max(1, right - left),
                    max(1, bottom - top),
                )
                pygame.draw.rect(self.sub.screen, (95, 190, 255), selection_rect, 2)

        handle = self._selection_handle_rect()
        if handle is not None:
            pygame.draw.rect(self.sub.screen, (245, 245, 245), handle)
            pygame.draw.rect(self.sub.screen, (35, 90, 150), handle, 1)

        scale_x, scale_y = self._view_scale()
        if self.snap_guides["x"] is not None:
            guide_x = round((self.snap_guides["x"] - Game.cam.pos.x) * scale_x)
            pygame.draw.line(
                self.sub.screen,
                (255, 90, 190),
                (guide_x, 0),
                (guide_x, self.rect.height),
                1,
            )
        if self.snap_guides["y"] is not None:
            guide_y = round((self.snap_guides["y"] - Game.cam.pos.y) * scale_y)
            pygame.draw.line(
                self.sub.screen,
                (255, 90, 190),
                (0, guide_y),
                (self.rect.width, guide_y),
                1,
            )

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
            f"{round(self.zoom * 100)}% | F frame | 1/2/3 zoom | middle/Space pan",
            True,
            "white",
        )
        self.sub.screen.blit(
            zoom_label,
            (max(8, self.rect.width - zoom_label.get_width() - 8), 38),
        )
        shortcut_label = self.axis_font.render(
            "Ctrl+D duplicate | arrows nudge | right-click actions",
            True,
            "white",
        )
        self.sub.screen.blit(shortcut_label, (8, 58))

        toolbar_labels = {
            "Move": "Move",
            "Scale": "Scale",
            "Snap": "Snap ON" if self.snap_enabled else "Snap OFF",
            "Smart": "Smart ON" if self.smart_snap_enabled else "Smart OFF",
            "Lines": "Lines ON" if self.grid_visible else "Lines OFF",
            "Grid": f"Grid {self.GridSize} v",
        }
        for label, rect in self.toolbar_rects.items():
            active = label == self.tool or (
                (label == "Snap" and self.snap_enabled)
                or (label == "Smart" and self.smart_snap_enabled)
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

        if self.hovered_toolbar in self.tooltip_hints:
            mouse = Vector2D(*pygame.mouse.get_pos()) - self.sub.get_absolute_pos()
            tooltip_text = self.tooltip_hints[self.hovered_toolbar]
            tooltip = self.axis_font.render(tooltip_text, True, "white")
            tooltip_rect = tooltip.get_rect(
                topleft=(mouse.x + 12, mouse.y + 14)
            )
            tooltip_rect.clamp_ip(self.sub.screen.get_rect())
            background = tooltip_rect.inflate(12, 8)
            pygame.draw.rect(self.sub.screen, Colors["bg"], background)
            pygame.draw.rect(self.sub.screen, (150, 165, 180), background, 1)
            self.sub.screen.blit(tooltip, tooltip_rect)

        selected_object, _ = self._selected_object()
        if selected_object is not None:
            selected_type = self.data["objects"][self.selected_name]["obj_type"]
            selected_count = len(selected_objects)
            count_label = f" +{selected_count - 1}" if selected_count > 1 else ""
            status = f"{self.tool}: {self.selected_name} ({selected_type}){count_label}"
        else:
            status = f"{self.tool}: no object selected"
        max_status_width = max(0, self.rect.width - 16)
        while status and self.axis_font.size(status)[0] > max_status_width:
            status = status[:-1]
        selected_label = self.axis_font.render(status, True, (150, 210, 255))
        self.sub.screen.blit(selected_label, (8, self.rect.height - 22))
        if self.interaction_message:
            message = self.axis_font.render(
                self.interaction_message,
                True,
                (255, 130, 130),
            )
            self.sub.screen.blit(
                message,
                (8, max(8, self.rect.height - 42)),
            )

        if self.context_menu_open:
            menu_rect = self._context_menu_rect()
            pygame.draw.rect(self.sub.screen, Colors["bg"], menu_rect)
            pygame.draw.rect(self.sub.screen, (150, 165, 180), menu_rect, 1)
            mouse = Vector2D(*pygame.mouse.get_pos()) - self.sub.get_absolute_pos()
            for index, action in enumerate(self.context_menu_actions):
                row = pygame.Rect(
                    menu_rect.x,
                    menu_rect.y + index * self.context_menu_row_height,
                    menu_rect.width,
                    self.context_menu_row_height,
                )
                if row.collidepoint(mouse.to_int()):
                    pygame.draw.rect(self.sub.screen, (48, 98, 145), row)
                label = self.axis_font.render(action, True, "white")
                self.sub.screen.blit(label, (row.x + 8, row.y + 6))

        if self.rename_target is not None:
            rename_rect = pygame.Rect(
                max(8, (self.rect.width - 280) // 2),
                max(45, (self.rect.height - 76) // 2),
                280,
                76,
            )
            pygame.draw.rect(self.sub.screen, Colors["bg"], rename_rect)
            pygame.draw.rect(self.sub.screen, (150, 165, 180), rename_rect, 1)
            prompt = self.axis_font.render(
                "Rename object (Ctrl+A, Enter to apply)",
                True,
                "white",
            )
            self.sub.screen.blit(prompt, (rename_rect.x + 8, rename_rect.y + 7))
            entry = pygame.Rect(rename_rect.x + 8, rename_rect.y + 29, rename_rect.width - 16, 22)
            pygame.draw.rect(self.sub.screen, Colors["pannel"], entry)
            self.sub.screen.blit(
                self.axis_font.render(self.rename_buffer, True, "white"),
                (entry.x + 4, entry.y + 3),
            )
            if self.rename_error:
                error = self.axis_font.render(self.rename_error, True, (255, 130, 130))
                self.sub.screen.blit(error, (rename_rect.x + 8, rename_rect.bottom - 15))

        self.sub.render()
