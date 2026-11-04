import builtins
import re

import pygame
import PyScene

from PyScene import Assets


_TOKEN_PATTERN = re.compile(
    r"(?P<qualified>(?:[A-Za-z_]\w*\.)*)(?P<prefix>[A-Za-z_]\w*)?$"
)
_SELF_ASSIGNMENT_PATTERN = re.compile(r"\bself\.([A-Za-z_]\w*)\s*(?::[^=]+)?=")
_FUNCTION_PATTERN = re.compile(r"^\s*def\s+([A-Za-z_]\w*)\s*\(")


class CodeCompleter:
    def __init__(self):
        self.font = Assets.get_font("default-25")
        self.suggestions: list[str] = []
        self.replace_start = 0
        self.replace_end = 0
        self.visible = False

    def update(self, line, data, current_init_code=None):
        before_cursor = line._code[:line.cursor_index]
        match = _TOKEN_PATTERN.search(before_cursor)
        if not match:
            self.suggestions = []
            self.visible = False
            return

        qualified = (match.group("qualified") or "").rstrip(".")
        prefix = match.group("prefix") or ""
        if not qualified and not prefix:
            self.suggestions = []
            self.visible = False
            return

        self.replace_start = match.start("prefix")
        self.replace_end = line.cursor_index
        while (
            self.replace_end < len(line._code)
            and (line._code[self.replace_end].isalnum() or line._code[self.replace_end] == "_")
        ):
            self.replace_end += 1
        candidates = self.get_candidates(qualified, data, current_init_code)
        self.suggestions = sorted(
            {
                name
                for name in candidates
                if name.startswith(prefix) and name != prefix
                and not (name.startswith("__") and name.endswith("__"))
                and (prefix.startswith("_") or not name.startswith("_"))
            },
            key=str.casefold,
        )[:6]
        self.visible = bool(self.suggestions)

    def get_candidates(self, qualified, data, current_init_code=None):
        if not qualified:
            return (
                set(dir(PyScene))
                | set(dir(pygame))
                | set(dir(builtins))
            )

        parts = qualified.split(".")
        if parts[0] == "self":
            if len(parts) != 1:
                return set()
            return self.get_self_members(data, current_init_code)

        roots = {
            "pygame": pygame,
            "PyScene": PyScene,
            "Game": PyScene.Game,
            "Keys": PyScene.Keys,
            "GameObj": PyScene.GameObj,
            "Scene": PyScene.Scene,
            "SubScreen": PyScene.SubScreen,
            "Vector2D": PyScene.Vector2D,
            "Timer": PyScene.Timer,
            "Assets": PyScene.Assets,
        }
        obj = roots.get(parts[0])
        if obj is None:
            return set()
        for part in parts[1:]:
            obj = getattr(obj, part, None)
            if obj is None:
                return set()
        return set(dir(obj))

    def get_self_members(self, data, current_init_code=None):
        members = {
            name for name in dir(PyScene.GameObj)
            if not name.startswith("__")
        }
        functions = data["functions"]
        members.update(functions)
        for function in functions.values():
            code_lines = function["code"]
            if function is functions.get("__init__") and current_init_code is not None:
                code_lines = current_init_code
            for code in code_lines:
                members.update(_SELF_ASSIGNMENT_PATTERN.findall(code))
                definition = _FUNCTION_PATTERN.match(code)
                if definition:
                    members.add(definition.group(1))
        return members

    def complete(self, line):
        if not self.visible:
            return False
        suggestion = self.suggestions[0]
        line._code = (
            line._code[:self.replace_start]
            + suggestion
            + line._code[self.replace_end:]
        )
        line.code.set_text(line._code)
        line.set_cursor(self.replace_start + len(suggestion))
        self.suggestions = []
        self.visible = False
        return True

    def hide(self):
        self.suggestions = []
        self.visible = False

    def render(self, surface, line, panel_size):
        if not self.visible or not self.suggestions:
            return

        padding = 6
        row_height = self.font.get_linesize()
        width = min(
            panel_size[0],
            max(self.font.size(item)[0] for item in self.suggestions) + padding * 2,
        )
        height = row_height * len(self.suggestions) + padding * 2
        x = line.pos.x + 40 + line.cursor_x
        y = line.pos.y + line.size.y + 2
        x = max(0, min(x, panel_size[0] - width))
        if y + height > panel_size[1]:
            y = line.pos.y - height - 2
        y = max(0, min(y, panel_size[1] - height))

        popup = pygame.Rect(x, y, width, height)
        pygame.draw.rect(surface, (35, 38, 45), popup)
        pygame.draw.rect(surface, (105, 110, 125), popup, 1)
        pygame.draw.rect(
            surface,
            (65, 95, 145),
            pygame.Rect(x + 1, y + 1, width - 2, row_height),
        )
        for index, suggestion in enumerate(self.suggestions):
            rendered = self.font.render(suggestion, True, "white")
            surface.blit(
                rendered,
                (x + padding, y + padding + index * row_height),
            )
