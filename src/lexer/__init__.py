"""
Urmom Lang Lexer
================
Tokenizes Urmom Lang source code into a stream of tokens.
Supports: string interpolation, raw strings, hex/binary/octal numbers,
multi-line strings, regex literals, decorators, and more.
"""

from .tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0):
        super().__init__(f"Lexer error at line {line}, col {col}: {message}")
        self.line = line
        self.col = col


class Lexer:
    """Urmom Lang lexer - converts source text into tokens."""
    
    def __init__(self, source: str, file: str = "<repl>"):
        self.source = source
        self.file = file
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []
        self.indent_stack = [0]
        self.paren_depth = 0
        self.brace_depth = 0
        self.bracket_depth = 0
    
    def error(self, msg):
        raise LexerError(msg, self.line, self.col)
    
    def peek(self, offset=0) -> str:
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return '\0'
    
    def advance(self) -> str:
        ch = self.source[self.pos] if self.pos < len(self.source) else '\0'
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch
    
    def match(self, expected: str) -> bool:
        if self.pos < len(self.source) and self.source[self.pos] == expected:
            self.advance()
            return True
        return False
    
    def at_end(self) -> bool:
        return self.pos >= len(self.source)
    
    def add_token(self, type: TokenType, value=None):
        self.tokens.append(Token(type, value, self.line, self.col, self.file))
    
    def skip_whitespace(self):
        while not self.at_end():
            ch = self.peek()
            if ch in ' \t\r':
                self.advance()
            elif ch == '#':
                # Single-line comment
                while not self.at_end() and self.peek() != '\n':
                    self.advance()
            elif ch == '/' and self.peek(1) == '/':
                # Single-line comment
                while not self.at_end() and self.peek() != '\n':
                    self.advance()
            elif ch == '/' and self.peek(1) == '*':
                # Multi-line comment
                self.advance()  # /
                self.advance()  # *
                while not self.at_end():
                    if self.peek() == '*' and self.peek(1) == '/':
                        self.advance()  # *
                        self.advance()  # /
                        break
                    self.advance()
            else:
                break
    
    def read_string(self, quote: str, raw: bool = False):
        """Read a string literal, supporting interpolation with $expr."""
        line, col = self.line, self.col
        self.advance()  # opening quote
        
        if raw:
            # Raw string - no escaping
            result = []
            while not self.at_end() and self.peek() != quote:
                result.append(self.advance())
            if self.at_end():
                self.error("Unterminated raw string")
            self.advance()  # closing quote
            self.add_token(TokenType.STRING, ''.join(result))
            return
        
        parts = []
        current = []
        has_interpolation = False
        
        while not self.at_end() and self.peek() != quote:
            ch = self.peek()
            if ch == '\\':
                self.advance()
                if self.at_end():
                    self.error("Unterminated escape sequence")
                esc = self.advance()
                escape_map = {
                    'n': '\n', 't': '\t', 'r': '\r', '\\': '\\',
                    "'": "'", '"': '"', '0': '\0', 'a': '\a',
                    'b': '\b', 'f': '\f', 'v': '\v',
                }
                if esc in escape_map:
                    current.append(escape_map[esc])
                elif esc == 'x':
                    # Hex escape \xNN
                    hex_str = self.source[self.pos:self.pos+2]
                    if len(hex_str) == 2:
                        try:
                            current.append(chr(int(hex_str, 16)))
                            self.pos += 2
                            self.col += 2
                        except ValueError:
                            self.error("Invalid hex escape")
                elif esc == 'u':
                    # Unicode escape \u{NNNN}
                    if self.match('{'):
                        hex_str = []
                        while not self.at_end() and self.peek() != '}':
                            hex_str.append(self.advance())
                        if not self.match('}'):
                            self.error("Unterminated unicode escape")
                        try:
                            current.append(chr(int(''.join(hex_str), 16)))
                        except ValueError:
                            self.error("Invalid unicode escape")
                    else:
                        hex_str = self.source[self.pos:self.pos+4]
                        if len(hex_str) == 4:
                            try:
                                current.append(chr(int(hex_str, 16)))
                                self.pos += 4
                                self.col += 4
                            except ValueError:
                                self.error("Invalid unicode escape")
                else:
                    current.append('\\')
                    current.append(esc)
            elif ch == '$' and self.peek(1) == '{':
                # String interpolation ${expr}
                has_interpolation = True
                if current:
                    parts.append(('str', ''.join(current)))
                    current = []
                self.advance()  # $
                self.advance()  # {
                expr = []
                depth = 1
                while not self.at_end() and depth > 0:
                    c = self.advance()
                    if c == '{': depth += 1
                    elif c == '}': depth -= 1
                    if depth > 0:
                        expr.append(c)
                parts.append(('expr', ''.join(expr)))
            elif ch == '$' and self.peek(1).isalpha():
                # Simple interpolation $identifier
                has_interpolation = True
                if current:
                    parts.append(('str', ''.join(current)))
                    current = []
                self.advance()  # $
                ident = []
                while not self.at_end() and (self.peek().isalnum() or self.peek() == '_'):
                    ident.append(self.advance())
                parts.append(('expr', ''.join(ident)))
            else:
                current.append(self.advance())
        
        if self.at_end():
            self.error("Unterminated string")
        self.advance()  # closing quote
        
        if has_interpolation:
            if current:
                parts.append(('str', ''.join(current)))
            self.add_token(TokenType.STRING, ('interpolated', parts))
        else:
            self.add_token(TokenType.STRING, ''.join(current))
    
    def read_number(self):
        """Read a number literal (int, float, hex, binary, octal)."""
        start = self.pos
        
        if self.peek() == '0':
            next_ch = self.peek(1)
            if next_ch in 'xX':
                # Hex: 0xFF
                self.advance()  # 0
                self.advance()  # x
                hex_digits = []
                while not self.at_end() and (self.peek() in '0123456789abcdefABCDEF_'):
                    ch = self.advance()
                    if ch != '_':
                        hex_digits.append(ch)
                self.add_token(TokenType.INT, int(''.join(hex_digits), 16))
                return
            elif next_ch in 'bB':
                # Binary: 0b101
                self.advance()
                self.advance()
                bin_digits = []
                while not self.at_end() and self.peek() in '01_':
                    ch = self.advance()
                    if ch != '_':
                        bin_digits.append(ch)
                self.add_token(TokenType.INT, int(''.join(bin_digits), 2))
                return
            elif next_ch in 'oO':
                # Octal: 0o77
                self.advance()
                self.advance()
                oct_digits = []
                while not self.at_end() and self.peek() in '01234567_':
                    ch = self.advance()
                    if ch != '_':
                        oct_digits.append(ch)
                self.add_token(TokenType.INT, int(''.join(oct_digits), 8))
                return
        
        # Regular number
        is_float = False
        while not self.at_end() and (self.peek().isdigit() or self.peek() == '_'):
            self.advance()
        
        if self.peek() == '.' and self.peek(1) != '.' and self.peek(1).isdigit():
            is_float = True
            self.advance()  # .
            while not self.at_end() and (self.peek().isdigit() or self.peek() == '_'):
                self.advance()
        
        if self.peek() in 'eE':
            is_float = True
            self.advance()
            if self.peek() in '+-':
                self.advance()
            while not self.at_end() and self.peek().isdigit():
                self.advance()
        
        text = self.source[start:self.pos].replace('_', '')
        if is_float:
            self.add_token(TokenType.FLOAT, float(text))
        else:
            self.add_token(TokenType.INT, int(text))
    
    def read_identifier(self):
        """Read an identifier or keyword."""
        start = self.pos
        while not self.at_end() and (self.peek().isalnum() or self.peek() == '_'):
            self.advance()
        text = self.source[start:self.pos]
        
        if text in KEYWORDS:
            tt = KEYWORDS[text]
            if tt == TokenType.BOOL:
                self.add_token(tt, text == "true")
            elif tt == TokenType.NONE:
                self.add_token(tt, None)
            else:
                self.add_token(tt, text)
        else:
            self.add_token(TokenType.IDENTIFIER, text)
    
    def read_regex(self):
        """Read a regex literal /pattern/flags."""
        start = self.pos
        self.advance()  # opening /
        pattern = []
        while not self.at_end() and self.peek() != '/':
            if self.peek() == '\\':
                pattern.append(self.advance())
            pattern.append(self.advance())
        if self.at_end():
            self.error("Unterminated regex")
        self.advance()  # closing /
        flags = []
        while not self.at_end() and self.peek().isalpha():
            flags.append(self.advance())
        self.add_token(TokenType.STRING, ('regex', ''.join(pattern), ''.join(flags)))
    
    def tokenize(self) -> list:
        """Tokenize the entire source and return token list."""
        self.tokens = []
        
        while not self.at_end():
            self.skip_whitespace()
            if self.at_end():
                break
            
            ch = self.peek()
            line, col = self.line, self.col
            
            # Newline handling
            if ch == '\n':
                self.advance()
                if self.paren_depth == 0 and self.brace_depth == 0 and self.bracket_depth == 0:
                    # Only add significant newlines when not inside brackets
                    if self.tokens and self.tokens[-1].type != TokenType.NEWLINE:
                        self.add_token(TokenType.NEWLINE, '\n')
                continue
            
            # Numbers
            if ch.isdigit():
                self.read_number()
                continue
            
            # Strings
            if ch == '"':
                self.read_string('"')
                continue
            if ch == "'":
                self.read_string("'")
                continue
            if ch == '`':
                self.read_string('`', raw=True)
                continue
            
            # Identifiers / Keywords
            if ch.isalpha() or ch == '_':
                self.read_identifier()
                continue
            
            # Multi-character operators and delimiters
            self.advance()  # consume ch
            
            if ch == '+':
                if self.match('='):
                    self.add_token(TokenType.PLUS_ASSIGN, '+=')
                elif self.match('+'):
                    self.add_token(TokenType.INCREMENT, '++')
                else:
                    self.add_token(TokenType.PLUS, '+')
            elif ch == '-':
                if self.match('='):
                    self.add_token(TokenType.MINUS_ASSIGN, '-=')
                elif self.match('>'):
                    self.add_token(TokenType.ARROW, '->')
                elif self.match('-'):
                    self.add_token(TokenType.DECREMENT, '--')
                else:
                    self.add_token(TokenType.MINUS, '-')
            elif ch == '*':
                if self.match('='):
                    self.add_token(TokenType.STAR_ASSIGN, '*=')
                elif self.match('*'):
                    self.add_token(TokenType.POWER, '**')
                else:
                    self.add_token(TokenType.STAR, '*')
            elif ch == '/':
                if self.match('='):
                    self.add_token(TokenType.SLASH_ASSIGN, '/=')
                elif self.peek() == '/' and self.match('/'):
                    self.add_token(TokenType.FLOOR_DIV, '//')
                elif self.peek().isalpha() and self.paren_depth == 0:
                    # Regex literal
                    self.pos -= 1
                    self.col -= 1
                    self.read_regex()
                else:
                    self.add_token(TokenType.SLASH, '/')
            elif ch == '%':
                if self.match('='):
                    self.add_token(TokenType.PERCENT_ASSIGN, '%=')
                else:
                    self.add_token(TokenType.PERCENT, '%')
            elif ch == '=':
                if self.match('='):
                    self.add_token(TokenType.EQ, '==')
                elif self.match('>'):
                    self.add_token(TokenType.FAT_ARROW, '=>')
                else:
                    self.add_token(TokenType.ASSIGN, '=')
            elif ch == '!':
                if self.match('='):
                    self.add_token(TokenType.NE, '!=')
                else:
                    self.add_token(TokenType.NOT, '!')
            elif ch == '<':
                if self.match('='):
                    if self.match('>'):
                        self.add_token(TokenType.SPACESHIP, '<=>')
                    else:
                        self.add_token(TokenType.LE, '<=')
                elif self.match('<'):
                    self.add_token(TokenType.LSHIFT, '<<')
                else:
                    self.add_token(TokenType.LT, '<')
            elif ch == '>':
                if self.match('='):
                    self.add_token(TokenType.GE, '>=')
                elif self.match('>'):
                    self.add_token(TokenType.COMPOSE, '>>')
                else:
                    self.add_token(TokenType.GT, '>')
            elif ch == '&':
                if self.match('&'):
                    self.add_token(TokenType.AND, '&&')
                else:
                    self.add_token(TokenType.BIT_AND, '&')
            elif ch == '|':
                if self.match('|'):
                    self.add_token(TokenType.OR, '||')
                elif self.match('>'):
                    self.add_token(TokenType.PIPE, '|>')
                else:
                    self.add_token(TokenType.BIT_OR, '|')
            elif ch == '^':
                self.add_token(TokenType.BIT_XOR, '^')
            elif ch == '~':
                self.add_token(TokenType.BIT_NOT, '~')
            elif ch == '(':
                self.paren_depth += 1
                self.add_token(TokenType.LPAREN, '(')
            elif ch == ')':
                self.paren_depth = max(0, self.paren_depth - 1)
                self.add_token(TokenType.RPAREN, ')')
            elif ch == '{':
                self.brace_depth += 1
                self.add_token(TokenType.LBRACE, '{')
            elif ch == '}':
                self.brace_depth = max(0, self.brace_depth - 1)
                self.add_token(TokenType.RBRACE, '}')
            elif ch == '[':
                self.bracket_depth += 1
                self.add_token(TokenType.LBRACKET, '[')
            elif ch == ']':
                self.bracket_depth = max(0, self.bracket_depth - 1)
                self.add_token(TokenType.RBRACKET, ']')
            elif ch == ',':
                self.add_token(TokenType.COMMA, ',')
            elif ch == '.':
                if self.match('.') and self.match('.'):
                    self.add_token(TokenType.SPREAD, '...')
                elif self.match('.'):
                    if self.match('<'):
                        self.add_token(TokenType.DOTDOTLT, '..<')
                    else:
                        self.add_token(TokenType.DOTDOT, '..')
                else:
                    self.add_token(TokenType.DOT, '.')
            elif ch == ':':
                if self.match(':'):
                    self.add_token(TokenType.COLONCOLON, '::')
                else:
                    self.add_token(TokenType.COLON, ':')
            elif ch == ';':
                self.add_token(TokenType.SEMICOLON, ';')
            elif ch == '?':
                if self.match('?'):
                    self.add_token(TokenType.NULL_COALESCE, '??')
                elif self.match(':'):
                    self.add_token(TokenType.ELVIS, '?:')
                elif self.match('.'):
                    self.add_token(TokenType.QUESTION, '?.')
                else:
                    self.add_token(TokenType.QUESTION, '?')
            elif ch == '@':
                self.add_token(TokenType.AT, '@')
            elif ch == '$':
                self.add_token(TokenType.DOLLAR, '$')
            else:
                self.error(f"Unexpected character: {ch!r}")
        
        # Add EOF
        self.add_token(TokenType.EOF, None)
        return self.tokens
