import builtins
import io
import keyword
import tokenize


BASE = (171, 178, 191)
KEYWORD = (198, 120, 221)
FUNCTION = (97, 175, 239)
STRING = (152, 195, 121)
NUMBER = (209, 154, 102)
COMMENT = (92, 99, 112)
OPERATOR = (86, 182, 194)

_KEYWORDS = set(keyword.kwlist) | set(getattr(keyword, "softkwlist", ()))
_BUILTINS = set(dir(builtins))


class CodeHighlighter:
    def get_segments(self, code):
        try:
            tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
        except (IndentationError, tokenize.TokenError):
            return [(0, code, BASE)]

        significant = [
            token for token in tokens
            if token.type not in (
                tokenize.ENCODING,
                tokenize.ENDMARKER,
                tokenize.NEWLINE,
                tokenize.NL,
                tokenize.INDENT,
                tokenize.DEDENT,
            )
        ]
        segments = []
        offset = 0

        for index, token in enumerate(significant):
            start = token.start[1]
            end = token.end[1]
            if start < offset or end <= start or start >= len(code):
                continue

            if start > offset:
                segments.append((offset, code[offset:start], BASE))

            text = code[start:end]
            color = self.token_color(token, significant, index)
            segments.append((start, text, color))
            offset = end

        if offset < len(code):
            segments.append((offset, code[offset:], BASE))
        return segments or ([(0, code, BASE)] if code else [])

    @staticmethod
    def token_color(token, tokens, index):
        if token.type == tokenize.COMMENT:
            return COMMENT
        if token.type == tokenize.STRING:
            return STRING
        if token.type == tokenize.NUMBER:
            return NUMBER
        if token.type == tokenize.OP:
            return OPERATOR
        if token.type != tokenize.NAME:
            return BASE
        if token.string in _KEYWORDS:
            return KEYWORD
        if token.string in _BUILTINS or (
            index + 1 < len(tokens) and tokens[index + 1].string == "("
        ):
            return FUNCTION
        return BASE
