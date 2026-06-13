"""
Urmom Lang Lexer/Tokenizer.
Converts source code text into a stream of tokens.
"""

from .tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"Lexer error at L{line}:{column} - {message}")


class Lexer:
    """Lexical analyzer for Urmom Lang source code."""

    def __init__(self, source: str, filename: str = "<stdin>"):
        self.source = source
        self.filename = filename
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens: list[Token] = []
        self._paren_depth = 0  # Track nesting for newline significance

    def _peek(self, offset: int = 0) -> str:
        pos = self.position + offset
        if pos < len(self.source):
            return self.source[pos]
        return "\0"

    def _advance(self) -> str:
        if self.position >= len(self.source):
            return "\0"
        ch = self.source[self.position]
        self.position += 1
        if ch == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _skip_whitespace(self):
        while self.position < len(self.source) and self.source[self.position] in " \t\r":
            self._advance()

    def _skip_comment(self):
        # Single-line comment: // ...
        if self._peek() == "/" and self._peek(1) == "/":
            while self.position < len(self.source) and self.source[self.position] != "\n":
                self._advance()
            return True
        # Multi-line comment: /* ... */
        if self._peek() == "/" and self._peek(1) == "*":
            self._advance()  # /
            self._advance()  # *
            while self.position < len(self.source):
                if self._peek() == "*" and self._peek(1) == "/":
                    self._advance()  # *
                    self._advance()  # /
                    break
                self._advance()
            return True
        return False

    def _read_string(self, quote: str) -> Token:
        start_line = self.line
        start_col = self.column
        self._advance()  # consume opening quote
        result = []
        while self.position < len(self.source):
            ch = self._advance()
            if ch == "\\":
                next_ch = self._advance()
                escape_map = {
                    "n": "\n", "t": "\t", "r": "\r", "\\": "\\",
                    "'": "'", '"': '"', "0": "\0",
                }
                if next_ch in escape_map:
                    result.append(escape_map[next_ch])
                else:
                    result.append("\\")
                    result.append(next_ch)
            elif ch == quote:
                return Token(TokenType.STRING, "".join(result), start_line, start_col, self.filename)
            else:
                result.append(ch)
        raise LexerError(f"Unterminated string", start_line, start_col)

    def _read_number(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []
        is_float = False
        # Handle hex
        if self._peek() == "0" and self._peek(1) in "xX":
            result.append(self._advance())  # 0
            result.append(self._advance())  # x
            while self.position < len(self.source) and (self.source[self.position].isalnum() or self.source[self.position] == "_"):
                result.append(self._advance())
            return Token(TokenType.INT, "".join(result), start_line, start_col, self.filename)
        # Handle binary
        if self._peek() == "0" and self._peek(1) in "bB":
            result.append(self._advance())  # 0
            result.append(self._advance())  # b
            while self.position < len(self.source) and self.source[self.position] in "01_":
                result.append(self._advance())
            return Token(TokenType.INT, "".join(result), start_line, start_col, self.filename)
        while self.position < len(self.source):
            ch = self.source[self.position]
            if ch == "_" and self._peek(1).isdigit():
                self._advance()
                continue
            if ch.isdigit():
                result.append(self._advance())
            elif ch == "." and not is_float:
                # Check if it's a method call or float
                if self._peek(1).isdigit():
                    is_float = True
                    result.append(self._advance())
                else:
                    break
            elif ch in "eE" and not is_float:
                is_float = True
                result.append(self._advance())
                if self._peek() in "+-":
                    result.append(self._advance())
            elif ch in "eE" and is_float:
                result.append(self._advance())
                if self._peek() in "+-":
                    result.append(self._advance())
            else:
                break
        tok_type = TokenType.FLOAT if is_float else TokenType.INT
        return Token(tok_type, "".join(result), start_line, start_col, self.filename)

    def _read_identifier(self) -> Token:
        start_line = self.line
        start_col = self.column
        result = []
        while self.position < len(self.source):
            ch = self.source[self.position]
            if ch.isalnum() or ch == "_":
                result.append(self._advance())
            else:
                break
        ident = "".join(result)
        tok_type = KEYWORDS.get(ident, TokenType.IDENT)
        return Token(tok_type, ident, start_line, start_col, self.filename)

    def _make_token(self, type: TokenType, literal: str) -> Token:
        return Token(type, literal, self.line, self.column, self.filename)

    def _two_char_token(self, ch: str, single_type: TokenType,
                        double_type: TokenType = None,
                        triple_type: TokenType = None) -> Token:
        start_line = self.line
        start_col = self.column
        self._advance()  # consume first char
        if triple_type and self._peek() == ch and self._peek(1) == ch:
            self._advance()
            self._advance()
            return Token(triple_type, ch * 3, start_line, start_col, self.filename)
        if double_type and self._peek() == ch:
            self._advance()
            return Token(double_type, ch * 2, start_line, start_col, self.filename)
        return Token(single_type, ch, start_line, start_col, self.filename)

    def tokenize(self) -> list[Token]:
        """Tokenize the entire source and return list of tokens."""
        self.tokens = []
        while self.position < len(self.source):
            self._skip_whitespace()
            if self.position >= len(self.source):
                break
            ch = self._peek()
            # Comments
            if ch == "/" and (self._peek(1) == "/" or self._peek(1) == "*"):
                self._skip_comment()
                continue
            # Newlines (significant in some contexts)
            if ch == "\n":
                self._advance()
                # Only emit newline tokens outside of parentheses/brackets
                if self._paren_depth == 0 and self.tokens and self.tokens[-1].type != TokenType.NEWLINE:
                    self.tokens.append(Token(TokenType.NEWLINE, "\\n", self.line - 1, 1, self.filename))
                continue
            # String literals
            if ch in '"\'':
                self.tokens.append(self._read_string(ch))
                continue
            # Numbers
            if ch.isdigit():
                self.tokens.append(self._read_number())
                continue
            # Identifiers and keywords
            if ch.isalpha() or ch == "_":
                self.tokens.append(self._read_identifier())
                continue
            # Two/three character operators
            if ch == "=" and self._peek(1) == "=" and self._peek(2) == "=":
                start = (self.line, self.column)
                self._advance(); self._advance(); self._advance()
                self.tokens.append(Token(TokenType.ILLEGAL, "===", start[0], start[1], self.filename))
                continue
            if ch == "!" and self._peek(1) == "=" and self._peek(2) == "=":
                start = (self.line, self.column)
                self._advance(); self._advance(); self._advance()
                self.tokens.append(Token(TokenType.ILLEGAL, "!==", start[0], start[1], self.filename))
                continue
            # Multi-char operators
            if ch == "+":
                if self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.PLUS_ASSIGN, "+=", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.PLUS, self._advance()))
                continue
            if ch == "-":
                if self._peek(1) == ">":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.ARROW, "->", start[0], start[1], self.filename))
                elif self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.MINUS_ASSIGN, "-=", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.MINUS, self._advance()))
                continue
            if ch == "*":
                if self._peek(1) == "*":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.POWER, "**", start[0], start[1], self.filename))
                elif self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.STAR_ASSIGN, "*=", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.STAR, self._advance()))
                continue
            if ch == "/":
                if self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.SLASH_ASSIGN, "/=", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.SLASH, self._advance()))
                continue
            if ch == "%":
                self.tokens.append(self._make_token(TokenType.PERCENT, self._advance()))
                continue
            if ch == "=":
                if self._peek(1) == ">":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.FAT_ARROW, "=>", start[0], start[1], self.filename))
                elif self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.EQ, "==", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.ASSIGN, self._advance()))
                continue
            if ch == "!":
                if self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.NOT_EQ, "!=", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.NOT, self._advance()))
                continue
            if ch == "<":
                if self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.LTE, "<=", start[0], start[1], self.filename))
                elif self._peek(1) == "<":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.LSHIFT, "<<", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.LT, self._advance()))
                continue
            if ch == ">":
                if self._peek(1) == "=":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.GTE, ">=", start[0], start[1], self.filename))
                elif self._peek(1) == ">":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.RSHIFT, ">>", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.GT, self._advance()))
                continue
            if ch == "&":
                if self._peek(1) == "&":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.AND, "&&", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.BIT_AND, self._advance()))
                continue
            if ch == "|":
                if self._peek(1) == "|":
                    start = (self.line, self.column)
                    self._advance(); self._advance()
                    self.tokens.append(Token(TokenType.OR, "||", start[0], start[1], self.filename))
                else:
                    self.tokens.append(self._make_token(TokenType.BIT_OR, self._advance()))
                continue
            if ch == "^":
                self.tokens.append(self._make_token(TokenType.BIT_XOR, self._advance()))
                continue
            if ch == "~":
                self.tokens.append(self._make_token(TokenType.BIT_NOT, self._advance()))
                continue
            # Delimiters
            delimiter_map = {
                "(": TokenType.LPAREN,
                ")": TokenType.RPAREN,
                "{": TokenType.LBRACE,
                "}": TokenType.RBRACE,
                "[": TokenType.LBRACKET,
                "]": TokenType.RBRACKET,
                ",": TokenType.COMMA,
                ";": TokenType.SEMICOLON,
                ":": TokenType.COLON,
                ".": TokenType.DOT,
            }
            if ch in delimiter_map:
                tok = self._make_token(delimiter_map[ch], self._advance())
                self.tokens.append(tok)
                if ch in "([{":
                    self._paren_depth += 1
                elif ch in ")]}":
                    self._paren_depth = max(0, self._paren_depth - 1)
                continue
            # Unknown character
            self.tokens.append(self._make_token(TokenType.ILLEGAL, self._advance()))

        self.tokens.append(Token(TokenType.EOF, "", self.line, self.column, self.filename))
        return self.tokens
