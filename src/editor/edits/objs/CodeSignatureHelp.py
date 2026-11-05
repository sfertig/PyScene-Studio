import builtins
import inspect
import keyword
import re

import pygame
import PyScene

from PyScene import Assets


_CALLEE_PATTERN = re.compile(r"([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*$")


class CodeSignatureHelp:
    def __init__(self):
        self.font = Assets.get_font("default-25")
        self.call_name = ""
        self.parameters: list[str] = []
        self.active_parameter = 0
        self.visible = False

    def update(self, code, active_line, cursor_index, data):
        source = "\n".join(line._code for line in code[:active_line])
        source += "\n" + code[active_line]._code[:cursor_index]
        call = self.find_active_call(source)
        if call is None:
            self.hide()
            return

        call_name, active_parameter = call
        parameters = self.get_parameters(call_name, data)
        if parameters is None:
            self.hide()
            return

        self.call_name = call_name
        self.parameters = parameters
        self.active_parameter = min(active_parameter, max(0, len(parameters) - 1))
        self.visible = True

    @staticmethod
    def find_active_call(source):
        stack = []
        quote = None
        triple_quote = False
        escaped = False
        comment = False

        index = 0
        while index < len(source):
            character = source[index]
            if comment:
                if character == "\n":
                    comment = False
                index += 1
                continue
            if quote is not None:
                if triple_quote and source.startswith(quote * 3, index):
                    quote = None
                    triple_quote = False
                    index += 3
                    continue
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif not triple_quote and character == quote:
                    quote = None
                index += 1
                continue
            if character == "#":
                comment = True
                index += 1
                continue
            if character in ("'", '"'):
                quote = character
                triple_quote = source.startswith(character * 3, index)
                index += 3 if triple_quote else 1
                continue

            if character in "([{":
                callee = None
                if character == "(":
                    match = _CALLEE_PATTERN.search(source[:index])
                    if match and not keyword.iskeyword(match.group(1)):
                        callee = match.group(1)
                stack.append([character, callee, 0])
            elif character in ")]}":
                if stack:
                    stack.pop()
            elif character == "," and stack and stack[-1][0] == "(":
                if stack[-1][1] is not None:
                    stack[-1][2] += 1
            index += 1

        for delimiter, callee, commas in reversed(stack):
            if delimiter == "(" and callee is not None:
                return callee, commas
        return None

    def get_parameters(self, call_name, data):
        if call_name.startswith("self."):
            function_name = call_name[5:]
            function = data.get("functions", {}).get(function_name)
            if function is not None:
                return [
                    self.format_custom_parameter(parameter)
                    for parameter in function.get("args", [])
                ]

        roots = {
            "pygame": pygame,
            "PyScene": PyScene,
            "builtins": builtins,
        }
        roots.update(
            {
                name: getattr(PyScene, name)
                for name in dir(PyScene)
                if not name.startswith("_")
            }
        )
        roots.update(
            {name: getattr(builtins, name) for name in dir(builtins) if not name.startswith("_")}
        )

        parts = call_name.split(".")
        target = roots.get(parts[0])
        if target is None:
            return None
        try:
            for part in parts[1:]:
                target = getattr(target, part)
            signature = inspect.signature(target)
        except (AttributeError, TypeError, ValueError):
            return self.get_documented_parameters(target)

        return [str(parameter) for parameter in signature.parameters.values()]

    @staticmethod
    def get_documented_parameters(target):
        doc = getattr(target, "__doc__", None)
        if not doc:
            return None
        first_line = doc.splitlines()[0].strip()
        opening = first_line.find("(")
        closing = first_line.rfind(")")
        if opening < 0 or closing <= opening:
            return None

        parameter_text = first_line[opening + 1:closing]
        parameters = []
        start = 0
        depth = 0
        for index, character in enumerate(parameter_text):
            if character in "([{":
                depth += 1
            elif character in ")]}":
                depth -= 1
            elif character == "," and depth == 0:
                parameter = parameter_text[start:index].strip()
                if parameter:
                    parameters.append(parameter)
                start = index + 1
        final_parameter = parameter_text[start:].strip()
        if final_parameter:
            parameters.append(final_parameter)
        return parameters

    @staticmethod
    def format_custom_parameter(parameter):
        name = parameter.get("name", "")
        if "default" not in parameter:
            return name
        default = parameter["default"]
        return f"{name}={default!r}"

    def hide(self):
        self.visible = False
        self.parameters = []

    def render(self, surface, line, panel_size):
        if not self.visible:
            return

        padding = 7
        row_height = self.font.get_linesize()
        max_width = max(1, panel_size[0] - padding * 2)
        parameter_rows = self.wrap_parameters(max_width)
        rendered_title = self.font.render(self.call_name, True, (170, 190, 220))
        width = min(
            panel_size[0],
            max(
                rendered_title.get_width() + padding * 2,
                max((self.measure_row(row) for row in parameter_rows), default=0)
                + padding * 2,
            ),
        )
        height = row_height * (1 + len(parameter_rows)) + padding * 2
        x = line.pos.x + 40 + line.cursor_x
        y = line.pos.y + line.size.y + 2
        x = max(0, min(x, panel_size[0] - width))
        if y + height > panel_size[1]:
            y = line.pos.y - height - 2
        y = max(0, min(y, panel_size[1] - height))

        popup = pygame.Rect(x, y, width, height)
        pygame.draw.rect(surface, (35, 38, 45), popup)
        pygame.draw.rect(surface, (105, 110, 125), popup, 1)
        surface.blit(rendered_title, (x + padding, y + padding))

        for row_index, row in enumerate(parameter_rows):
            row_y = y + padding + (row_index + 1) * row_height
            cursor_x = x + padding
            for text, active in row:
                if active:
                    rendered = self.font.render(text, True, "white")
                    pygame.draw.rect(
                        surface,
                        (65, 95, 145),
                        pygame.Rect(cursor_x - 2, row_y, rendered.get_width() + 4, row_height),
                    )
                else:
                    rendered = self.font.render(text, True, "white")
                surface.blit(rendered, (cursor_x, row_y))
                cursor_x += rendered.get_width()

    def wrap_parameters(self, max_width):
        rows = [[]]
        current_width = 0
        for index, parameter in enumerate(self.parameters):
            text = parameter + (", " if index < len(self.parameters) - 1 else "")
            width = self.font.size(text)[0]
            if rows[-1] and current_width + width > max_width:
                rows.append([])
                current_width = 0
            rows[-1].append((text, index == self.active_parameter))
            current_width += width
        return [row for row in rows if row]

    def measure_row(self, row):
        return sum(self.font.size(text)[0] for text, _ in row)
