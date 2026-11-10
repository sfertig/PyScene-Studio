import queue
import threading

from PyScene import *
import pygame
import json

from ...utils.load_assets import Colors
from ...utils.files import *

from ...Export import export_web, export_windows
from .scenes.Inputs import ColorInput
from .TabManager import btn, TextInput


class SettingsTabEdit(GameObj):
    def __init__(self):
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], Game.screen)
        self.title = self.child(Text(Assets.get_font("default-35"), "Settings:", "white", Vector2D(10, 5), "topleft", visible=False))

        self.rename = self.child(Rename(5, 40, 300, 200, self.sub))
        self.win = self.child(Window(5, 245, 400, 400, self.sub))
        self.export = self.child(ExportPanel(430, 40, 520, 400, self.sub, self.win))

    def update(self):
        self.rename.update()
        self.win.update()
        self.export.update()

    def render(self):
        self.sub.clear()
        self.title.render_to(self.sub.screen)
        pygame.draw.line(self.sub.screen, "black", (5, 35), (self.size.x-5, 35))

        self.rename.render()
        self.win.render()
        self.export.render()

        self.sub.render()

    def save(self):
        self.win.save()
        self.export.save()

class Rename(GameObj):
    def __init__(self, x, y, w, h, sub):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen
        self._rect = pygame.Rect(0, 0, w, h)
        self.title = self.child(Text(Assets.get_font("default-35"), "Rename", "white", Vector2D(self.size.x/2, 20), visible=False))

        self.box = self.child(TextInput(10, 50, self.size.x-20, 30, Assets.get_font("default-25"), "", self.sub))
        self.accept = btn(self.size.x/2-50, self.size.y-50, 100, 30, "Accept", self.sub)
    def update(self):
        self.box.update()
        if self.box.text != "" and not self.box.active:
            self.box.text.set_text(check_name(self.box.text.text)) 
        self.accept.update()
        if self.accept.pressed and self.box.text != "": 
            new = self.box.text.text
            old = Game.project
            #check if folder name is already in use in another project
            if new in gen_project_lists().keys():
                self.box.text.set_text("")
                return
            elif new == old:
                return
            Game.project = new
            #rename the folder
            os.rename(get_save_dir_path()+"/"+old, get_save_dir_path()+"/"+new)
            self.box.text.set_text("")
            Game.RENAMETITLE = True
            #rename project file name
            with open(get_save_dir_path()+"/"+Game.project+"/project.json", "r") as f:
                data = json.load(f)
                data["project_name"] = Game.project
            with open(get_save_dir_path()+"/"+Game.project+"/project.json", "w") as f:
                json.dump(data, f, indent=4)

            print("[Settings] - Project Renamed from "+old+" to "+Game.project)

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.screen, Colors["b"], self._rect, 2)
        self.title.render_to(self.sub.screen)
        self.box.render()
        self.accept.render()
        self.sub.render()

