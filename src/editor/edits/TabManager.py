from PyScene import *
import pygame
import json
import copy
import keyword

from ...utils.load_assets import Colors
from ...utils.files import *

class TabManagerEdit(GameObj):
    def __init__(self, tabs):
        super().__init__(Vector2D(Game._usableEdit.x, Game._usableEdit.y), 0)
        self.size = Vector2D(Game._usableEdit.width, Game._usableEdit.height)
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["pannel"], Game.screen)
        self.tabs = tabs

        #children
        self.scenes = self.child(Display(5, self.sub, tabs, "scene", "Scenes:"))
        self.objs = self.child(Display(425, self.sub, tabs, "object", "Objects:"))

        self.create_scene = self.child(Create(Vector2D(845, 345), self.sub, tabs, "scene"))
        self.create_obj = self.child(Create(Vector2D(845, 25), self.sub, tabs, "object"))

    def update(self):
        self.scenes.update()
        self.objs.update()

        self.create_scene.update()
        self.create_obj.update()
        if self.create_scene.GEN: self.scenes.gen()
        if self.create_obj.GEN: self.objs.gen()

    def render(self):
        self.sub.clear()

        self.scenes.render()
        self.objs.render()

        self.create_scene.render()
        self.create_obj.render()
        
        self.sub.render()

