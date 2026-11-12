import copy
import os
import tempfile
import time

import colorsys

from PyScene import *
import PyScene
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn

from .Inputs import *
from .Objs import *
from .Create import *
from .VisualPannel import VisualEditor
from ..objs.LeftPannel import LeftPannel
from ..objs.CodePannel import CodePannel

class VisualSceneTabEdit(GameObj):
    def __init__(self, name):
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], Game.screen)
        self.name = name

        project_path = os.path.join(get_save_dir_path(), Game.project)
        self.scene_path = os.path.join(project_path, "scenes", f"{self.name}.json")
        self.autosave_dir = os.path.join(project_path, "scenes", ".autosave")
        self.autosave_path = os.path.join(self.autosave_dir, f"{self.name}.json")
        with open(self.scene_path, "r") as f:
            self.data: dict = json.load(f)
        self.last_saved_state = copy.deepcopy(self.data)
        self.recovered_autosave = False
        if (
            os.path.isfile(self.autosave_path)
            and os.path.getmtime(self.autosave_path) > os.path.getmtime(self.scene_path)
        ):
            with open(self.autosave_path, "r") as f:
                self.data = json.load(f)
            self.recovered_autosave = True
        self.last_autosave_state = copy.deepcopy(self.data)
        self.autosave_interval = 10
        self.autosave_check_interval = 1
        self.last_autosave_time = time.monotonic()
        self.last_save_check_time = 0
        self.save_status_text = (
            "Recovered autosave" if self.recovered_autosave else "Saved"
        )
        self.save_status_color = (
            (255, 210, 110) if self.recovered_autosave else (160, 220, 160)
        )

        self.script_mode = False
        self.mode_btn = btn(
            (self.size.x - 200) // 2,
            0,
            200,
            30,
            "Visual Mode",
            self.sub,
            -1,
            5,
            Colors["pannel"],
        )
        self.script_left = self.child(LeftPannel(self.sub, self.data))
        self.script_code_sub = SubScreen(
            420,
            0,
            self.size.x - 420,
            self.size.y,
            Colors["pannel"],
            self.sub.screen,
            self.sub,
        )
        self.script_code_title = self.child(
            Text(
                Assets.get_font("default-35"),
                "__init__",
                "white",
                Vector2D(self.script_code_sub.dim.x // 2, 50),
                visible=False,
            )
        )
        self.script = self.child(
            CodePannel(
                self.script_code_sub,
                self.data,
                pos=Vector2D(10, 80),
                height=self.size.y - 90,
            )
        )
        self.gen()
        self.undo_stack = []
        self.redo_stack = []
        self.history_limit = 100
        self.history_restore = False
        self.history_state = copy.deepcopy(self.data["objects"])

    def gen(self):
        #components

        self.r = pygame.Rect(self.sub.dim.x-400, 35, 400, self.sub.dim.y-35)
        self.test = pygame.Rect(420, 35, self.sub.dim.x-840, self.sub.dim.y-35)
        self.objs = self.child(ObjectsMenue(self.name, self.data, self.sub))
        self.create = self.child(CreateObj(self.sub, self.data.copy(), self.test))
        self.visual_editor = self.child(
            VisualEditor(self.test, self.sub, self.data)
        )
        self.objs.visual_editor = self.visual_editor

    def save(self):
        self.objs.save()
        self.script.save()
        current_state = copy.deepcopy(self.data["objects"])
        if not self.history_restore and current_state != self.history_state:
            self.undo_stack.append(self.history_state)
            if len(self.undo_stack) > self.history_limit:
                self.undo_stack.pop(0)
            self.redo_stack.clear()
        self.history_state = current_state
        save_source_json(self.data, self.scene_path)
        if os.path.isfile(self.autosave_path):
            os.remove(self.autosave_path)
        self.last_saved_state = copy.deepcopy(self.data)
        self.last_autosave_state = copy.deepcopy(self.data)
        self.recovered_autosave = False
        self.save_status_text = "Saved"
        self.save_status_color = (160, 220, 160)

    @staticmethod
    def _source_snapshot(data):
        return {key: value for key, value in data.items() if key != "dirty"}

    def _write_autosave(self, snapshot):
        os.makedirs(self.autosave_dir, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.autosave_dir,
                prefix=f".{self.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = temporary_file.name
                json.dump(snapshot, temporary_file, indent=4)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.autosave_path)
            temporary_path = None
        finally:
            if temporary_path is not None and os.path.exists(temporary_path):
                os.remove(temporary_path)

    def update_save_confidence(self):
        now = time.monotonic()
        if now - self.last_save_check_time < self.autosave_check_interval:
            return
        self.last_save_check_time = now
        self.objs.save()
        if self.script_mode:
            self.script.save()
        snapshot = copy.deepcopy(self.data)
        if self._source_snapshot(snapshot) == self._source_snapshot(self.last_saved_state):
            self.save_status_text = "Saved"
            self.save_status_color = (160, 220, 160)
            return

        if self._source_snapshot(snapshot) == self._source_snapshot(self.last_autosave_state):
            self.save_status_text = (
                "Recovered autosave"
                if self.recovered_autosave
                else "Autosaved"
            )
            self.save_status_color = (150, 200, 255)
            return

        self.save_status_text = "Unsaved"
        self.save_status_color = (255, 190, 100)
        if (
            (
                not os.path.isfile(self.autosave_path)
                or now - self.last_autosave_time >= self.autosave_interval
            )
        ):
            self._write_autosave(snapshot)
            self.last_autosave_state = snapshot
            self.last_autosave_time = now
            self.save_status_text = "Autosaved"
            self.save_status_color = (150, 200, 255)

    def apply_history(self, undo=True):
        source = self.undo_stack if undo else self.redo_stack
        destination = self.redo_stack if undo else self.undo_stack
        if not source:
            return

        destination.append(copy.deepcopy(self.data["objects"]))
        if len(destination) > self.history_limit:
            destination.pop(0)
        restored_state = source.pop()
        self.history_restore = True
        try:
            self.data["objects"].clear()
            self.data["objects"].update(copy.deepcopy(restored_state))
            self.objs.reload()
            self.create.data = self.data["objects"].copy()
            self.visual_editor.selected_names.intersection_update(self.data["objects"])
            if self.visual_editor.selected_name not in self.data["objects"]:
                self.visual_editor.selected_name = next(
                    iter(self.visual_editor.selected_names),
                    None,
                )
            self.visual_editor.preview_signature = None
            self.save()
        finally:
            self.history_restore = False

    def update(self):
        self.mode_btn.update()
        if any(
            event.type == pygame.KEYDOWN
            and event.key == pygame.K_s
            and getattr(event, "mod", 0) & pygame.KMOD_CTRL
            for event in Game.events
        ):
            self.save()
        if self.mode_btn.pressed:
            self.script_mode = not self.script_mode
            self.mode_btn.text.set_text(
                "Script Mode" if self.script_mode else "Visual Mode"
            )
            self.save()

        if self.script_mode:
            self.script_left.update()
            if self.script_left.OPEN is not None:
                self.script_code_title.set_text(self.script_left.OPEN)
            self.script.update(self.script_left.OPEN)
            self.update_save_confidence()
            return

        if self.create.update():
            self.data["objects"] = self.create.data.copy()
            self.gen()
            self.save()
            return

        self.visual_editor.update()
        if self.visual_editor.refresh_object_list:
            self.objs.reload()
            self.create.data = self.data["objects"].copy()
            self.visual_editor.refresh_object_list = False
        if self.visual_editor.history_action is not None:
            self.apply_history(
                undo=self.visual_editor.history_action == "undo"
            )
            self.visual_editor.history_action = None
        elif self.visual_editor.needs_save:
            self.save()
            self.visual_editor.needs_save = False

        if self.objs.update():
            self.gen()
            self.save()
            return
        self.update_save_confidence()

    def print_dict(self, data): #debug func
        for k, v in data.items():
            print(k, v)
            print("\n")

    def render(self):
        self.sub.clear()

        if self.script_mode:
            pygame.draw.rect(self.sub.screen, Colors["pannel"], (0, 0, 400, self.size.y))
            self.script_left.render()
            self.script_code_sub.clear()
            self.script_code_title.render_to(self.script_code_sub.screen)
            pygame.draw.line(
                self.script_code_sub.screen,
                "black",
                (10, 75),
                (self.script_code_sub.dim.x - 10, 75),
            )
            self.script.render()
            self.script_code_sub.render()
        else:
            pygame.draw.rect(self.sub.screen, Colors["pannel"], self.r)
            self.visual_editor.render()
            #pygame.draw.rect(self.sub.screen, Colors["pannel"], self.test)
            self.objs.render()
            self.create.render()

        self.mode_btn.render()
        save_status = Assets.get_font("default-25").render(
            self.save_status_text,
            True,
            self.save_status_color,
        )
        self.sub.screen.blit(
            save_status,
            (
                max(8, self.size.x - save_status.get_width() - 12),
                7,
            ),
        )
        self.sub.render()
