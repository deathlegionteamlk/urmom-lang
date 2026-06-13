"""
Urmom Lang Token Types
======================
Defines all token types for the Urmom Lang lexer.
"""

from enum import Enum, auto


class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    NONE = auto()
    IDENTIFIER = auto()
    
    # Arithmetic
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    PERCENT = auto()
    POWER = auto()
    FLOOR_DIV = auto()
    
    # Assignment
    ASSIGN = auto()
    PLUS_ASSIGN = auto()
    MINUS_ASSIGN = auto()
    STAR_ASSIGN = auto()
    SLASH_ASSIGN = auto()
    PERCENT_ASSIGN = auto()
    POWER_ASSIGN = auto()
    
    # Increment/Decrement
    INCREMENT = auto()
    DECREMENT = auto()
    
    # Comparison
    EQ = auto()
    NE = auto()
    LT = auto()
    LE = auto()
    GT = auto()
    GE = auto()
    SPACESHIP = auto()     # <=>
    
    # Logical
    AND = auto()           # and
    OR = auto()            # or
    NOT = auto()           # not
    
    # Bitwise
    BIT_AND = auto()       # &
    BIT_OR = auto()        # |
    BIT_XOR = auto()       # ^
    BIT_NOT = auto()       # ~
    LSHIFT = auto()        # <<
    RSHIFT = auto()        # >>
    
    # Delimiters
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    
    # Punctuation
    COMMA = auto()
    DOT = auto()
    DOTDOT = auto()        # ..
    DOTDOTLT = auto()      # ..<
    COLON = auto()
    COLONCOLON = auto()    # :: (enum variant / namespace)
    SEMICOLON = auto()
    ARROW = auto()         # ->
    FAT_ARROW = auto()     # =>
    PIPE = auto()          # |>
    COMPOSE = auto()       # >>
    SPREAD = auto()        # ...
    QUESTION = auto()      # ?
    NULL_COALESCE = auto() # ??
    ELVIS = auto()         # ?:
    AT = auto()            # @ (decorator)
    HASH = auto()          # # (for shebang / attributes)
    UNDERSCORE = auto()    # _
    DOLLAR = auto()        # $ (string interpolation prefix)
    BACKTICK = auto()      # ` (raw string)
    
    # Keywords
    LET = auto()
    MUT = auto()
    CONST = auto()
    FN = auto()
    RETURN = auto()
    IF = auto()
    ELIF = auto()
    ELSE = auto()
    FOR = auto()
    IN = auto()
    WHILE = auto()
    LOOP = auto()
    BREAK = auto()
    CONTINUE = auto()
    MATCH = auto()
    WHEN = auto()
    STRUCT = auto()
    IMPL = auto()
    TRAIT = auto()
    ENUM = auto()
    TYPE = auto()
    ALIAS = auto()
    WHERE = auto()
    SPAWN = auto()
    CHAN = auto()
    SELECT = auto()
    ASYNC = auto()
    AWAIT = auto()
    YIELD = auto()
    DEFER = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    THROW = auto()
    ASSERT = auto()
    IMPORT = auto()
    FROM = auto()
    EXPORT = auto()
    AS = auto()
    IS = auto()
    NEW = auto()
    SELF = auto()
    SUPER = auto()
    PUB = auto()
    PRIV = auto()
    STATIC = auto()
    ABSTRACT = auto()
    VIRTUAL = auto()
    OVERRIDE = auto()
    SEALED = auto()
    READONLY = auto()
    UNSAFE = auto()
    EXTERN = auto()
    ASM = auto()
    MACRO = auto()
    DO = auto()
    END = auto()
    THEN = auto()
    GIVEN = auto()
    WITH = auto()
    USING = auto()
    
    # Special
    NEWLINE = auto()
    EOF = auto()


class Token:
    __slots__ = ('type', 'value', 'line', 'col', 'file')
    
    def __init__(self, type: TokenType, value, line: int = 0, col: int = 0, file: str = ""):
        self.type = type
        self.value = value
        self.line = line
        self.col = col
        self.file = file
    
    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, line={self.line})"
    
    def __eq__(self, other):
        if isinstance(other, Token):
            return self.type == other.type and self.value == other.value
        return False


# Keywords map
KEYWORDS = {
    "let": TokenType.LET,
    "mut": TokenType.MUT,
    "const": TokenType.CONST,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "elif": TokenType.ELIF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "while": TokenType.WHILE,
    "loop": TokenType.LOOP,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "match": TokenType.MATCH,
    "when": TokenType.WHEN,
    "struct": TokenType.STRUCT,
    "impl": TokenType.IMPL,
    "trait": TokenType.TRAIT,
    "enum": TokenType.ENUM,
    "type": TokenType.TYPE,
    "alias": TokenType.ALIAS,
    "where": TokenType.WHERE,
    "spawn": TokenType.SPAWN,
    "chan": TokenType.CHAN,
    "select": TokenType.SELECT,
    "async": TokenType.ASYNC,
    "await": TokenType.AWAIT,
    "yield": TokenType.YIELD,
    "defer": TokenType.DEFER,
    "try": TokenType.TRY,
    "catch": TokenType.CATCH,
    "finally": TokenType.FINALLY,
    "throw": TokenType.THROW,
    "assert": TokenType.ASSERT,
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
    "export": TokenType.EXPORT,
    "as": TokenType.AS,
    "is": TokenType.IS,
    "new": TokenType.NEW,
    "self": TokenType.SELF,
    "super": TokenType.SUPER,
    "pub": TokenType.PUB,
    "priv": TokenType.PRIV,
    "static": TokenType.STATIC,
    "abstract": TokenType.ABSTRACT,
    "virtual": TokenType.VIRTUAL,
    "override": TokenType.OVERRIDE,
    "sealed": TokenType.SEALED,
    "readonly": TokenType.READONLY,
    "unsafe": TokenType.UNSAFE,
    "extern": TokenType.EXTERN,
    "asm": TokenType.ASM,
    "macro": TokenType.MACRO,
    "do": TokenType.DO,
    "end": TokenType.END,
    "then": TokenType.THEN,
    "given": TokenType.GIVEN,
    "with": TokenType.WITH,
    "using": TokenType.USING,
    "true": TokenType.BOOL,
    "false": TokenType.BOOL,
    "none": TokenType.NONE,
    "_": TokenType.UNDERSCORE,
}
