import ast
import builtins
import symtable

import pygame
import PyScene


class CodeErrors:
    def __init__(self):
        self._last_source = None
        self.errors = {}

    def update(self, code_lines, data=None, function_name=None):
        body = self.body_or_pass(code_lines)
        source_lines = ["def __editor_check__():"] + [
            "    " + line if line else ""
            for line in body
        ]
        source = "\n".join(source_lines)
        function_args = (
            repr(data.get("functions", {}).get(function_name, {}).get("args", ()))
            if data and function_name is not None
            else ""
        )
        cache_key = (
            source,
            tuple(data.get("imports", ())) if data else (),
            function_name,
            function_args,
        )
        if cache_key == self._last_source:
            return self.errors

        self._last_source = cache_key
        self.errors = {}
        try:
            compile(source, "<editor>", "exec")
        except SyntaxError as error:
            line_index = (error.lineno or 2) - 2
            line_index = max(0, min(line_index, len(code_lines) - 1))
            start = max(0, (error.offset or 5) - 5)
            end_offset = getattr(error, "end_offset", None)
            end = max(start + 1, (end_offset - 5) if end_offset else start + 1)
            self.errors[line_index] = {
                "message": error.msg,
                "start": start,
                "end": end,
            }
            return self.errors

        if data is not None and function_name is not None:
            self.errors.update(
                self.find_undefined_names(code_lines, data, function_name)
            )
        return self.errors

    @staticmethod
    def body_or_pass(code_lines):
        if any(line.strip() and not line.lstrip().startswith("#") for line in code_lines):
            return code_lines
        return ["pass"]

    def find_undefined_names(self, code_lines, data, function_name):
        imports = self.valid_imports(data.get("imports", ()))
        if self.has_unknown_star_import(imports):
            return {}
        function = data.get("functions", {}).get(function_name, {})
        arguments = [
            argument.get("name", "")
            for argument in function.get("args", ())
            if isinstance(argument, dict)
        ]
        arguments = [
            name for name in arguments
            if name.isidentifier() and not name.startswith("__editor_")
        ]

        prefix_lines = ["from PyScene import *", "import pygame", *imports]
        signature = ", ".join(["self", *arguments])
        source_lines = [
            *prefix_lines,
            f"def __editor_check__({signature}):",
            *[
                "    " + line if line else ""
                for line in self.body_or_pass(code_lines)
            ],
        ]
        source = "\n".join(source_lines)

        try:
            tree = ast.parse(source, filename="<editor>")
            module_symbols = symtable.symtable(source, "<editor>", "exec")
        except (SyntaxError, ValueError):
            return {}

        function_symbols = next(
            (
                child
                for child in module_symbols.get_children()
                if child.get_name() == "__editor_check__"
            ),
            None,
        )
        if function_symbols is None:
            return {}

        known_globals = (
            set(dir(builtins))
            | set(dir(PyScene))
            | set(dir(pygame))
            | self.imported_names(imports)
        )
        unresolved = {
            symbol.get_name()
            for symbol in function_symbols.get_symbols()
            if symbol.is_global()
            and symbol.is_referenced()
            and not symbol.is_assigned()
            and symbol.get_name() not in known_globals
        }
        if not unresolved:
            return {}

        editor_function = next(
            (
                node for node in tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "__editor_check__"
            ),
            None,
        )
        if editor_function is None:
            return {}

        body_start_line = len(prefix_lines) + 2
        errors = {}
        for node in ast.walk(editor_function):
            if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
                continue
            if node.id not in unresolved:
                continue

            line_index = node.lineno - body_start_line
            if not 0 <= line_index < len(code_lines) or line_index in errors:
                continue
            errors[line_index] = {
                "message": f"Name '{node.id}' is not defined",
                "start": max(0, node.col_offset - 4),
                "end": max(1, node.end_col_offset - 4),
            }
        return errors

    @staticmethod
    def valid_imports(import_lines):
        imports = []
        for import_line in import_lines:
            try:
                parsed = ast.parse(import_line)
            except SyntaxError:
                continue
            if parsed.body and all(
                isinstance(node, (ast.Import, ast.ImportFrom))
                for node in parsed.body
            ):
                imports.append(import_line)
        return imports

    @staticmethod
    def imported_names(import_lines):
        names = set()
        for import_line in import_lines:
            try:
                parsed = ast.parse(import_line)
            except SyntaxError:
                continue
            for node in parsed.body:
                if isinstance(node, ast.Import):
                    names.update(
                        alias.asname or alias.name.split(".")[0]
                        for alias in node.names
                    )
                elif isinstance(node, ast.ImportFrom):
                    names.update(
                        alias.asname or alias.name
                        for alias in node.names
                        if alias.name != "*"
                    )
                    if any(alias.name == "*" for alias in node.names):
                        if node.module == "PyScene":
                            names.update(dir(PyScene))
                        elif node.module == "pygame":
                            names.update(dir(pygame))
        return names

    @staticmethod
    def has_unknown_star_import(import_lines):
        for import_line in import_lines:
            try:
                parsed = ast.parse(import_line)
            except SyntaxError:
                continue
            for node in parsed.body:
                if (
                    isinstance(node, ast.ImportFrom)
                    and node.module not in ("PyScene", "pygame")
                    and any(alias.name == "*" for alias in node.names)
                ):
                    return True
        return False
