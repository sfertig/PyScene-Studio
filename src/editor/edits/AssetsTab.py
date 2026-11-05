import json
import os
import re
import shutil
import tkinter
from tkinter import filedialog

import pygame
from PyScene import Assets, Game, GameObj, SubScreen, Text, Vector2D

from ...utils.files import ensure_project_assets_dir, get_save_dir_path
from ...utils.load_assets import Colors
from .TabManager import TextInput, btn


ASSET_EXTENSIONS = {
    "image": {".png", ".jpg", ".jpeg", ".bmp", ".gif"},
    "sound": {".wav", ".ogg", ".mp3"},
    "font": {".ttf", ".otf"},
}
ASSET_TYPES = ("image", "animation", "tilemap", "font", "sound")


class AssetsTabEdit(GameObj):
    def __init__(self):
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], Game.screen)
        project_path = os.path.join(get_save_dir_path(), Game.project)
        self.assets_path = ensure_project_assets_dir(project_path)
        self.manifest_path = os.path.join(self.assets_path, "manifest.json")
        if os.path.isfile(self.manifest_path):
            with open(self.manifest_path, "r") as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {"files": [], "definitions": []}
        self.manifest.setdefault("files", [])
        self.manifest.setdefault("definitions", [])

        self.title = self.child(Text(Assets.get_font("default-35"), "Project Assets", "white", Vector2D(10, 5), "topleft", visible=False))
        self.import_button = btn(10, 45, 170, 35, "Import Files", self.sub)
        self.name_input = self.child(TextInput(10, 105, 220, 35, Assets.get_font("default-25"), "", self.sub))
        self.selected_file = None
        self.asset_type = "image"
        self.type_buttons = []
        x = 245
        for asset_type in ASSET_TYPES:
            button = btn(x, 105, 145, 35, asset_type.title(), self.sub, 2, 5, Colors["bg"])
            self.type_buttons.append((asset_type, button))
            x += 150

        self.add_button = btn(10, 290, 170, 35, "Add Definition", self.sub)
        self.fields = []
        self.field_slots = []
        self.field_values = {}
        self._create_fields()
        self.status = self.child(Text(Assets.get_font("default-25"), "", "white", Vector2D(195, 175), "midleft", visible=False))
        self.file_scroll = 0
        self.definition_scroll = 0
        self.refresh_lists()

    def _field_specs(self, asset_type=None):
        if asset_type is None:
            asset_type = self.asset_type
        return {
            "image": (("scale", "Scale", "1.0"), ("crop_x", "Crop X", ""), ("crop_y", "Crop Y", ""), ("crop_w", "Crop W", ""), ("crop_h", "Crop H", "")),
            "animation": (("frame_size", "Frame Size", "16"), ("fps", "FPS", "3"), ("loop", "Loop (true/false)", "true")),
            "tilemap": (("width", "Tile Width", "16"), ("height", "Tile Height", "16"), ("scale", "Scale", "1.0")),
            "font": (("size", "Font Size", "24"),),
            "sound": (),
        }[asset_type]

    def _create_fields(self):
        if not self.field_slots:
            for index in range(5):
                x = 10 + index * 205
                label = self.child(Text(Assets.get_font("default-25"), "", "white", Vector2D(x, 215), "topleft", visible=False))
                field = self.child(TextInput(x, 242, 190, 32, Assets.get_font("default-25"), "", self.sub))
                self.field_slots.append((label, field))

        if self.fields:
            self.field_values[self.asset_type] = {
                key: field.text.text for _, field, key in self.fields
            }

        values = self.field_values.get(self.asset_type, {})
        self.fields = []
        specs = self._field_specs()
        for index, (label, field) in enumerate(self.field_slots):
            if index < len(specs):
                key, label_text, default = specs[index]
                x = 10 + index * 205
                label.set_text(label_text)
                label.set_pos(Vector2D(x, 215))
                field._rect.topleft = (x, 242)
                field.active = False
                field.text.set_text(values.get(key, default))
                self.fields.append((label, field, key))
            else:
                label.set_text("")
                field._rect.topleft = (-10000, -10000)
                field.active = False

        self.add_button.pos.y = 290
        self.add_button.rect.y = 290
        self.add_button.text.set_pos(Vector2D(self.add_button.rect.centerx, self.add_button.rect.centery))

    def _save_manifest(self):
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=4)

    def import_files(self):
        root = tkinter.Tk()
        root.withdraw()
        try:
            sources = filedialog.askopenfilenames(
                parent=root,
                title="Import project assets",
                filetypes=(
                    ("Supported assets", "*.png *.jpg *.jpeg *.bmp *.gif *.wav *.ogg *.mp3 *.ttf *.otf"),
                    ("All files", "*.*"),
                ),
            )
        finally:
            root.destroy()

        if not sources:
            return

        imported = []
        unsupported = []
        for source in sources:
            extension = os.path.splitext(source)[1].lower()
            if not any(extension in extensions for extensions in ASSET_EXTENSIONS.values()):
                unsupported.append(os.path.basename(source))
                continue

            filename = os.path.basename(source)
            target = os.path.join(self.assets_path, filename)
            base, extension = os.path.splitext(filename)
            index = 2
            while os.path.exists(target):
                target = os.path.join(self.assets_path, f"{base}_{index}{extension}")
                index += 1

            shutil.copy2(source, target)
            relative_path = os.path.relpath(target, self.assets_path).replace(os.sep, "/")
            if relative_path not in self.manifest["files"]:
                self.manifest["files"].append(relative_path)
            imported.append(relative_path)

        self.manifest["files"].sort()
        self._save_manifest()
        if imported:
            self.selected_file = imported[-1]
            self.name_input.text.set_text(re.sub(r"\W+", "_", os.path.splitext(os.path.basename(self.selected_file))[0]))
            self.status.set_text(f"Imported {len(imported)} file(s).")
            self.refresh_lists()
        elif unsupported:
            self.status.set_text("Unsupported file type: " + ", ".join(unsupported))

    def _set_type(self, asset_type):
        if self.asset_type == asset_type:
            return
        self.asset_type = asset_type
        for current_type, button in self.type_buttons:
            button.pressed = current_type == asset_type
        self._create_fields()

    def _make_options(self):
        values = {key: field.text.text.strip() for _, field, key in self.fields}
        if self.asset_type == "image":
            options = {"scale": float(values["scale"])}
            crop = [values[f"crop_{axis}"] for axis in ("x", "y", "w", "h")]
            if any(crop):
                if not all(crop):
                    raise ValueError("Fill in all four crop fields or leave them blank.")
                options["rect"] = [int(value) for value in crop]
                if options["rect"][0] < 0 or options["rect"][1] < 0 or options["rect"][2] <= 0 or options["rect"][3] <= 0:
                    raise ValueError("Crop position must be non-negative and crop size must be positive.")
            if options["scale"] <= 0:
                raise ValueError("Image scale must be greater than zero.")
        elif self.asset_type == "animation":
            options = {
                "frame_size": int(values["frame_size"]),
                "fps": float(values["fps"]),
                "loop": values["loop"].lower() in ("true", "yes", "1"),
            }
            if values["loop"].lower() not in ("true", "false", "yes", "no", "1", "0"):
                raise ValueError("Loop must be true or false.")
            if options["frame_size"] <= 0 or options["fps"] <= 0:
                raise ValueError("Frame size and FPS must be greater than zero.")
        elif self.asset_type == "tilemap":
            options = {
                "width": int(values["width"]),
                "height": int(values["height"]),
                "scale": float(values["scale"]),
            }
            if options["width"] <= 0 or options["height"] <= 0 or options["scale"] <= 0:
                raise ValueError("Tile dimensions and scale must be greater than zero.")
        elif self.asset_type == "font":
            options = {"size": int(values["size"])}
            if options["size"] <= 0:
                raise ValueError("Font size must be greater than zero.")
        else:
            options = {}
        return options

    def add_definition(self):
        name = self.name_input.text.text.strip()
        if not name.isidentifier():
            raise ValueError("Asset name must be a valid Python identifier.")
        if not self.selected_file or self.selected_file not in self.manifest["files"]:
            raise ValueError("Select an imported asset file first.")
        if any(definition["name"] == name for definition in self.manifest["definitions"]):
            raise ValueError(f"An asset named {name!r} already exists.")

        extension = os.path.splitext(self.selected_file)[1].lower()
        if extension not in ASSET_EXTENSIONS[self.asset_type if self.asset_type in ("image", "font", "sound") else "image"]:
            raise ValueError(f"{self.selected_file} is not a supported {self.asset_type} source.")

        definition = {
            "name": name,
            "type": self.asset_type,
            "file": self.selected_file,
            "options": self._make_options(),
        }
        self.manifest["definitions"].append(definition)
        self._save_manifest()
        self.status.set_text(f"Added {self.asset_type}: {name}")
        self.refresh_lists()

    def refresh_lists(self):
        self.files = []
        for filename in self.manifest["files"]:
            self.files.append(filename)
        self.file_delete_buttons = [
            btn(0, 0, 85, 26, "Delete", self.sub, -1, 5, (120, 35, 35))
            for _ in self.files
        ]
        self.definitions = list(self.manifest["definitions"])
        self.definition_delete_buttons = [
            btn(0, 0, 85, 26, "Remove", self.sub, -1, 5, (120, 35, 35))
            for _ in self.definitions
        ]

    def remove_definition(self, index):
        definition = self.manifest["definitions"].pop(index)
        self._save_manifest()
        self.status.set_text(f"Removed {definition['name']}.")
        self.refresh_lists()

    def delete_file(self, index):
        filename = self.files[index]
        asset_path = os.path.abspath(
            os.path.join(self.assets_path, filename.replace("/", os.sep))
        )
        assets_root = os.path.abspath(self.assets_path)
        try:
            is_inside_assets = os.path.commonpath((assets_root, asset_path)) == assets_root
        except ValueError:
            is_inside_assets = False
        if not is_inside_assets:
            raise ValueError(f"Asset path is outside the project assets directory: {filename!r}")

        if os.path.isfile(asset_path):
            os.remove(asset_path)

        removed_definitions = [
            definition for definition in self.manifest["definitions"]
            if definition.get("file") == filename
        ]
        self.manifest["definitions"] = [
            definition for definition in self.manifest["definitions"]
            if definition.get("file") != filename
        ]
        self.manifest["files"].remove(filename)
        self._save_manifest()

        if self.selected_file == filename:
            self.selected_file = None
        self.refresh_lists()
        message = f"Deleted {filename}."
        if removed_definitions:
            message += f" Removed {len(removed_definitions)} definition(s)."
        self.status.set_text(message)

    def update(self):
        self.import_button.update()
        if self.import_button.pressed:
            self.import_files()

        for asset_type, button in self.type_buttons:
            button.update()
            if button.pressed and self.asset_type != asset_type:
                self._set_type(asset_type)

        self.name_input.update()
        for _, field, _ in self.fields:
            field.update()
        self.add_button.update()
        if self.add_button.pressed:
            try:
                self.add_definition()
            except (ValueError, KeyError) as error:
                self.status.set_text(str(error))

        mouse_pos = self.sub.local_mouse_pos().to_int()
        if Game.click:
            file_area = pygame.Rect(10, 350, 480, self.size.y - 360)
            if file_area.collidepoint(mouse_pos):
                row = (mouse_pos[1] - file_area.y + self.file_scroll) // 30
                if 0 <= row < len(self.files):
                    file_button = self.file_delete_buttons[row]
                    file_y = 375 + row * 30 - self.file_scroll
                    file_button.pos = Vector2D(400, file_y - 3)
                    file_button.rect.topleft = file_button.pos.to_int()
                    file_button.update()
                    if file_button.pressed:
                        self.delete_file(row)
                        Game.click = False
                    elif mouse_pos[0] < 400:
                        self.selected_file = self.files[row]
                        stem = os.path.splitext(os.path.basename(self.selected_file))[0]
                        self.name_input.text.set_text(re.sub(r"\W+", "_", stem))
                        self.status.set_text(f"Selected {self.selected_file}")
                        Game.click = False

            for index, button in enumerate(self.definition_delete_buttons):
                button.update()
                if button.pressed:
                    self.remove_definition(index)
                    break

        for event in Game.events:
            if event.type == pygame.MOUSEWHEEL:
                if pygame.Rect(10, 350, 480, self.size.y - 360).collidepoint(mouse_pos):
                    self.file_scroll = max(0, min(
                        self.file_scroll - event.y * 30,
                        max(0, len(self.files) * 30 - (self.size.y - 360)),
                    ))
                elif pygame.Rect(510, 350, self.size.x - 520, self.size.y - 360).collidepoint(mouse_pos):
                    self.definition_scroll = max(0, min(
                        self.definition_scroll - event.y * 30,
                        max(0, len(self.definitions) * 36 - (self.size.y - 360)),
                    ))

    def render(self):
        self.sub.clear()
        self.title.render_to(self.sub.screen)
        pygame.draw.line(self.sub.screen, "black", (5, 38), (self.size.x - 5, 38))
        self.import_button.render()
        self.name_input.render()
        for asset_type, button in self.type_buttons:
            button.color = Colors["pannel"] if asset_type == self.asset_type else Colors["bg"]
            button.render()
        for label, field, _ in self.fields:
            label.render_to(self.sub.screen)
            field.render()
        self.add_button.render()
        self.status.render_to(self.sub.screen)

        pygame.draw.rect(self.sub.screen, Colors["bg"], (10, 340, 480, self.size.y - 350))
        pygame.draw.rect(self.sub.screen, Colors["bg"], (500, 340, self.size.x - 510, self.size.y - 350))
        pygame.draw.line(self.sub.screen, "black", (500, 340), (500, self.size.y - 10), 1)
        self.sub.screen.blit(Assets.get_font("default-25").render("Imported files", True, "white"), (20, 345))
        self.sub.screen.blit(Assets.get_font("default-25").render("Asset definitions", True, "white"), (515, 345))

        for index, filename in enumerate(self.files):
            y = 375 + index * 30 - self.file_scroll
            if 350 <= y < self.size.y:
                color = (255, 220, 120) if filename == self.selected_file else "white"
                file_font = Assets.get_font("default-25")
                label = filename
                max_width = 365
                while label and file_font.size(label)[0] > max_width:
                    label = label[:-1]
                if label != filename:
                    while label and file_font.size(label + "...")[0] > max_width:
                        label = label[:-1]
                    label += "..."
                self.sub.screen.blit(file_font.render(label, True, color), (20, y))
                button = self.file_delete_buttons[index]
                button.pos = Vector2D(400, y - 3)
                button.rect.topleft = button.pos.to_int()
                button.text.set_pos(Vector2D(button.rect.centerx, button.rect.centery))
                button.render()

        for index, (definition, button) in enumerate(zip(self.definitions, self.definition_delete_buttons)):
            y = 375 + index * 36 - self.definition_scroll
            if 350 <= y < self.size.y:
                details = f"{definition['name']}  [{definition['type']}]  <- {definition['file']}"
                self.sub.screen.blit(Assets.get_font("default-25").render(details, True, "white"), (515, y))
                button.pos = Vector2D(self.size.x - 105, y - 3)
                button.rect.topleft = button.pos.to_int()
                button.text.set_pos(Vector2D(button.rect.centerx, button.rect.centery))
                button.render()

        self.sub.render()

    def save(self):
        self._save_manifest()