class Window(GameObj):
    def __init__(self, x, y, w, h, sub):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen
        self._rect = pygame.Rect(0, 0, w, h)
        self.title = self.child(Text(Assets.get_font("default-35"), "Window Attributes", "white", Vector2D(self.size.x/2, 20), visible=False))

        with open(get_save_dir_path()+"/"+Game.project+"/project.json", "r") as f:
            data = json.load(f)

        #win name
        self.winTitle = self.child(Text(Assets.get_font("default-25"), "Window Name:", "white", Vector2D(5, 50), "topleft", visible=False))
        self.winName = self.child(TextInput(10, 80, self.size.x-20, 30, Assets.get_font("default-25"), data["window"]["title"], self.sub))
        #dimentions
        self.widthTitle = self.child(Text(Assets.get_font("default-25"), "Width:", "white", Vector2D(5, 130), "topleft", visible=False))
        self.heightTitle = self.child(Text(Assets.get_font("default-25"), "Height:", "white", Vector2D(5, 160), "topleft", visible=False))
        self.width = self.child(TextInput(60, 125, 100, 30, Assets.get_font("default-25"), str(data["window"]["width"]), self.sub))
        self.height = self.child(TextInput(60, 155, 100, 30, Assets.get_font("default-25"), str(data["window"]["height"]), self.sub))
        #fullscreen
        self.fullText = self.child(Text(Assets.get_font("default-25"), "Fullscreen:", "white", Vector2D(175, 130), "topleft", visible=False))
        r = pygame.Rect(270, 130, 25, 25)
        _r = self.sub.get_global_rect(r)
        self.fullBtn = btn(r.x, r.y, r.width, r.height, "", self.sub, 1, 0, toggle=True, _rect=_r)
        self.fullBtn.pressed = data["window"]["fullscreen"]
        #fps
        self.fpsText = self.child(Text(Assets.get_font("default-25"), "FPS:", "white", Vector2D(5, 200), "topleft", visible=False))
        self.fps = self.child(TextInput(60, 200, 100, 30, Assets.get_font("default-25"), str(data["window"]["fps"]), self.sub))

        self.bgColorText = self.child(Text(Assets.get_font("default-25"), "Background Color:", "white", Vector2D(5, 245), "topleft", visible=False))
        raw_color = data["window"]["bg_color"]
        color = pygame.Color(raw_color) if isinstance(raw_color, str) else pygame.Color(*raw_color)
        self.bgColor = self.child(ColorInput(10, 275, 370, 30, list(color)[:3], self.sub))

        self.splashText = self.child(Text(
            Assets.get_font("default-25"),
            "Include Splashscreen:",
            "white",
            Vector2D(5, 330),
            "topleft",
            visible=False,
        ))
        splash_rect = pygame.Rect(270, 325, 25, 25)
        self.splashBtn = btn(
            splash_rect.x,
            splash_rect.y,
            splash_rect.width,
            splash_rect.height,
            "",
            self.sub,
            1,
            0,
            toggle=True,
            _rect=self.sub.get_global_rect(splash_rect),
        )
        self.splashBtn.pressed = data.get("include_splashscreen", False)

    def update(self):
        self.winTitle.update()
        self.winName.update()

        self.widthTitle.update()
        self.heightTitle.update()
        self.width.update()
        self.height.update()
        

        self.fullText.update()
        self.fullBtn.update()

        self.fpsText.update()
        self.fps.update()
        self.bgColorText.update()
        self.bgColor.update()
        self.splashText.update()
        self.splashBtn.update()
        
        self.format_dims()

    def save(self):
        #save title
        with open(get_save_dir_path()+"/"+Game.project+"/project.json", "r") as f:
            data = json.load(f)

        data["window"]["title"] = self.winName.text.text
        self.format_dims()
        data["window"]["width"] = int(self.width.text.text)
        data["window"]["height"] = int(self.height.text.text)
        data["window"]["fullscreen"] = self.fullBtn.pressed
        data["window"]["fps"] = int(self.fps.text.text)
        data["window"]["bg_color"] = self.bgColor.get_value()
        data["include_splashscreen"] = self.splashBtn.pressed


        with open(get_save_dir_path()+"/"+Game.project+"/project.json", "w") as f:
            json.dump(data, f, indent=4)

    def format_dims(self):
        #make dimentions only numbers
        width = self.width.text.text
        height = self.height.text.text
        for char in width:
            if not char.isdigit():
                width = width.replace(char, "")
        for char in height:
            if not char.isdigit():
                height = height.replace(char, "")
        self.width.text.set_text(width)
        self.height.text.set_text(height)

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.screen, Colors["b"], self._rect, 2)
        self.title.render_to(self.sub.screen)
        pygame.draw.line(self.sub.screen, "black", (5, 35), (self.size.x-5, 35))

        self.winTitle.render_to(self.sub.screen)
        self.winName.render()
        pygame.draw.line(self.sub.screen, "black", (5, 75), (self.size.x-5, 75))

        self.widthTitle.render_to(self.sub.screen)
        self.heightTitle.render_to(self.sub.screen)
        self.width.render()
        self.height.render()
        pygame.draw.line(self.sub.screen, "black", (5, 115), (self.size.x-5, 115))

        self.fullText.render_to(self.sub.screen)
        self.fullBtn.render()
        pygame.draw.line(self.sub.screen, "black", (5, 190), (self.size.x-5, 190))

        self.fpsText.render_to(self.sub.screen)
        self.fps.render()
        self.bgColorText.render_to(self.sub.screen)
        self.bgColor.render()
        self.splashText.render_to(self.sub.screen)
        self.splashBtn.render()

        self.sub.render()


