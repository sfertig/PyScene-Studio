class CodeErrors:
    def __init__(self):
        self._last_source = None
        self.errors = {}

    def update(self, code_lines):
        body = code_lines if any(line.strip() for line in code_lines) else ["pass"]
        source_lines = ["def __editor_check__():"] + [
            "    " + line if line else ""
            for line in body
        ]
        source = "\n".join(source_lines)
        if source == self._last_source:
            return self.errors

        self._last_source = source
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
