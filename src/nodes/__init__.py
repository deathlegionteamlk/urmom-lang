"""
Abstract Syntax Tree (AST) node definitions for Urmom Lang.
All language constructs are represented as AST nodes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any


# ========== Base Node ==========

class ASTNode:
    """Base class for all AST nodes."""
    pass


# ========== Expressions ==========

@dataclass
class Identifier(ASTNode):
    name: str

@dataclass
class IntLiteral(ASTNode):
    value: int

@dataclass
class FloatLiteral(ASTNode):
    value: float

@dataclass
class StringLiteral(ASTNode):
    value: str

@dataclass
class BoolLiteral(ASTNode):
    value: bool

@dataclass
class NoneLiteral(ASTNode):
    pass

@dataclass
class ArrayLiteral(ASTNode):
    elements: list[Expression]

@dataclass
class DictLiteral(ASTNode):
    pairs: list[tuple[Expression, Expression]]

@dataclass
class TupleLiteral(ASTNode):
    elements: list[Expression]

@dataclass
class PrefixExpr(ASTNode):
    operator: str
    right: Expression

@dataclass
class InfixExpr(ASTNode):
    left: Expression
    operator: str
    right: Expression

@dataclass
class PostfixExpr(ASTNode):
    left: Expression
    operator: str

@dataclass
class CallExpr(ASTNode):
    function: Expression
    arguments: list[Expression]

@dataclass
class IndexExpr(ASTNode):
    obj: Expression
    index: Expression

@dataclass
class SliceExpr(ASTNode):
    obj: Expression
    start: Optional[Expression]
    end: Optional[Expression]
    step: Optional[Expression]

@dataclass
class MemberExpr(ASTNode):
    obj: Expression
    member: str

@dataclass
class MethodCallExpr(ASTNode):
    obj: Expression
    method: str
    arguments: list[Expression]

@dataclass
class LambdaExpr(ASTNode):
    params: list[FunctionParam]
    body: Block
    return_type: Optional[TypeAnnotation] = None

@dataclass
class SpawnExpr(ASTNode):
    call: CallExpr

@dataclass
class AwaitExpr(ASTNode):
    expr: Expression

@dataclass
class ChanExpr(ASTNode):
    element_type: Optional[TypeAnnotation] = None
    capacity: Optional[Expression] = None

@dataclass
class SendExpr(ASTNode):
    channel: Expression
    value: Expression

@dataclass
class ReceiveExpr(ASTNode):
    channel: Expression

@dataclass
class MatchExpr(ASTNode):
    subject: Expression
    arms: list[MatchArm]

@dataclass
class MatchArm(ASTNode):
    pattern: Expression
    guard: Optional[Expression]
    body: Block

@dataclass
class TypeCastExpr(ASTNode):
    expr: Expression
    target_type: TypeAnnotation

@dataclass
class RangeExpr(ASTNode):
    start: Expression
    end: Expression
    inclusive: bool = False

@dataclass
class SpreadExpr(ASTNode):
    expr: Expression

@dataclass
class IfExpr(ASTNode):
    condition: Expression
    consequence: Block
    alternative: Optional[Block] = None
    elif_clauses: list[tuple[Expression, Block]] = field(default_factory=list)


# ========== Type Annotations ==========

@dataclass
class TypeAnnotation(ASTNode):
    name: str
    generics: list[TypeAnnotation] = field(default_factory=list)

@dataclass
class FunctionType(ASTNode):
    params: list[TypeAnnotation]
    return_type: TypeAnnotation

@dataclass
class UnionType(ASTNode):
    types: list[TypeAnnotation]

@dataclass
class OptionalType(ASTNode):
    inner: TypeAnnotation


# ========== Statements ==========

@dataclass
class LetStmt(ASTNode):
    name: str
    type_annotation: Optional[TypeAnnotation]
    value: Optional[Expression]
    mutable: bool = False

@dataclass
class ConstStmt(ASTNode):
    name: str
    type_annotation: Optional[TypeAnnotation]
    value: Expression

@dataclass
class AssignStmt(ASTNode):
    target: Expression
    value: Expression

@dataclass
class CompoundAssignStmt(ASTNode):
    target: Expression
    operator: str
    value: Expression

@dataclass
class ReturnStmt(ASTNode):
    value: Optional[Expression]

@dataclass
class BreakStmt(ASTNode):
    pass

@dataclass
class ContinueStmt(ASTNode):
    pass

@dataclass
class ThrowStmt(ASTNode):
    value: Expression

@dataclass
class DeferStmt(ASTNode):
    call: CallExpr

@dataclass
class ExpressionStmt(ASTNode):
    expression: Expression

@dataclass
class Block(ASTNode):
    statements: list[Statement]

@dataclass
class IfStmt(ASTNode):
    condition: Expression
    consequence: Block
    alternative: Optional[Block] = None
    elif_clauses: list[tuple[Expression, Block]] = field(default_factory=list)

@dataclass
class WhileStmt(ASTNode):
    condition: Expression
    body: Block

@dataclass
class ForInStmt(ASTNode):
    name: str
    iterable: Expression
    body: Block

@dataclass
class ForStmt(ASTNode):
    init: Optional[Statement]
    condition: Optional[Expression]
    update: Optional[Expression]
    body: Block

@dataclass
class MatchStmt(ASTNode):
    subject: Expression
    arms: list[MatchArm]

@dataclass
class TryCatchStmt(ASTNode):
    try_block: Block
    catch_var: Optional[str]
    catch_block: Optional[Block]
    finally_block: Optional[Block]


# ========== Declarations ==========

@dataclass
class FunctionParam(ASTNode):
    name: str
    type_annotation: Optional[TypeAnnotation] = None
    default_value: Optional[Expression] = None
    is_variadic: bool = False

@dataclass
class FunctionDecl(ASTNode):
    name: str
    params: list[FunctionParam]
    return_type: Optional[TypeAnnotation]
    body: Block
    is_public: bool = False
    is_async: bool = False

@dataclass
class StructField(ASTNode):
    name: str
    type_annotation: TypeAnnotation
    default_value: Optional[Expression] = None
    is_public: bool = False

@dataclass
class StructDecl(ASTNode):
    name: str
    fields: list[StructField]
    is_public: bool = False

@dataclass
class ImplDecl(ASTNode):
    target: str
    trait_name: Optional[str]
    methods: list[FunctionDecl]

@dataclass
class TraitDecl(ASTNode):
    name: str
    methods: list[FunctionDecl]
    is_public: bool = False

@dataclass
class EnumVariant(ASTNode):
    name: str
    fields: list[TypeAnnotation] = field(default_factory=list)
    values: list[Expression] = field(default_factory=list)

@dataclass
class EnumDecl(ASTNode):
    name: str
    variants: list[EnumVariant]
    is_public: bool = False

@dataclass
class TypeAliasDecl(ASTNode):
    name: str
    target: TypeAnnotation
    is_public: bool = False

@dataclass
class ImportDecl(ASTNode):
    module_path: str
    items: list[str] = field(default_factory=list)
    alias: Optional[str] = None
    is_from_import: bool = False

@dataclass
class ModuleDecl(ASTNode):
    name: str
    declarations: list[Declaration]
    is_public: bool = False


# ========== Top-Level ==========

@dataclass
class Program(ASTNode):
    statements: list[Statement]
    declarations: list[Declaration]
    imports: list[ImportDecl]


# Type aliases
Expression = ASTNode
Statement = ASTNode
Declaration = ASTNode
