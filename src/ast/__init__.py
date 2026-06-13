"""
Urmom Lang AST Nodes
====================
Defines the complete Abstract Syntax Tree for Urmom Lang.
Every syntactic construct in the language has a corresponding AST node.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


# ═══════════════════════════════════════════════════════════════
# Type Annotations
# ═══════════════════════════════════════════════════════════════

@dataclass
class TypeAnnotation:
    """Base class for type annotations."""
    pass

@dataclass
class SimpleType(TypeAnnotation):
    name: str = ""

@dataclass
class GenericType(TypeAnnotation):
    name: str = ""
    type_args: List[TypeAnnotation] = field(default_factory=list)

@dataclass
class FuncType(TypeAnnotation):
    param_types: List[TypeAnnotation] = field(default_factory=list)
    return_type: TypeAnnotation = None

@dataclass
class TupleType(TypeAnnotation):
    element_types: List[TypeAnnotation] = field(default_factory=list)

@dataclass
class ArrayType(TypeAnnotation):
    element_type: TypeAnnotation = None

@dataclass
class DictType(TypeAnnotation):
    key_type: TypeAnnotation = None
    value_type: TypeAnnotation = None

@dataclass
class OptionalType(TypeAnnotation):
    inner: TypeAnnotation = None

@dataclass
class UnionType(TypeAnnotation):
    types: List[TypeAnnotation] = field(default_factory=list)

@dataclass
class NullableType(TypeAnnotation):
    """Type? syntax."""
    inner: TypeAnnotation = None


# ═══════════════════════════════════════════════════════════════
# Expressions
# ═══════════════════════════════════════════════════════════════

@dataclass
class Expr:
    """Base class for all expressions."""
    line: int = 0
    col: int = 0

@dataclass
class IntLiteral(Expr):
    value: int = 0

@dataclass
class FloatLiteral(Expr):
    value: float = 0.0

@dataclass
class StringLiteral(Expr):
    value: str = ""

@dataclass
class InterpolatedString(Expr):
    parts: list = field(default_factory=list)  # [(str|expr), ...]

@dataclass
class BoolLiteral(Expr):
    value: bool = False

@dataclass
class NoneLiteral(Expr):
    pass

@dataclass
class Identifier(Expr):
    name: str = ""

@dataclass
class SelfExpr(Expr):
    pass

@dataclass
class SuperExpr(Expr):
    pass

@dataclass
class ArrayLiteral(Expr):
    elements: List[Expr] = field(default_factory=list)

@dataclass
class DictLiteral(Expr):
    pairs: List[tuple] = field(default_factory=list)  # [(key_expr, val_expr), ...]

@dataclass
class TupleLiteral(Expr):
    elements: List[Expr] = field(default_factory=list)

@dataclass
class SetLiteral(Expr):
    elements: List[Expr] = field(default_factory=list)

@dataclass
class RangeLiteral(Expr):
    start: Expr = None
    end: Expr = None
    step: Expr = None
    inclusive: bool = False

@dataclass
class BinaryOp(Expr):
    left: Expr = None
    op: str = ""
    right: Expr = None

@dataclass
class UnaryOp(Expr):
    op: str = ""
    operand: Expr = None

@dataclass
class Comparison(Expr):
    left: Expr = None
    ops: list = field(default_factory=list)  # [(op, expr), ...]

@dataclass
class LogicalOp(Expr):
    left: Expr = None
    op: str = ""  # "and", "or"
    right: Expr = None

@dataclass
class TernaryExpr(Expr):
    condition: Expr = None
    true_expr: Expr = None
    false_expr: Expr = None

@dataclass
class NullCoalesce(Expr):
    left: Expr = None
    right: Expr = None

@dataclass
class ElvisExpr(Expr):
    condition: Expr = None
    default: Expr = None

@dataclass
class AssignExpr(Expr):
    target: Expr = None
    op: str = "="  # =, +=, -=, *=, /=, %=
    value: Expr = None

@dataclass
class CallExpr(Expr):
    callee: Expr = None
    args: List[Expr] = field(default_factory=list)
    kwargs: Dict[str, Expr] = field(default_factory=dict)

@dataclass
class MethodCallExpr(Expr):
    object: Expr = None
    method: str = ""
    args: List[Expr] = field(default_factory=list)
    kwargs: Dict[str, Expr] = field(default_factory=dict)
    null_safe: bool = False

@dataclass
class MemberAccess(Expr):
    object: Expr = None
    member: str = ""
    null_safe: bool = False

@dataclass
class IndexAccess(Expr):
    object: Expr = None
    index: Expr = None
    null_safe: bool = False

@dataclass
class SliceExpr(Expr):
    object: Expr = None
    start: Expr = None
    end: Expr = None
    step: Expr = None

@dataclass
class PipeExpr(Expr):
    left: Expr = None
    right: Expr = None  # function to pipe into

@dataclass
class ComposeExpr(Expr):
    left: Expr = None
    right: Expr = None

@dataclass
class LambdaExpr(Expr):
    params: list = field(default_factory=list)
    body: Any = None  # Expr or Block
    is_async: bool = False

@dataclass
class SpawnExpr(Expr):
    expr: Expr = None

@dataclass
class AwaitExpr(Expr):
    expr: Expr = None

@dataclass
class YieldExpr(Expr):
    value: Expr = None

@dataclass
class SpreadExpr(Expr):
    expr: Expr = None

@dataclass
class DestructureExpr(Expr):
    patterns: list = field(default_factory=list)
    rest: str = None  # rest identifier for ...

@dataclass
class TypeCastExpr(Expr):
    expr: Expr = None
    target_type: TypeAnnotation = None

@dataclass
class IsExpr(Expr):
    left: Expr = None
    right: TypeAnnotation = None

@dataclass
class RegexLiteral(Expr):
    pattern: str = ""
    flags: str = ""

@dataclass
class EnumVariantAccess(Expr):
    enum_name: str = ""
    variant_name: str = ""

@dataclass
class NewExpr(Expr):
    type_name: str = ""
    args: List[Expr] = field(default_factory=list)

@dataclass
class MacroInvocation(Expr):
    name: str = ""
    args: List[Expr] = field(default_factory=list)

@dataclass
class AsmExpr(Expr):
    instructions: list = field(default_factory=list)

@dataclass
class TryExpr(Expr):
    expr: Expr = None
    catch_var: str = ""
    catch_body: Any = None
    finally_body: Any = None

@dataclass
class ListComp(Expr):
    result_expr: Expr = None
    iter_var: str = ""
    iter_expr: Expr = None
    condition: Expr = None

@dataclass
class DictComp(Expr):
    key_expr: Expr = None
    value_expr: Expr = None
    iter_var: str = ""
    iter_expr: Expr = None
    condition: Expr = None

@dataclass
class SetComp(Expr):
    result_expr: Expr = None
    iter_var: str = ""
    iter_expr: Expr = None
    condition: Expr = None

@dataclass
class GroupedExpr(Expr):
    expr: Expr = None


# ═══════════════════════════════════════════════════════════════
# Statements
# ═══════════════════════════════════════════════════════════════

@dataclass
class Stmt:
    """Base class for all statements."""
    line: int = 0
    col: int = 0

@dataclass
class ExprStmt(Stmt):
    expr: Expr = None

@dataclass
class LetStmt(Stmt):
    name: str = ""
    mutable: bool = False
    type_annotation: TypeAnnotation = None
    value: Expr = None

@dataclass
class ConstStmt(Stmt):
    name: str = ""
    type_annotation: TypeAnnotation = None
    value: Expr = None

@dataclass
class AssignStmt(Stmt):
    target: Expr = None
    op: str = "="
    value: Expr = None

@dataclass
class Block(Stmt):
    statements: List[Stmt] = field(default_factory=list)

@dataclass
class IfStmt(Stmt):
    condition: Expr = None
    then_block: Block = None
    elif_clauses: list = field(default_factory=list)  # [(expr, block), ...]
    else_block: Block = None

@dataclass
class WhileStmt(Stmt):
    condition: Expr = None
    body: Block = None

@dataclass
class ForInStmt(Stmt):
    name: str = ""
    iterable: Expr = None
    body: Block = None

@dataclass
class ForRangeStmt(Stmt):
    name: str = ""
    start: Expr = None
    end: Expr = None
    step: Expr = None
    inclusive: bool = False
    body: Block = None

@dataclass
class LoopStmt(Stmt):
    body: Block = None

@dataclass
class BreakStmt(Stmt):
    value: Expr = None

@dataclass
class ContinueStmt(Stmt):
    pass

@dataclass
class ReturnStmt(Stmt):
    value: Expr = None

@dataclass
class YieldStmt(Stmt):
    value: Expr = None

@dataclass
class ThrowStmt(Stmt):
    error: Expr = None

@dataclass
class DeferStmt(Stmt):
    body: Stmt = None

@dataclass
class AssertStmt(Stmt):
    condition: Expr = None
    message: Expr = None

@dataclass
class MatchStmt(Stmt):
    subject: Expr = None
    arms: list = field(default_factory=list)  # [(patterns, guard, block), ...]

@dataclass
class TryCatchStmt(Stmt):
    try_block: Block = None
    catches: list = field(default_factory=list)  # [(type, var, block), ...]
    finally_block: Block = None

@dataclass
class ImportStmt(Stmt):
    module: str = ""
    names: list = field(default_factory=list)  # specific imports
    alias: str = ""

@dataclass
class ExportStmt(Stmt):
    names: list = field(default_factory=list)

@dataclass
class UsingStmt(Stmt):
    module: str = ""


# ═══════════════════════════════════════════════════════════════
# Declarations
# ═══════════════════════════════════════════════════════════════

@dataclass
class Decl:
    """Base class for top-level declarations."""
    line: int = 0
    col: int = 0

@dataclass
class FuncDecl(Decl):
    name: str = ""
    params: list = field(default_factory=list)  # [(name, type, default), ...]
    return_type: TypeAnnotation = None
    body: Block = None
    is_async: bool = False
    is_generator: bool = False
    is_pub: bool = False
    is_static: bool = False
    is_virtual: bool = False
    is_override: bool = False
    is_abstract: bool = False
    is_variadic: bool = False
    decorators: list = field(default_factory=list)

@dataclass
class Param:
    name: str = ""
    type_annotation: TypeAnnotation = None
    default: Expr = None
    is_mut: bool = False
    is_self: bool = False

@dataclass
class StructDecl(Decl):
    name: str = ""
    fields: list = field(default_factory=list)  # [(name, type, default), ...]
    methods: List[FuncDecl] = field(default_factory=list)
    traits: List[str] = field(default_factory=list)
    is_pub: bool = False
    decorators: list = field(default_factory=list)
    generic_params: list = field(default_factory=list)

@dataclass
class EnumDecl(Decl):
    name: str = ""
    variants: list = field(default_factory=list)  # [(name, [fields]), ...]
    methods: List[FuncDecl] = field(default_factory=list)
    is_pub: bool = False
    decorators: list = field(default_factory=list)

@dataclass
class TraitDecl(Decl):
    name: str = ""
    method_sigs: list = field(default_factory=list)  # [(name, params, return_type), ...]
    default_methods: List[FuncDecl] = field(default_factory=list)
    is_pub: bool = False

@dataclass
class ImplDecl(Decl):
    trait_name: str = ""
    target_type: str = ""
    methods: List[FuncDecl] = field(default_factory=list)

@dataclass
class TypeAliasDecl(Decl):
    name: str = ""
    target: TypeAnnotation = None

@dataclass
class ModuleDecl(Decl):
    name: str = ""


# ═══════════════════════════════════════════════════════════════
# Program
# ═══════════════════════════════════════════════════════════════

@dataclass
class Program:
    """The root of an Urmom Lang AST."""
    declarations: List[Decl] = field(default_factory=list)
    statements: List[Stmt] = field(default_factory=list)
    source_file: str = ""
    
    def all_items(self):
        """Return all top-level items."""
        return self.declarations + self.statements
