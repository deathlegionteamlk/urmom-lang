"""
Token types for Urmom Lang lexer.
Defines all lexical tokens the language supports.
"""

from enum import Enum, auto


class TokenType(Enum):
    # Literals
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    IDENT = auto()

    # Operators
    PLUS = auto()        # +
    MINUS = auto()       # -
    STAR = auto()        # *
    SLASH = auto()       # /
    PERCENT = auto()     # %
    POWER = auto()       # **

    # Comparison
    EQ = auto()          # ==
    NOT_EQ = auto()      # !=
    LT = auto()          # <
    GT = auto()           # >
    LTE = auto()         # <=
    GTE = auto()         # >=

    # Assignment
    ASSIGN = auto()      # =
    PLUS_ASSIGN = auto()    # +=
    MINUS_ASSIGN = auto()   # -=
    STAR_ASSIGN = auto()    # *=
    SLASH_ASSIGN = auto()   # /=

    # Logic
    AND = auto()         # &&
    OR = auto()          # ||
    NOT = auto()         # !

    # Bitwise
    BIT_AND = auto()     # &
    BIT_OR = auto()      # |
    BIT_XOR = auto()     # ^
    BIT_NOT = auto()     # ~
    LSHIFT = auto()      # <<
    RSHIFT = auto()      # >>

    # Delimiters
    LPAREN = auto()      # (
    RPAREN = auto()      # )
    LBRACE = auto()      # {
    RBRACE = auto()      # }
    LBRACKET = auto()    # [
    RBRACKET = auto()    # ]
    COMMA = auto()       # ,
    SEMICOLON = auto()   # ;
    COLON = auto()       # :
    DOT = auto()         # .
    ARROW = auto()       # ->
    FAT_ARROW = auto()   # =>

    # Keywords
    LET = auto()
    CONST = auto()
    FN = auto()
    RETURN = auto()
    IF = auto()
    ELSE = auto()
    ELIF = auto()
    FOR = auto()
    IN = auto()
    WHILE = auto()
    BREAK = auto()
    CONTINUE = auto()
    MATCH = auto()
    STRUCT = auto()
    IMPL = auto()
    TRAIT = auto()
    ENUM = auto()
    IMPORT = auto()
    FROM = auto()
    AS = auto()
    PUB = auto()
    MUT = auto()
    SPAWN = auto()
    CHAN = auto()
    TRY = auto()
    CATCH = auto()
    FINALLY = auto()
    THROW = auto()
    TYPE = auto()
    NONE = auto()
    TRUE = auto()
    FALSE = auto()
    SELF = auto()
    SUPER = auto()
    WHERE = auto()
    ASYNC = auto()
    AWAIT = auto()
    DEFER = auto()

    # Special
    EOF = auto()
    ILLEGAL = auto()
    NEWLINE = auto()
    COMMENT = auto()


KEYWORDS = {
    "let": TokenType.LET,
    "const": TokenType.CONST,
    "fn": TokenType.FN,
    "return": TokenType.RETURN,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "elif": TokenType.ELIF,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "while": TokenType.WHILE,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
    "match": TokenType.MATCH,
    "struct": TokenType.STRUCT,
    "impl": TokenType.IMPL,
    "trait": TokenType.TRAIT,
    "enum": TokenType.ENUM,
    "import": TokenType.IMPORT,
    "from": TokenType.FROM,
    "as": TokenType.AS,
    "pub": TokenType.PUB,
    "mut": TokenType.MUT,
    "spawn": TokenType.SPAWN,
    "chan": TokenType.CHAN,
    "try": TokenType.TRY,
    "catch": TokenType.CATCH,
    "finally": TokenType.FINALLY,
    "throw": TokenType.THROW,
    "type": TokenType.TYPE,
    "none": TokenType.NONE,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "self": TokenType.SELF,
    "super": TokenType.SUPER,
    "where": TokenType.WHERE,
    "async": TokenType.ASYNC,
    "await": TokenType.AWAIT,
    "defer": TokenType.DEFER,
}


class Token:
    __slots__ = ("type", "literal", "line", "column", "filename")

    def __init__(self, type: TokenType, literal: str, line: int = 0,
                 column: int = 0, filename: str = "<stdin>"):
        self.type = type
        self.literal = literal
        self.line = line
        self.column = column
        self.filename = filename

    def __repr__(self):
        return f"Token({self.type.name}, {self.literal!r}, L{self.line}:{self.column})"

    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return self.type == other.type and self.literal == other.literal