class Create(GameObj):
    def __init__(self, pos: Vector2D, sub: SubScreen, tabs, name):
        super().__init__(pos, visible=False, active=False)
        self.PSub = sub
        self.tabs = tabs
        self.GEN = False

        self.size = Vector2D(400, 300)
        self.sub = SubScreen(pos.x, pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen
        self.title = self.child(Text(Assets.get_font("default-35"), f"Create New {name}:", "white", Vector2D(5, 5), "topleft", visible=False))

        self._name = name
        self._name_ = f"_{name}_"
        self.id = name
        self.name = self.child(TextInput(5, 50, self.size.x-10, 30, Assets.get_font("default-25"), "", self.sub))
        self.scene_templates = (
            "Empty",
            "Platformer",
            "Menu / UI",
            "Duplicate Existing",
        )
        self.template_index = 0
        self.template_button = btn(
            5,
            100,
            self.size.x - 10,
            32,
            "Template: Empty",
            self.sub,
        )
        self.source_scene_names = self._available_scene_names()
        self.source_scene_index = 0
        self.source_button = btn(
            5,
            145,
            self.size.x - 10,
            32,
            "Source: main",
            self.sub,
        )
        self._update_source_button()
        self.status = self.child(
            Text(
                Assets.get_font("default-25"),
                "",
                (255, 150, 150),
                Vector2D(5, 195),
                "topleft",
                visible=False,
            )
        )
        self.create = btn(self.size.x/2-50, self.size.y-50, 100, 50, "Create", self.sub, -1, 2, Colors["b"])
        self.child(self.create.text)

    def update(self):
        self.GEN = False
        self.name.update()
        if self._name == "scene":
            self.template_button.update()
            if self.template_button.pressed:
                self.template_index = (
                    self.template_index + 1
                ) % len(self.scene_templates)
                self.template_button.text.set_text(
                    f"Template: {self.scene_templates[self.template_index]}"
                )
            if self.scene_templates[self.template_index] == "Duplicate Existing":
                self.source_button.update()
                if self.source_button.pressed and self.source_scene_names:
                    self.source_scene_index = (
                        self.source_scene_index + 1
                    ) % len(self.source_scene_names)
                    self._update_source_button()
        self.create.update()
        if self.create.pressed:
            name = self.name.text.text
            if not name:
                self.status.set_text("Enter a name.")
                return
            if not name.isidentifier() or keyword.iskeyword(name):
                self.status.set_text("Use a valid Python identifier.")
                return
            try:
                if self.check_exists(name):
                    self.status.set_text(f"{self._name.title()} already exists.")
                    return
                self._create(name)
            except (OSError, ValueError) as error:
                self.status.set_text(str(error))

    def _available_scene_names(self):
        if self._name != "scene":
            return []
        scenes_path = os.path.join(
            get_save_dir_path(),
            Game.project,
            "scenes",
        )
        if not os.path.isdir(scenes_path):
            return []
        return sorted(
            os.path.splitext(filename)[0]
            for filename in os.listdir(scenes_path)
            if filename.endswith(".json")
        )

    def _update_source_button(self):
        if self.source_scene_names:
            source = self.source_scene_names[self.source_scene_index]
            self.source_button.text.set_text(f"Source: {source}")

    def _make_scene_template(self, name):
        template = self.scene_templates[self.template_index]
        if template == "Duplicate Existing":
            self.source_scene_names = self._available_scene_names()
            if not self.source_scene_names:
                raise ValueError("There are no scenes available to duplicate.")
            self.source_scene_index %= len(self.source_scene_names)
            source_path = os.path.join(
                get_save_dir_path(),
                Game.project,
                "scenes",
                f"{self.source_scene_names[self.source_scene_index]}.json",
            )
            with open(source_path, "r") as f:
                data = json.load(f)
            data = copy.deepcopy(data)
            data["name"] = name
            data["dirty"] = False
            return data

        data = copy.deepcopy(DEFAULTSCENE)
        data["name"] = name
        if template == "Empty":
            return data

        project_path = os.path.join(get_save_dir_path(), Game.project)
        with open(os.path.join(project_path, "project.json"), "r") as f:
            project = json.load(f)
        width = project["window"]["width"]
        height = project["window"]["height"]

        def rectangle(x, y, w, h, color, z_index):
            return {
                "obj_type": "Rect",
                "variables": {
                    "x": x,
                    "y": y,
                    "w": w,
                    "h": h,
                    "color": color,
                    "width": 0,
                    "z_index": z_index,
                    "active": True,
                    "visible": True,
                    "offset": True,
                    "Global": False,
                },
            }

        if template == "Platformer":
            data["objects"] = {
                "Ground": rectangle(
                    0,
                    max(0, height - 32),
                    width,
                    32,
                    [70, 180, 110],
                    0,
                ),
                "Player": rectangle(
                    max(0, width // 8),
                    max(0, height - 80),
                    24,
                    32,
                    [80, 150, 255],
                    1,
                ),
            }
            data["functions"]["update"]["code"] = [
                "# Add player movement and collision logic here.",
                "pass",
            ]
        elif template == "Menu / UI":
            data["objects"] = {
                "Background": rectangle(
                    0,
                    0,
                    width,
                    height,
                    [28, 34, 52],
                    0,
                ),
                "MenuPanel": rectangle(
                    width // 4,
                    height // 5,
                    width // 2,
                    height * 3 // 5,
                    [55, 68, 94],
                    1,
                ),
                "StartButton": rectangle(
                    width * 3 // 8,
                    height // 2,
                    width // 4,
                    max(24, height // 9),
                    [70, 150, 105],
                    2,
                ),
            }
            data["functions"]["update"]["code"] = [
                "# Add button input and menu transitions here.",
                "pass",
            ]
        return data

    def _create(self, name):
        #create file
        if self._name == "scene":
            data = self._make_scene_template(name)
        else:
            data = copy.deepcopy(DEFAULTOBJECT)
        data["name"] = name
        data["dirty"] = True
        path = os.path.join(
            get_save_dir_path(),
            Game.project,
            f"{self._name}s",
            f"{name}.json",
        )
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
            print(f"[TabManager] - {self._name} File Created: "+name)
        self.tabs.open_tab(name, self._name_, self.id)
        self.name.text.set_text("")
        self.status.set_text("")
        self.GEN = True


    def check_exists(self, name):
        scenes = os.listdir(get_save_dir_path()+f"/{Game.project}/scenes/")
        objs = os.listdir(get_save_dir_path()+f"/{Game.project}/objects/")
        for s in scenes:
            if s[:-5] == name: return True
        for o in objs:
            if o[:-5] == name: return True
        return False

    def render(self):
        self.sub.clear()

        self.title.render_to(self.sub.screen)
        pygame.draw.line(self.screen, "black", (5, 35), (self.size.x-5, 35))
        self.name.render()
        self.status.render_to(self.sub.screen)
        if self._name == "scene":
            self.template_button.render()
            if self.scene_templates[self.template_index] == "Duplicate Existing":
                self.source_button.render()
        self.create.render()

        self.sub.render()

class Display(GameObj):
    def __init__(self, x, sub: SubScreen, tabs, name, title):
        super().__init__(Vector2D(x, 25), visible=False, active=False)
        self.PSub = sub
        self.tabs = tabs

        self.title = self.child(Text(Assets.get_font("default-35"), title, "white", Vector2D(self.pos.x, 0), "topleft", visible=False))
        self.name = name
        self._name_ = f"_{name}_"

        self.sub = SubScreen(self.pos.x, self.pos.y, 400, sub.dim.y-30, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        #options
        self.op_sub = SubScreen(0, self.sub.dim.y-130, self.sub.dim.x, 130, Colors["bg"], self.screen, self.sub)
        self.op_rect = pygame.Rect(0, 0, self.sub.dim.x, 130)
        self.open = btn(5, 5, 100, 30, "Open", self.op_sub, 2)
        self.child(self.open.text)
        self.delete = btn(5, 50, 275, 30, "Delete (hover and press enter)", self.op_sub, -1, 0, (255, 0, 0))
        self.child(self.delete.text)
        self.show_options = False

        #load / create scenes
        self.scenes: list[btn] = []
        self.gen()

    def gen(self):
        for scene in self.scenes:
            scene.text.destroy()
        self.scenes.clear()
        y = 5
        w = self.sub.dim.x-20
        pos = self.sub.get_absolute_pos()
        rect = pygame.Rect(pos.x, pos.y, self.sub.dim.x, self.sub.dim.y-130)
        for file in os.listdir(get_save_dir_path()+f"/{Game.project}/{self.name}s/"):
            if file.endswith(".json"):
                name = file[:-5]
                self.scenes.append(btn(10, y, w, 40, name, self.sub, -1, 3, Colors["pannel"], True, rect))
                y += 50
                self.child(self.scenes[-1].text)


    def update(self):
        self.open.update()
        self.delete.update()

        self.show_options = False
        for s in self.scenes.copy():
            s.update()
            if s.pressed: self.show_options = True

        for s in self.scenes.copy():
            if s.pressed and self.check_open(s):
                return

    def check_open(self, scene):
        if scene.pressed and self.open.pressed:
            name = scene.text.text
            self.tabs.open_tab(name, self._name_, self.name)
            return False
        elif scene.pressed and self.delete.hovered and Keys.is_pressed(Keys.enter):
            name = scene.text.text
            if self.name == "scene" and name == "main":
                return False
            for tab in self.tabs.tabs.copy():
                if hasattr(tab, self._name_): 
                    if tab._name == name:
                        self.tabs.close_tab(tab)
            os.remove(get_save_dir_path()+f"/{Game.project}/{self.name}s/{name}.json")
            print(f"[TabManager] - {self.name} Deleted: "+name)
            self.gen()
            return True
        return False


    def render(self):
        self.sub.clear()

        self.title.render_to(self.PSub.screen)

        for s in self.scenes: s.render()

        #options
        if self.show_options:
            self.op_sub.clear()
            pygame.draw.rect(self.op_sub.screen, Colors["b"], self.op_rect, 2)
            self.open.render()
            self.delete.render()
            self.op_sub.render()

        self.sub.render()

class btn():
    def __init__(self, x, y, w, h, text, sub, min_w=-1, max_w=5, color=Colors["b"], toggle=False, _rect=None):
        self.pos = Vector2D(x, y)
        self.size = Vector2D(w, h)
        self.rect = pygame.Rect(self.pos.to_int(), self.size.to_int())
        self.text = Text(Assets.get_font("default-25"), text, "white", Vector2D(self.rect.centerx, self.rect.centery), visible=False)
        self.sub: SubScreen = sub

        self._r = _rect
        self.min_w = min_w
        self.max_w = max_w
        self.w = min_w
        self.hovered = False
        self.pressed = False
        self.toggle = toggle
        self.color = color

    def update(self):
        if not self.toggle: self.pressed = False
        mpos = self.sub.local_mouse_pos().to_int()
        #self.mpos = mpos
        self.hovered = self.rect.collidepoint(mpos)
        if self.hovered: self.w = self.max_w
        else: self.w = self.min_w

        if self.toggle and self.pressed: self.w = self.max_w

        if not self.toggle: 
            if Game.click and self.hovered:
                self.pressed = True
        else:
            # Handles the toggle logic properly
            #if Game.click: print(f"checking: mpos: {pygame.mouse.get_pos()}, hit: {self._r.collidepoint(pygame.mouse.get_pos())}, hovered: {self.hovered}, pressed: {self.pressed}")
            if Game.click and self._r.collidepoint(pygame.mouse.get_pos()):
                if self.hovered and not self.pressed:
                    self.pressed = True  # Flips between True and False
                elif self.hovered and self.pressed:
                    self.pressed = False
                elif self.pressed:
                    self.pressed = False             # Turns off if clicking anywhere else


    def render(self):
        pygame.draw.rect(self.sub.screen, self.color, self.rect, self.w)
        self.text.render_to(self.sub.screen)
        #pygame.draw.circle(self.sub.screen, "yellow", self.mpos, 3)
        #if self._r: pygame.draw.rect(self.sub.screen, self.color, self._r, 2)

class TextInput(GameObj):
    def __init__(self, x, y, w, h, font, text="", sub=None, _input=True):
        super().__init__(Vector2D(x, y), visible=False, active=False)
        self.size = Vector2D(w, h)
        s = Game.screen
        if sub: s = sub.screen
        self.sub = SubScreen(x, y, w, h, Colors["bg"], s, sub)
        self.PSub = sub
        self.rect = pygame.Rect((0, 0), self.size.to_int())
        self._rect = pygame.Rect(x, y, w, h)
        self.w = 2
        self.text = Text(font, text, "white", Vector2D(self.rect.centerx, self.rect.centery), "center", 5, visible=False)
        self.active = False
        self.hovered = False

        self.buffer = 0
        self._input = _input

        self.child(self.text)

    def update(self):
        self.buffer -= 1
        if self.buffer < 0: self.buffer = 0
        mpos = self.PSub.local_mouse_pos().to_int()
        self.hovered = self._rect.collidepoint(mpos)
        if not self.active:
            if self.hovered: self.w = 5
            else: self.w = 2

        if Game.click:
            if not self.hovered:
                self.active = False
            else:
                self.active = True

        if self.active:
            if Keys.is_pressed(Keys.enter) or Keys.is_pressed(Keys.escape):
                self.active = False
                self.w = 2
            if self._input:
                text = self.text.text
                done = False
                for event in Game.events:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_BACKSPACE: continue #text = text[:-1]
                        elif event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE: continue
                        else: text += event.unicode
                if Keys.is_held(Keys.backspace) and self.buffer == 0: 
                    text = text[:-1]
                    self.buffer = 7
                elif not Keys.is_held(Keys.backspace): self.buffer = 0
                if text != self.text.text: self.text.set_text(text)

    def render(self):
        self.sub.clear()
        pygame.draw.rect(self.sub.screen, Colors["pannel"], self.rect, self.w)
        self.text.render_to(self.sub.screen)
        self.sub.render()
