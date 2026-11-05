from PyScene import *
import pygame
import json

from ....utils.load_assets import Colors
from ....utils.files import *
from ..TabManager import btn
from ..scenes.Inputs import StrInput
from .RightPannel import *

from .CodeLine import CodeLine
from .CodeCompleter import CodeCompleter
from .CodeErrors import CodeErrors
from .CodeSignatureHelp import CodeSignatureHelp

class CodePannel(GameObj):
    def __init__(
        self,
        sub: SubScreen,
        data,
        right: RightPannel | None = None,
        args: Arguments | None = None,
        pos: Vector2D | None = None,
        height: int | None = None,
    ):
        position = pos if pos is not None else Vector2D(10, 55)
        super().__init__(position, visible=False, active=False)
        panel_height = height if height is not None else sub.dim.y-position.y-10
        self.size = Vector2D(sub.dim.x-20, panel_height)
        self.PSub = sub
        self.sub = SubScreen(self.pos.x, self.pos.y, self.size.x, self.size.y, Colors["bg"], sub.screen, sub)
        self.screen = self.sub.screen

        self.data = data
        self.args: Arguments | None = right.args if right is not None else args
        self.code: list[CodeLine] = []
        self.scroll_y = 0
        self.selection_anchor = None
        self.selection_focus = None
        self.selecting = False
        self.clipboard_ready = False
        self.backspace_buffer = 0
        self.completer = CodeCompleter()
        self.signature_help = CodeSignatureHelp()
        self.errors = CodeErrors()
        self.set_func("__init__")

    def set_func(self, func):
        self.func = func
        if self.args is not None:
            self.args.set_func(func)
        self.active_line = 0

        self.code.clear()
        self.scroll_y = 0
        self.completer.hide()
        y = 5
        for i, code in enumerate(self.data["functions"][func]["code"], start=1):
            line = CodeLine(y, self.sub, {}, func, i)
            line.set_code(code)
            self.code.append(line)
            y += line.size.y

        if not self.code:
            self.code.append(CodeLine(y, self.sub, {}, func, 1))
        self.refresh_errors()

    def save(self):
        lines = [line._code for line in self.code]
        while lines and not lines[-1]:
            lines.pop()
        self.data["functions"][self.func]["code"] = lines

    def update(self, func=None):
        if func is not None and func != self.func:
            self.save()
            self.set_func(func)

        line_to_delete = None
        clicked_line = None
        left_mouse_down = any(
            event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            for event in Game.events
        )
        for index, line in enumerate(self.code):
            line.update()
            if line.active: self.active_line = line.num-1
            if line.just_clicked:
                clicked_line = index
            if line.DEL:
                line_to_delete = line
                break

        if line_to_delete and len(self.code) > 1:
            self.del_line(line_to_delete)
            return
        if line_to_delete:
            line_to_delete.DEL = False

        if left_mouse_down and clicked_line is not None:
            self.selection_anchor = (clicked_line, self.code[clicked_line].cursor_index)
            self.selection_focus = self.selection_anchor
            self.selecting = True
        elif left_mouse_down:
            self.selecting = False
            mouse_pos = self.sub.local_mouse_pos().to_int()
            if 0 <= mouse_pos[0] < self.size.x and 0 <= mouse_pos[1] < self.size.y:
                self.selection_anchor = None
                self.selection_focus = None

        if self.selecting:
            self.update_mouse_selection()
        if any(
            event.type == pygame.MOUSEBUTTONUP and event.button == 1
            for event in Game.events
        ):
            self.selecting = False

        self.update_selection_state()

        focused = any(line.active for line in self.code)
        if focused:
            for event in Game.events:
                if event.type != pygame.KEYDOWN:
                    continue
                modifiers = getattr(event, "mod", 0)
                control = bool(modifiers & pygame.KMOD_CTRL)
                if control and event.key == pygame.K_c:
                    self.copy_selection()
                    continue
                if control and event.key == pygame.K_v:
                    pasted = self.get_clipboard_text()
                    if pasted is not None:
                        self.replace_selection(pasted)
                    continue
                if event.key == pygame.K_TAB:
                    current_init_code = (
                        [line._code for line in self.code]
                        if self.func == "__init__"
                        else None
                    )
                    self.completer.update(
                        self.code[self.active_line],
                        self.data,
                        current_init_code,
                    )
                    self.completer.complete(self.code[self.active_line])
                    continue
                if event.key in (pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_KP_ENTER,
                                 pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN):
                    continue
                if not control and not (modifiers & pygame.KMOD_ALT) and event.unicode and event.unicode.isprintable():
                    self.replace_selection(event.unicode)

            shift = Keys.is_held(Keys.shift)
            if Keys.is_pressed(Keys.left):
                self.move_cursor_horizontal(-1, shift)
            elif Keys.is_pressed(Keys.right):
                self.move_cursor_horizontal(1, shift)
            elif Keys.is_pressed(Keys.up):
                self.move_cursor_vertical(-1, shift)
            elif Keys.is_pressed(Keys.down):
                self.move_cursor_vertical(1, shift)

            self.backspace_buffer = max(0, self.backspace_buffer - 1)
            if Keys.is_held(Keys.backspace) and self.backspace_buffer == 0:
                if self.has_selection():
                    self.replace_selection("")
                else:
                    self.backspace()
                self.backspace_buffer = 5
            elif not Keys.is_held(Keys.backspace):
                self.backspace_buffer = 0

            if Keys.is_pressed(Keys.enter):
                self.replace_selection("\n")

            current_init_code = (
                [line._code for line in self.code]
                if self.func == "__init__"
                else None
            )
            self.completer.update(
                self.code[self.active_line],
                self.data,
                current_init_code,
            )
            self.signature_help.update(
                self.code,
                self.active_line,
                self.code[self.active_line].cursor_index,
                self.data,
            )
        else:
            self.completer.hide()
            self.signature_help.hide()

        mouse_pos = self.sub.local_mouse_pos().to_int()
        if 0 <= mouse_pos[0] < self.size.x and 0 <= mouse_pos[1] < self.size.y:
            for event in Game.events:
                if event.type == pygame.MOUSEWHEEL:
                    modifiers = getattr(event, "mod", 0)
                    if event.x or ((modifiers & pygame.KMOD_SHIFT) or Keys.is_held(Keys.shift)):
                        amount = event.x if event.x else event.y
                        line_index = min(
                            range(len(self.code)),
                            key=lambda i: abs(
                                mouse_pos[1]
                                - (self.code[i].pos.y + self.code[i].size.y // 2)
                            ),
                        )
                        self.code[line_index].scroll_horizontal(-amount * 60)
                    else:
                        self.scroll_vertical(-event.y * self.code[0].size.y * 3)

        self.refresh_errors()

    def refresh_errors(self):
        error_map = self.errors.update([line._code for line in self.code])
        for index, line in enumerate(self.code):
            line.error = error_map.get(index)

    def has_selection(self):
        return (
            self.selection_anchor is not None
            and self.selection_focus is not None
            and self.selection_anchor != self.selection_focus
        )

    def ordered_selection(self):
        if self.selection_anchor <= self.selection_focus:
            return self.selection_anchor, self.selection_focus
        return self.selection_focus, self.selection_anchor

    def update_selection_state(self):
        for line in self.code:
            line.selection = None
        if not self.has_selection():
            return

        (start_line, start_index), (end_line, end_index) = self.ordered_selection()
        for index in range(start_line, end_line + 1):
            line = self.code[index]
            if start_line == end_line:
                segment = (start_index, end_index, False)
            elif index == start_line:
                segment = (start_index, len(line._code), True)
            elif index == end_line:
                segment = (0, end_index, False)
            else:
                segment = (0, len(line._code), True)
            line.selection = segment

    def update_mouse_selection(self):
        if not self.code:
            return
        mouse_pos = self.sub.local_mouse_pos().to_int()
        index = min(
            range(len(self.code)),
            key=lambda i: abs(mouse_pos[1] - (self.code[i].pos.y + self.code[i].size.y // 2)),
        )
        line = self.code[index]
        line_x = mouse_pos[0] - line.pos.x - 40
        line.set_cursor_from_x(line_x)
        for existing in self.code:
            existing.active = existing is line
        self.active_line = index
        self.selection_focus = (index, line.cursor_index)

    def set_cursor_position(self, line_index, cursor_index, extend=False):
        if not self.code:
            return
        line_index = max(0, min(line_index, len(self.code) - 1))
        line = self.code[line_index]
        cursor_index = max(0, min(cursor_index, len(line._code)))
        current = (line_index, cursor_index)
        if extend:
            if self.selection_anchor is None:
                active = self.code[self.active_line]
                self.selection_anchor = (self.active_line, active.cursor_index)
            self.selection_focus = current
        else:
            self.selection_anchor = None
            self.selection_focus = None

        for existing in self.code:
            existing.active = existing is line
        self.active_line = line_index
        line.set_cursor(cursor_index)
        self.ensure_line_visible(line)
        self.update_selection_state()

    def move_cursor_horizontal(self, direction, extend):
        if not self.code:
            return
        if not extend and self.has_selection():
            start, end = self.ordered_selection()
            self.set_cursor_position(*(start if direction < 0 else end))
            return
        line_index = self.active_line
        cursor_index = self.code[line_index].cursor_index + direction
        if cursor_index < 0 and line_index > 0:
            line_index -= 1
            cursor_index = len(self.code[line_index]._code)
        elif cursor_index > len(self.code[line_index]._code) and line_index + 1 < len(self.code):
            line_index += 1
            cursor_index = 0
        self.set_cursor_position(line_index, cursor_index, extend)

    def move_cursor_vertical(self, direction, extend):
        if not self.code:
            return
        target = max(0, min(len(self.code) - 1, self.active_line + direction))
        self.set_cursor_position(
            target,
            self.code[self.active_line].cursor_index,
            extend,
        )

    def selected_text(self):
        if not self.has_selection():
            return ""
        (start_line, start_index), (end_line, end_index) = self.ordered_selection()
        if start_line == end_line:
            return self.code[start_line]._code[start_index:end_index]
        parts = [self.code[start_line]._code[start_index:]]
        parts.extend(line._code for line in self.code[start_line + 1:end_line])
        parts.append(self.code[end_line]._code[:end_index])
        return "\n".join(parts)

    def initialize_clipboard(self):
        if not self.clipboard_ready:
            pygame.scrap.init()
            self.clipboard_ready = True

    def copy_selection(self):
        if not self.has_selection():
            return
        self.initialize_clipboard()
        pygame.scrap.put(pygame.SCRAP_TEXT, self.selected_text().encode("utf-8"))

    def get_clipboard_text(self):
        self.initialize_clipboard()
        contents = pygame.scrap.get(pygame.SCRAP_TEXT)
        if contents is None:
            return None
        return contents.decode("utf-8").rstrip("\x00").replace("\r\n", "\n").replace("\r", "\n")

    def replace_selection(self, text):
        if not self.code:
            self.code.append(CodeLine(5, self.sub, {}, self.func, 1))

        if self.has_selection():
            (start_line, start_index), (end_line, end_index) = self.ordered_selection()
        else:
            start_line = end_line = self.active_line
            start_index = end_index = self.code[self.active_line].cursor_index

        start_line = max(0, min(start_line, len(self.code) - 1))
        end_line = max(start_line, min(end_line, len(self.code) - 1))
        start_index = max(0, min(start_index, len(self.code[start_line]._code)))
        end_index = max(0, min(end_index, len(self.code[end_line]._code)))
        original_lines = [line._code for line in self.code]

        text = text.replace("\r\n", "\n").replace("\r", "\n")
        inserted_lines = text.split("\n")
        prefix = original_lines[start_line][:start_index]
        suffix = original_lines[end_line][end_index:]
        replacement_lines = [prefix + inserted_lines[0]]
        if len(inserted_lines) > 1:
            replacement_lines.extend(inserted_lines[1:-1])
            replacement_lines.append(inserted_lines[-1] + suffix)
        else:
            replacement_lines[0] += suffix
        new_text = (
            original_lines[:start_line]
            + replacement_lines
            + original_lines[end_line + 1:]
        )

        line_height = self.code[0].size.y
        max_scroll = max(0, 5 + len(new_text) * line_height - self.size.y)
        self.scroll_y = min(self.scroll_y, max_scroll)
        self.code = [
            CodeLine(5 + index * line_height - self.scroll_y, self.sub, {}, self.func, index + 1)
            for index in range(len(new_text))
        ]
        for line, code in zip(self.code, new_text):
            line.set_code(code)

        self.active_line = start_line + len(inserted_lines) - 1
        cursor_index = len(inserted_lines[-1])
        if len(inserted_lines) == 1:
            cursor_index += len(prefix)
        for index, line in enumerate(self.code):
            line.num = index + 1
            line.lineNum.set_text(str(index + 1))
            line.active = index == self.active_line
        self.active_line = max(0, min(self.active_line, len(self.code) - 1))
        self.code[self.active_line].set_cursor(cursor_index)
        self.selection_anchor = None
        self.selection_focus = None
        self.ensure_line_visible(self.code[self.active_line])

    def backspace(self):
        line = self.code[self.active_line]
        if line.cursor_index == 0:
            if self.active_line > 0 or not line._code:
                self.del_line(line)
        else:
            line._code = line._code[:line.cursor_index - 1] + line._code[line.cursor_index:]
            line.code.set_text(line._code)
            line.set_cursor(line.cursor_index - 1)

    def del_line(self, line):
        if len(self.code) == 1:
            line.DEL = False
            return

        i = self.code.index(line)
        if i == 0 and line._code:
            line.DEL = False
            return

        cursor_index = 0
        if i > 0:
            previous = self.code[i - 1]
            cursor_index = len(previous._code)
            previous.set_code(previous._code + line._code)

        self.code.remove(line)
        for num, remaining in enumerate(self.code, start=1):
            if remaining.num != num:
                remaining.move_y(-line.size.y)
                remaining.num = num
                remaining.lineNum.set_text(str(num))

        self.active_line = max(0, i - 1)
        for remaining in self.code:
            remaining.active = False
        active = self.code[self.active_line]
        active.active = True
        if i > 0:
            active.set_cursor(cursor_index)
        else:
            active._on_active()
        active.backspace_buffer = 15
        self.clamp_vertical_scroll()
        self.ensure_line_visible(active)

    def move_active(self, dir):
        if not self.code:
            return
        self.code[self.active_line].active = False
        self.active_line = max(0, min(len(self.code)-1, self.active_line+dir))
        self.code[self.active_line].active = True
        self.code[self.active_line]._on_active()
        self.ensure_line_visible(self.code[self.active_line])

    def scroll_vertical(self, amount):
        if not self.code:
            return
        content_bottom = self.code[-1].pos.y + self.code[-1].size.y + self.scroll_y
        max_scroll = max(0, content_bottom - self.size.y)
        new_scroll = max(0, min(max_scroll, self.scroll_y + amount))
        delta = new_scroll - self.scroll_y
        if delta:
            for line in self.code:
                line.move_y(-delta)
            self.scroll_y = new_scroll

    def clamp_vertical_scroll(self):
        if not self.code:
            self.scroll_y = 0
            return
        content_bottom = self.code[-1].pos.y + self.code[-1].size.y + self.scroll_y
        self.scroll_vertical(content_bottom - self.size.y - self.scroll_y)

    def ensure_line_visible(self, line):
        if line.pos.y < 0:
            self.scroll_vertical(line.pos.y)
        elif line.pos.y + line.size.y > self.size.y:
            self.scroll_vertical(line.pos.y + line.size.y - self.size.y)


    def render(self):
        self.sub.clear()
        #pygame.draw.rect(self.sub.screen, "yellow", (0, 0, 100, 100)) #test to find the subscreen

        for line in self.code:
            line.render()

        hovered_error = next(
            (line for line in self.code if line.hovered and line.error),
            None,
        )
        if hovered_error:
            self.render_error_tooltip(hovered_error)

        if self.code and self.code[self.active_line].active:
            self.completer.render(
                self.sub.screen,
                self.code[self.active_line],
                (self.size.x, self.size.y),
            )
            self.signature_help.render(
                self.sub.screen,
                self.code[self.active_line],
                (self.size.x, self.size.y),
            )

        self.sub.render()

    def render_error_tooltip(self, line):
        font = Assets.get_font("default-25")
        message = line.error["message"]
        padding = 8
        text = font.render(message, True, "white")
        width = min(self.size.x, text.get_width() + padding * 2)
        height = text.get_height() + padding * 2
        x = max(0, min(line.pos.x + 40, self.size.x - width))
        y = line.pos.y + line.size.y + 2
        if y + height > self.size.y:
            y = line.pos.y - height - 2
        y = max(0, min(y, self.size.y - height))

        tooltip = pygame.Rect(x, y, width, height)
        pygame.draw.rect(self.sub.screen, (45, 35, 35), tooltip)
        pygame.draw.rect(self.sub.screen, (255, 65, 65), tooltip, 1)
        self.sub.screen.blit(text, (x + padding, y + padding))