class ExportPanel(GameObj):
    def __init__(self, x, y, w, h, parent, window_settings):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        self.window_settings = window_settings
        self.sub = SubScreen(x, y, w, h, Colors["bg"], parent.screen, parent)
        self.rect = pygame.Rect(0, 0, w, h)
        self.title = self.child(Text(
            Assets.get_font("default-35"),
            "Export",
            "white",
            Vector2D(w / 2, 20),
            visible=False,
        ))
        self.windows = btn(20, 75, 220, 40, "Export Windows", self.sub)
        self.web = btn(260, 75, 220, 40, "Export Web", self.sub)
        self.windowed_text = self.child(Text(
            Assets.get_font("default-25"),
            "Use --windowed (hide console):",
            "white",
            Vector2D(20, 145),
            "topleft",
            visible=False,
        ))
        toggle_rect = pygame.Rect(360, 135, 25, 25)
        self.windowed = btn(
            toggle_rect.x,
            toggle_rect.y,
            toggle_rect.width,
            toggle_rect.height,
            "",
            self.sub,
            1,
            0,
            toggle=True,
            _rect=self.sub.get_global_rect(toggle_rect),
        )
        self.status = self.child(Text(
            Assets.get_font("default-25"),
            "Choose an export target.",
            "white",
            Vector2D(20, 215),
            "topleft",
            visible=False,
        ))
        self.results: queue.Queue[str] = queue.Queue()
        self.exporting = False

        with open(os.path.join(get_save_dir_path(), Game.project, "project.json"), "r") as f:
            project = json.load(f)
        self.windowed.pressed = project.get("export", {}).get("windows_windowed", True)

    def update(self):
        while not self.results.empty():
            message = self.results.get_nowait()
            self.exporting = False
            self.status.set_text(message)

        if self.exporting:
            return

        self.windows.update()
        self.web.update()
        self.windowed.update()
        if self.windows.pressed:
            self._start_export("windows")
        elif self.web.pressed:
            self._start_export("web")

    def _start_export(self, target):
        self.window_settings.save()
        self.save()
        self.exporting = True
        self.status.set_text(f"Exporting {target}; this may take a while...")
        project_name = Game.project
        windowed = self.windowed.pressed

        def run_export():
            try:
                if target == "windows":
                    output_path = export_windows(project_name, windowed)
                else:
                    output_path = export_web(project_name)
                self.results.put(f"Export complete: {output_path}")
            except Exception as error:
                print(f"[Export Error] - {error}")
                self.results.put(f"Export failed: {error}")

        threading.Thread(target=run_export).start()

    def save(self):
        path = os.path.join(get_save_dir_path(), Game.project, "project.json")
        with open(path, "r") as f:
            project = json.load(f)
        project.setdefault("export", {})["windows_windowed"] = self.windowed.pressed
        with open(path, "w") as f:
            json.dump(project, f, indent=4)

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Colors["b"], self.rect, 2)
        pygame.draw.line(self.sub.screen, "black", (5, 35), (self.size.x - 5, 35))
        self.title.render_to(self.sub.screen)
        self.windows.render()
        self.web.render()
        self.windowed_text.render_to(self.sub.screen)
        self.windowed.render()
        self.status.render_to(self.sub.screen)
        self.sub.render()
