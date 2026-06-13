"""
Urmom Lang Parser
=================
Recursive descent parser that converts a token stream into an AST.
Supports: all expression types, pattern matching, pipe operators,
string interpolation, comprehensions, null-safe access, and more.
"""

from ..lexer.tokens import TokenType, Token
from ..ast import *


class ParseError(Exception):
    def __init__(self, message, token=None):
        self.token = token
        super().__init__(message)


class Parser:
    """Urmom Lang recursive descent parser."""
    
    def __init__(self, tokens: list, file: str = "<repl>"):
        self.tokens = [t for t in tokens if t.type != TokenType.NEWLINE]
        self.pos = 0
        self.file = file
    
    def error(self, msg, token=None):
        tok = token or self.current()
        raise ParseError(f"Parse error at line {tok.line}: {msg}", tok)
    
    def current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return Token(TokenType.EOF, None)
    
    def peek(self, offset=1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return Token(TokenType.EOF, None)
    
    def advance(self) -> Token:
        tok = self.current()
        self.pos += 1
        return tok
    
    def match(self, *types) -> bool:
        return self.current().type in types
    
    def expect(self, type: TokenType, msg: str = "") -> Token:
        if self.current().type == type:
            return self.advance()
        expected = msg or f"Expected {type.name}"
        self.error(f"{expected}, got {self.current().type.name}")
    
    def at_end(self) -> bool:
        return self.current().type == TokenType.EOF
    
    def skip_newlines(self):
        pass  # already filtered
    
    def parse(self) -> Program:
        """Parse the entire program."""
        program = Program(source_file=self.file)
        while not self.at_end():
            item = self.parse_top_level()
            if isinstance(item, Decl):
                program.declarations.append(item)
            elif item is not None:
                program.statements.append(item)
        return program
    
    # ═══════════════════════════════════════════════════════════
    # Top Level
    # ═══════════════════════════════════════════════════════════
    
    def parse_top_level(self):
        tok = self.current()
        
        # Decorators
        decorators = []
        while self.match(TokenType.AT):
            decorators.append(self.parse_decorator())
        
        # Visibility modifiers
        is_pub = False
        if self.match(TokenType.PUB):
            is_pub = True
            self.advance()
        
        if self.match(TokenType.FN):
            return self.parse_func_decl(is_pub=is_pub, decorators=decorators)
        elif self.match(TokenType.STRUCT):
            return self.parse_struct_decl(is_pub=is_pub, decorators=decorators)
        elif self.match(TokenType.ENUM):
            return self.parse_enum_decl(is_pub=is_pub, decorators=decorators)
        elif self.match(TokenType.TRAIT):
            return self.parse_trait_decl(is_pub=is_pub)
        elif self.match(TokenType.IMPL):
            return self.parse_impl_decl()
        elif self.match(TokenType.TYPE):
            return self.parse_type_alias()
        elif self.match(TokenType.IMPORT):
            return self.parse_import()
        elif self.match(TokenType.EXPORT):
            return self.parse_export()
        elif self.match(TokenType.CONST):
            return self.parse_const_decl()
        elif self.match(TokenType.USING):
            return self.parse_using()
        elif decorators:
            self.error("Decorators must precede a declaration")
        else:
            return self.parse_statement()
    
    def parse_decorator(self):
        self.expect(TokenType.AT)
        name = self.expect(TokenType.IDENTIFIER).value
        args = []
        if self.match(TokenType.LPAREN):
            self.advance()
            while not self.match(TokenType.RPAREN):
                args.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RPAREN)
        return (name, args)
    
    # ═══════════════════════════════════════════════════════════
    # Declarations
    # ═══════════════════════════════════════════════════════════
    
    def parse_func_decl(self, is_pub=False, decorators=None, is_method=False):
        line = self.current().line
        self.expect(TokenType.FN)
        
        is_async = False
        is_generator = False
        is_static = False
        is_virtual = False
        is_override = False
        is_abstract = False
        
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LPAREN)
        params = self.parse_param_list()
        self.expect(TokenType.RPAREN)
        
        return_type = None
        if self.match(TokenType.ARROW):
            self.advance()
            return_type = self.parse_type_annotation()
        
        body = None
        if self.match(TokenType.LBRACE):
            body = self.parse_block()
        elif self.match(TokenType.FAT_ARROW):
            self.advance()
            expr = self.parse_expression()
            body = Block([ReturnStmt(value=expr, line=line)])
        
        return FuncDecl(
            name=name, params=params, return_type=return_type,
            body=body, is_pub=is_pub, is_async=is_async,
            is_generator=is_generator, is_static=is_static,
            is_virtual=is_virtual, is_override=is_override,
            is_abstract=is_abstract, decorators=decorators or [],
            line=line
        )
    
    def parse_param_list(self) -> list:
        params = []
        while not self.match(TokenType.RPAREN) and not self.at_end():
            is_self = False
            is_mut = False
            
            if self.match(TokenType.SELF):
                is_self = True
                self.advance()
                params.append(Param(name="self", is_self=True))
                if self.match(TokenType.COMMA):
                    self.advance()
                continue
            
            if self.match(TokenType.MUT):
                is_mut = True
                self.advance()
            
            name = self.expect(TokenType.IDENTIFIER).value
            type_ann = None
            if self.match(TokenType.COLON):
                self.advance()
                type_ann = self.parse_type_annotation()
            
            default = None
            if self.match(TokenType.ASSIGN):
                self.advance()
                default = self.parse_expression()
            
            params.append(Param(name=name, type_annotation=type_ann,
                               default=default, is_mut=is_mut, is_self=is_self))
            
            if self.match(TokenType.COMMA):
                self.advance()
        return params
    
    def parse_struct_decl(self, is_pub=False, decorators=None):
        line = self.current().line
        self.expect(TokenType.STRUCT)
        name = self.expect(TokenType.IDENTIFIER).value
        
        generic_params = []
        if self.match(TokenType.LT):
            self.advance()
            while not self.match(TokenType.GT):
                generic_params.append(self.expect(TokenType.IDENTIFIER).value)
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.GT)
        
        traits = []
        if self.match(TokenType.COLON):
            self.advance()
            while self.match(TokenType.IDENTIFIER):
                traits.append(self.advance().value)
                if self.match(TokenType.PLUS):
                    self.advance()
        
        self.expect(TokenType.LBRACE)
        fields = []
        methods = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            if self.match(TokenType.FN):
                methods.append(self.parse_func_decl(is_method=True))
            elif self.match(TokenType.PUB):
                self.advance()
                if self.match(TokenType.FN):
                    methods.append(self.parse_func_decl(is_pub=True, is_method=True))
                else:
                    self.error("Expected fn after pub in struct")
            elif self.match(TokenType.STATIC):
                self.advance()
                m = self.parse_func_decl(is_method=True)
                m.is_static = True
                methods.append(m)
            else:
                field_name = self.expect(TokenType.IDENTIFIER).value
                type_ann = None
                if self.match(TokenType.COLON):
                    self.advance()
                    type_ann = self.parse_type_annotation()
                default = None
                if self.match(TokenType.ASSIGN):
                    self.advance()
                    default = self.parse_expression()
                fields.append((field_name, type_ann, default))
                if self.match(TokenType.COMMA):
                    self.advance()
        self.expect(TokenType.RBRACE)
        
        return StructDecl(name=name, fields=fields, methods=methods,
                         traits=traits, is_pub=is_pub, decorators=decorators or [],
                         generic_params=generic_params, line=line)
    
    def parse_enum_decl(self, is_pub=False, decorators=None):
        line = self.current().line
        self.expect(TokenType.ENUM)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LBRACE)
        variants = []
        methods = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            if self.match(TokenType.FN):
                methods.append(self.parse_func_decl(is_method=True))
            else:
                vname = self.expect(TokenType.IDENTIFIER).value
                vfields = []
                if self.match(TokenType.LPAREN):
                    self.advance()
                    while not self.match(TokenType.RPAREN):
                        vfields.append(self.parse_type_annotation())
                        if self.match(TokenType.COMMA):
                            self.advance()
                    self.expect(TokenType.RPAREN)
                variants.append((vname, vfields))
                if self.match(TokenType.COMMA):
                    self.advance()
        self.expect(TokenType.RBRACE)
        return EnumDecl(name=name, variants=variants, methods=methods,
                       is_pub=is_pub, decorators=decorators or [], line=line)
    
    def parse_trait_decl(self, is_pub=False):
        line = self.current().line
        self.expect(TokenType.TRAIT)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.LBRACE)
        method_sigs = []
        default_methods = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            if self.match(TokenType.FN):
                m = self.parse_func_decl(is_method=True)
                if m.body:
                    default_methods.append(m)
                else:
                    method_sigs.append((m.name, m.params, m.return_type))
            else:
                self.advance()
        self.expect(TokenType.RBRACE)
        return TraitDecl(name=name, method_sigs=method_sigs,
                        default_methods=default_methods, is_pub=is_pub, line=line)
    
    def parse_impl_decl(self):
        line = self.current().line
        self.expect(TokenType.IMPL)
        trait_name = ""
        target_type = ""
        
        first = self.expect(TokenType.IDENTIFIER).value
        if self.match(TokenType.FOR):
            self.advance()
            trait_name = first
            target_type = self.expect(TokenType.IDENTIFIER).value
        else:
            target_type = first
        
        self.expect(TokenType.LBRACE)
        methods = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            if self.match(TokenType.FN):
                methods.append(self.parse_func_decl(is_method=True))
            else:
                self.advance()
        self.expect(TokenType.RBRACE)
        return ImplDecl(trait_name=trait_name, target_type=target_type,
                       methods=methods, line=line)
    
    def parse_type_alias(self):
        line = self.current().line
        self.expect(TokenType.TYPE)
        name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.ASSIGN)
        target = self.parse_type_annotation()
        return TypeAliasDecl(name=name, target=target, line=line)
    
    def parse_const_decl(self):
        line = self.current().line
        self.expect(TokenType.CONST)
        name = self.expect(TokenType.IDENTIFIER).value
        type_ann = None
        if self.match(TokenType.COLON):
            self.advance()
            type_ann = self.parse_type_annotation()
        self.expect(TokenType.ASSIGN)
        value = self.parse_expression()
        return ConstStmt(name=name, type_annotation=type_ann, value=value, line=line)
    
    def parse_import(self):
        line = self.current().line
        self.expect(TokenType.IMPORT)
        
        # import "module" or import module
        if self.match(TokenType.STRING):
            module = self.advance().value
        else:
            parts = [self.expect(TokenType.IDENTIFIER).value]
            while self.match(TokenType.DOT):
                self.advance()
                parts.append(self.expect(TokenType.IDENTIFIER).value)
            module = '.'.join(parts)
        
        names = []
        alias = ""
        if self.match(TokenType.FROM):
            self.advance()
            while self.match(TokenType.IDENTIFIER):
                names.append(self.advance().value)
                if self.match(TokenType.COMMA):
                    self.advance()
        if self.match(TokenType.AS):
            self.advance()
            alias = self.expect(TokenType.IDENTIFIER).value
        
        return ImportStmt(module=module, names=names, alias=alias, line=line)
    
    def parse_export(self):
        line = self.current().line
        self.expect(TokenType.EXPORT)
        names = []
        while self.match(TokenType.IDENTIFIER):
            names.append(self.advance().value)
            if self.match(TokenType.COMMA):
                self.advance()
        return ExportStmt(names=names, line=line)
    
    def parse_using(self):
        line = self.current().line
        self.expect(TokenType.USING)
        parts = [self.expect(TokenType.IDENTIFIER).value]
        while self.match(TokenType.DOT):
            self.advance()
            parts.append(self.expect(TokenType.IDENTIFIER).value)
        return UsingStmt(module='.'.join(parts), line=line)
    
    # ═══════════════════════════════════════════════════════════
    # Type Annotations
    # ═══════════════════════════════════════════════════════════
    
    def parse_type_annotation(self) -> TypeAnnotation:
        typ = self.parse_primary_type()
        
        # Nullable? suffix
        if self.match(TokenType.QUESTION):
            self.advance()
            return NullableType(inner=typ)
        
        # Union types with |
        if self.match(TokenType.BIT_OR):
            types = [typ]
            while self.match(TokenType.BIT_OR):
                self.advance()
                types.append(self.parse_primary_type())
            return UnionType(types=types)
        
        return typ
    
    def parse_primary_type(self) -> TypeAnnotation:
        if self.match(TokenType.LPAREN):
            # Tuple or function type
            self.advance()
            types = []
            while not self.match(TokenType.RPAREN):
                types.append(self.parse_type_annotation())
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RPAREN)
            if self.match(TokenType.ARROW):
                self.advance()
                ret = self.parse_type_annotation()
                return FuncType(param_types=types, return_type=ret)
            return TupleType(element_types=types)
        
        if self.match(TokenType.LBRACKET):
            self.advance()
            elem = self.parse_type_annotation()
            self.expect(TokenType.RBRACKET)
            return ArrayType(element_type=elem)
        
        name = self.expect(TokenType.IDENTIFIER).value
        
        # Generic types: Map<K, V>, List<T>
        if self.match(TokenType.LT):
            self.advance()
            type_args = []
            while not self.match(TokenType.GT) and not self.at_end():
                type_args.append(self.parse_type_annotation())
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.GT)
            return GenericType(name=name, type_args=type_args)
        
        return SimpleType(name=name)
    
    # ═══════════════════════════════════════════════════════════
    # Statements
    # ═══════════════════════════════════════════════════════════
    
    def parse_statement(self) -> Stmt:
        tok = self.current()
        
        if self.match(TokenType.LET):
            return self.parse_let_stmt()
        elif self.match(TokenType.CONST):
            return self.parse_const_decl()
        elif self.match(TokenType.IF):
            return self.parse_if_stmt()
        elif self.match(TokenType.WHILE):
            return self.parse_while_stmt()
        elif self.match(TokenType.FOR):
            return self.parse_for_stmt()
        elif self.match(TokenType.LOOP):
            return self.parse_loop_stmt()
        elif self.match(TokenType.BREAK):
            self.advance()
            val = None
            if not self.match(TokenType.SEMICOLON, TokenType.RBRACE, TokenType.EOF):
                val = self.parse_expression()
            return BreakStmt(value=val, line=tok.line)
        elif self.match(TokenType.CONTINUE):
            self.advance()
            return ContinueStmt(line=tok.line)
        elif self.match(TokenType.RETURN):
            return self.parse_return_stmt()
        elif self.match(TokenType.THROW):
            self.advance()
            expr = self.parse_expression()
            return ThrowStmt(error=expr, line=tok.line)
        elif self.match(TokenType.DEFER):
            self.advance()
            body = self.parse_statement()
            return DeferStmt(body=body, line=tok.line)
        elif self.match(TokenType.ASSERT):
            return self.parse_assert_stmt()
        elif self.match(TokenType.MATCH):
            return self.parse_match_stmt()
        elif self.match(TokenType.TRY):
            return self.parse_try_stmt()
        elif self.match(TokenType.YIELD):
            self.advance()
            val = None
            if not self.match(TokenType.SEMICOLON, TokenType.RBRACE, TokenType.EOF):
                val = self.parse_expression()
            return YieldStmt(value=val, line=tok.line)
        elif self.match(TokenType.LBRACE):
            return self.parse_block()
        elif self.match(TokenType.SEMICOLON):
            self.advance()
            return None
        else:
            return self.parse_expr_stmt()
    
    def parse_let_stmt(self) -> LetStmt:
        line = self.current().line
        self.expect(TokenType.LET)
        mutable = False
        if self.match(TokenType.MUT):
            mutable = True
            self.advance()
        
        name = self.expect(TokenType.IDENTIFIER).value
        type_ann = None
        if self.match(TokenType.COLON):
            self.advance()
            type_ann = self.parse_type_annotation()
        
        value = None
        if self.match(TokenType.ASSIGN):
            self.advance()
            value = self.parse_expression()
        
        return LetStmt(name=name, mutable=mutable, type_annotation=type_ann,
                      value=value, line=line)
    
    def parse_if_stmt(self) -> IfStmt:
        line = self.current().line
        self.expect(TokenType.IF)
        condition = self.parse_expression()
        then_block = self.parse_block_or_stmt()
        
        elif_clauses = []
        while self.match(TokenType.ELIF):
            self.advance()
            elif_cond = self.parse_expression()
            elif_body = self.parse_block_or_stmt()
            elif_clauses.append((elif_cond, elif_body))
        
        else_block = None
        if self.match(TokenType.ELSE):
            self.advance()
            else_block = self.parse_block_or_stmt()
        
        return IfStmt(condition=condition, then_block=then_block,
                     elif_clauses=elif_clauses, else_block=else_block, line=line)
    
    def parse_while_stmt(self) -> WhileStmt:
        line = self.current().line
        self.expect(TokenType.WHILE)
        condition = self.parse_expression()
        body = self.parse_block_or_stmt()
        return WhileStmt(condition=condition, body=body, line=line)
    
    def parse_for_stmt(self) -> Stmt:
        line = self.current().line
        self.expect(TokenType.FOR)
        name = self.expect(TokenType.IDENTIFIER).value
        
        if self.match(TokenType.IN):
            self.advance()
            iterable = self.parse_expression()
            body = self.parse_block_or_stmt()
            return ForInStmt(name=name, iterable=iterable, body=body, line=line)
        
        # for i = 0; i < 10; i++ style (C-style)
        self.error("Expected 'in' after for variable")
    
    def parse_loop_stmt(self) -> LoopStmt:
        line = self.current().line
        self.expect(TokenType.LOOP)
        body = self.parse_block_or_stmt()
        return LoopStmt(body=body, line=line)
    
    def parse_return_stmt(self) -> ReturnStmt:
        line = self.current().line
        self.expect(TokenType.RETURN)
        value = None
        if not self.match(TokenType.SEMICOLON, TokenType.RBRACE, TokenType.EOF):
            value = self.parse_expression()
        return ReturnStmt(value=value, line=line)
    
    def parse_assert_stmt(self) -> AssertStmt:
        line = self.current().line
        self.expect(TokenType.ASSERT)
        condition = self.parse_expression()
        message = None
        if self.match(TokenType.COMMA):
            self.advance()
            message = self.parse_expression()
        return AssertStmt(condition=condition, message=message, line=line)
    
    def parse_match_stmt(self) -> MatchStmt:
        line = self.current().line
        self.expect(TokenType.MATCH)
        subject = self.parse_expression()
        self.expect(TokenType.LBRACE)
        
        arms = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            patterns = []
            # Parse pattern(s)
            while True:
                patterns.append(self.parse_match_pattern())
                if self.match(TokenType.COMMA):
                    self.advance()
                else:
                    break
            
            # Optional guard
            guard = None
            if self.match(TokenType.WHEN):
                self.advance()
                guard = self.parse_expression()
            
            self.expect(TokenType.FAT_ARROW)
            body = self.parse_block_or_stmt()
            arms.append((patterns, guard, body))
        
        self.expect(TokenType.RBRACE)
        return MatchStmt(subject=subject, arms=arms, line=line)
    
    def parse_match_pattern(self):
        # Simple patterns: literals, identifiers, wildcards, type patterns
        if self.match(TokenType.UNDERSCORE):
            self.advance()
            return ('wildcard',)
        if self.match(TokenType.INT):
            return ('literal', self.advance().value)
        if self.match(TokenType.FLOAT):
            return ('literal', self.advance().value)
        if self.match(TokenType.STRING):
            return ('literal', self.advance().value)
        if self.match(TokenType.BOOL):
            return ('literal', self.advance().value)
        if self.match(TokenType.NONE):
            self.advance()
            return ('literal', None)
        if self.match(TokenType.IDENTIFIER):
            name = self.advance().value
            # Enum variant: Name::Variant
            if self.match(TokenType.COLONCOLON):
                self.advance()
                variant = self.expect(TokenType.IDENTIFIER).value
                data = []
                if self.match(TokenType.LPAREN):
                    self.advance()
                    while not self.match(TokenType.RPAREN):
                        data.append(self.parse_match_pattern())
                        if self.match(TokenType.COMMA):
                            self.advance()
                    self.expect(TokenType.RPAREN)
                return ('enum', name, variant, data)
            # Destructure: Name(a, b)
            if self.match(TokenType.LPAREN):
                self.advance()
                fields = []
                while not self.match(TokenType.RPAREN):
                    fields.append(self.parse_match_pattern())
                    if self.match(TokenType.COMMA):
                        self.advance()
                self.expect(TokenType.RPAREN)
                return ('destructure', name, fields)
            # Binding or type check
            if self.match(TokenType.IS):
                self.advance()
                type_name = self.expect(TokenType.IDENTIFIER).value
                return ('type_bind', name, type_name)
            return ('binding', name)
        if self.match(TokenType.MINUS):
            self.advance()
            val = self.expect(TokenType.INT).value
            return ('literal', -val)
        self.error(f"Invalid match pattern: {self.current().type.name}")
    
    def parse_try_stmt(self) -> TryCatchStmt:
        line = self.current().line
        self.expect(TokenType.TRY)
        try_block = self.parse_block_or_stmt()
        
        catches = []
        while self.match(TokenType.CATCH):
            self.advance()
            error_type = ""
            var_name = ""
            if self.match(TokenType.IDENTIFIER):
                error_type = self.advance().value
            if self.match(TokenType.AS):
                self.advance()
                var_name = self.expect(TokenType.IDENTIFIER).value
            elif self.match(TokenType.IDENTIFIER):
                var_name = self.advance().value
            catch_body = self.parse_block_or_stmt()
            catches.append((error_type, var_name, catch_body))
        
        finally_block = None
        if self.match(TokenType.FINALLY):
            self.advance()
            finally_block = self.parse_block_or_stmt()
        
        return TryCatchStmt(try_block=try_block, catches=catches,
                           finally_block=finally_block, line=line)
    
    def parse_block(self) -> Block:
        self.expect(TokenType.LBRACE)
        stmts = []
        while not self.match(TokenType.RBRACE) and not self.at_end():
            s = self.parse_statement()
            if s is not None:
                stmts.append(s)
        self.expect(TokenType.RBRACE)
        return Block(statements=stmts)
    
    def parse_block_or_stmt(self):
        if self.match(TokenType.LBRACE):
            return self.parse_block()
        s = self.parse_statement()
        return Block([s]) if s else Block()
    
    def parse_expr_stmt(self) -> ExprStmt:
        expr = self.parse_expression()
        return ExprStmt(expr=expr, line=expr.line)
    
    # ═══════════════════════════════════════════════════════════
    # Expressions (by precedence, lowest to highest)
    # ═══════════════════════════════════════════════════════════
    
    def parse_expression(self) -> Expr:
        return self.parse_assignment()
    
    def parse_assignment(self) -> Expr:
        left = self.parse_ternary()
        
        assign_ops = {
            TokenType.ASSIGN: "=",
            TokenType.PLUS_ASSIGN: "+=",
            TokenType.MINUS_ASSIGN: "-=",
            TokenType.STAR_ASSIGN: "*=",
            TokenType.SLASH_ASSIGN: "/=",
            TokenType.PERCENT_ASSIGN: "%=",
            TokenType.POWER_ASSIGN: "**=",
        }
        
        if self.current().type in assign_ops:
            op = assign_ops[self.current().type]
            self.advance()
            value = self.parse_assignment()
            return AssignExpr(target=left, op=op, value=value, line=left.line)
        
        return left
    
    def parse_ternary(self) -> Expr:
        left = self.parse_null_coalesce()
        
        if self.match(TokenType.QUESTION):
            self.advance()
            true_expr = self.parse_ternary()
            self.expect(TokenType.COLON)
            false_expr = self.parse_ternary()
            return TernaryExpr(condition=left, true_expr=true_expr,
                             false_expr=false_expr, line=left.line)
        
        if self.match(TokenType.ELVIS):
            self.advance()
            default = self.parse_ternary()
            return ElvisExpr(condition=left, default=default, line=left.line)
        
        return left
    
    def parse_null_coalesce(self) -> Expr:
        left = self.parse_pipe()
        
        if self.match(TokenType.NULL_COALESCE):
            self.advance()
            right = self.parse_null_coalesce()
            return NullCoalesce(left=left, right=right, line=left.line)
        
        return left
    
    def parse_pipe(self) -> Expr:
        left = self.parse_or()
        
        while self.match(TokenType.PIPE):
            self.advance()
            right = self.parse_or()
            left = PipeExpr(left=left, right=right, line=left.line)
        
        if self.match(TokenType.COMPOSE):
            self.advance()
            right = self.parse_pipe()
            left = ComposeExpr(left=left, right=right, line=left.line)
        
        return left
    
    def parse_or(self) -> Expr:
        left = self.parse_and()
        while self.match(TokenType.OR, TokenType.BIT_OR) and self.peek().type != TokenType.GT:
            if self.match(TokenType.OR):
                self.advance()
                right = self.parse_and()
                left = LogicalOp(left=left, op="or", right=right, line=left.line)
            else:
                break
        return left
    
    def parse_and(self) -> Expr:
        left = self.parse_comparison()
        while self.match(TokenType.AND):
            self.advance()
            right = self.parse_comparison()
            left = LogicalOp(left=left, op="and", right=right, line=left.line)
        return left
    
    def parse_comparison(self) -> Expr:
        left = self.parse_spaceship()
        
        comp_ops = {
            TokenType.EQ: "==", TokenType.NE: "!=",
            TokenType.LT: "<", TokenType.LE: "<=",
            TokenType.GT: ">", TokenType.GE: ">=",
        }
        
        ops = []
        while self.current().type in comp_ops:
            op = comp_ops[self.current().type]
            self.advance()
            right = self.parse_spaceship()
            ops.append((op, right))
        
        if not ops:
            return left
        if len(ops) == 1:
            return BinaryOp(left=left, op=ops[0][0], right=ops[0][1], line=left.line)
        return Comparison(left=left, ops=ops, line=left.line)
    
    def parse_spaceship(self) -> Expr:
        left = self.parse_is()
        if self.match(TokenType.SPACESHIP):
            self.advance()
            right = self.parse_is()
            return BinaryOp(left=left, op="<=>", right=right, line=left.line)
        return left
    
    def parse_is(self) -> Expr:
        left = self.parse_bitwise()
        if self.match(TokenType.IS):
            self.advance()
            right = self.parse_type_annotation()
            return IsExpr(left=left, right=right, line=left.line)
        return left
    
    def parse_bitwise(self) -> Expr:
        left = self.parse_range()
        
        while self.match(TokenType.BIT_AND, TokenType.BIT_OR, TokenType.BIT_XOR,
                        TokenType.LSHIFT, TokenType.RSHIFT):
            op_map = {
                TokenType.BIT_AND: "&", TokenType.BIT_OR: "|",
                TokenType.BIT_XOR: "^", TokenType.LSHIFT: "<<",
                TokenType.RSHIFT: ">>",
            }
            op = op_map[self.current().type]
            self.advance()
            right = self.parse_range()
            left = BinaryOp(left=left, op=op, right=right, line=left.line)
        return left
    
    def parse_range(self) -> Expr:
        left = self.parse_addition()
        
        if self.match(TokenType.DOTDOT):
            self.advance()
            inclusive = True
            end = self.parse_addition()
            step = None
            if self.match(TokenType.COLON):
                self.advance()
                step = self.parse_addition()
            return RangeLiteral(start=left, end=end, step=step,
                              inclusive=inclusive, line=left.line)
        
        if self.match(TokenType.DOTDOTLT):
            self.advance()
            end = self.parse_addition()
            step = None
            if self.match(TokenType.COLON):
                self.advance()
                step = self.parse_addition()
            return RangeLiteral(start=left, end=end, step=step,
                              inclusive=False, line=left.line)
        
        return left
    
    def parse_addition(self) -> Expr:
        left = self.parse_multiplication()
        while self.match(TokenType.PLUS, TokenType.MINUS):
            op = "+" if self.match(TokenType.PLUS) else "-"
            self.advance()
            right = self.parse_multiplication()
            left = BinaryOp(left=left, op=op, right=right, line=left.line)
        return left
    
    def parse_multiplication(self) -> Expr:
        left = self.parse_power()
        while self.match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT, TokenType.FLOOR_DIV):
            op_map = {
                TokenType.STAR: "*", TokenType.SLASH: "/",
                TokenType.PERCENT: "%", TokenType.FLOOR_DIV: "//",
            }
            op = op_map[self.current().type]
            self.advance()
            right = self.parse_power()
            left = BinaryOp(left=left, op=op, right=right, line=left.line)
        return left
    
    def parse_power(self) -> Expr:
        left = self.parse_unary()
        if self.match(TokenType.POWER):
            self.advance()
            right = self.parse_unary()
            left = BinaryOp(left=left, op="**", right=right, line=left.line)
        return left
    
    def parse_unary(self) -> Expr:
        if self.match(TokenType.MINUS):
            self.advance()
            operand = self.parse_unary()
            return UnaryOp(op="-", operand=operand, line=self.current().line)
        if self.match(TokenType.NOT):
            self.advance()
            operand = self.parse_unary()
            return UnaryOp(op="not", operand=operand, line=self.current().line)
        if self.match(TokenType.BIT_NOT):
            self.advance()
            operand = self.parse_unary()
            return UnaryOp(op="~", operand=operand, line=self.current().line)
        if self.match(TokenType.INCREMENT):
            self.advance()
            operand = self.parse_postfix()
            return UnaryOp(op="++", operand=operand, line=self.current().line)
        if self.match(TokenType.DECREMENT):
            self.advance()
            operand = self.parse_postfix()
            return UnaryOp(op="--", operand=operand, line=self.current().line)
        return self.parse_postfix()
    
    def parse_postfix(self) -> Expr:
        left = self.parse_call()
        
        # Postfix increment/decrement
        if self.match(TokenType.INCREMENT):
            self.advance()
            return UnaryOp(op="post++", operand=left, line=left.line)
        if self.match(TokenType.DECREMENT):
            self.advance()
            return UnaryOp(op="post--", operand=left, line=left.line)
        
        return left
    
    def parse_call(self) -> Expr:
        expr = self.parse_primary()
        
        while True:
            if self.match(TokenType.LPAREN):
                # Function call
                self.advance()
                args, kwargs = self.parse_call_args()
                self.expect(TokenType.RPAREN)
                expr = CallExpr(callee=expr, args=args, kwargs=kwargs, line=expr.line)
            elif self.match(TokenType.DOT):
                # Member access
                self.advance()
                null_safe = False
                if self.match(TokenType.QUESTION):
                    null_safe = True
                    self.advance()
                member = self.expect(TokenType.IDENTIFIER).value
                if self.match(TokenType.LPAREN):
                    # Method call
                    self.advance()
                    args, kwargs = self.parse_call_args()
                    self.expect(TokenType.RPAREN)
                    expr = MethodCallExpr(object=expr, method=member, args=args,
                                        kwargs=kwargs, null_safe=null_safe, line=expr.line)
                else:
                    expr = MemberAccess(object=expr, member=member,
                                       null_safe=null_safe, line=expr.line)
            elif self.match(TokenType.LBRACKET):
                # Index or slice
                self.advance()
                null_safe = False
                index = self.parse_expression()
                if self.match(TokenType.COLON):
                    # Slice
                    self.advance()
                    end = None
                    if not self.match(TokenType.RBRACKET):
                        end = self.parse_expression()
                    step = None
                    if self.match(TokenType.COLON):
                        self.advance()
                        step = self.parse_expression()
                    self.expect(TokenType.RBRACKET)
                    expr = SliceExpr(object=expr, start=index, end=end,
                                   step=step, line=expr.line)
                else:
                    self.expect(TokenType.RBRACKET)
                    expr = IndexAccess(object=expr, index=index,
                                     null_safe=null_safe, line=expr.line)
            elif self.match(TokenType.COLONCOLON):
                # Enum variant access
                self.advance()
                variant = self.expect(TokenType.IDENTIFIER).value
                if isinstance(expr, Identifier):
                    expr = EnumVariantAccess(enum_name=expr.name,
                                           variant_name=variant, line=expr.line)
                else:
                    self.error("Invalid enum variant access")
            else:
                break
        
        return expr
    
    def parse_call_args(self):
        args = []
        kwargs = {}
        while not self.match(TokenType.RPAREN) and not self.at_end():
            # Check for keyword argument: name = value
            if (self.match(TokenType.IDENTIFIER) and 
                self.peek().type == TokenType.ASSIGN):
                name = self.advance().value
                self.advance()  # =
                kwargs[name] = self.parse_expression()
            elif self.match(TokenType.SPREAD):
                self.advance()
                args.append(SpreadExpr(expr=self.parse_expression(), line=self.current().line))
            else:
                args.append(self.parse_expression())
            if self.match(TokenType.COMMA):
                self.advance()
        return args, kwargs
    
    def parse_primary(self) -> Expr:
        tok = self.current()
        
        # Literals
        if self.match(TokenType.INT):
            self.advance()
            return IntLiteral(value=tok.value, line=tok.line)
        if self.match(TokenType.FLOAT):
            self.advance()
            return FloatLiteral(value=tok.value, line=tok.line)
        if self.match(TokenType.STRING):
            self.advance()
            val = tok.value
            if isinstance(val, tuple):
                if val[0] == 'interpolated':
                    return InterpolatedString(parts=val[1], line=tok.line)
                elif val[0] == 'regex':
                    return RegexLiteral(pattern=val[1], flags=val[2], line=tok.line)
            return StringLiteral(value=val, line=tok.line)
        if self.match(TokenType.BOOL):
            self.advance()
            return BoolLiteral(value=tok.value, line=tok.line)
        if self.match(TokenType.NONE):
            self.advance()
            return NoneLiteral(line=tok.line)
        
        # Self
        if self.match(TokenType.SELF):
            self.advance()
            return SelfExpr(line=tok.line)
        if self.match(TokenType.SUPER):
            self.advance()
            return SuperExpr(line=tok.line)
        
        # Identifier
        if self.match(TokenType.IDENTIFIER):
            self.advance()
            return Identifier(name=tok.value, line=tok.line)
        
        # Grouped expression
        if self.match(TokenType.LPAREN):
            self.advance()
            expr = self.parse_expression()
            if self.match(TokenType.COMMA):
                # Tuple
                elements = [expr]
                while self.match(TokenType.COMMA):
                    self.advance()
                    elements.append(self.parse_expression())
                self.expect(TokenType.RPAREN)
                return TupleLiteral(elements=elements, line=tok.line)
            self.expect(TokenType.RPAREN)
            return GroupedExpr(expr=expr, line=tok.line)
        
        # Array literal
        if self.match(TokenType.LBRACKET):
            self.advance()
            # List comprehension
            if self.match(TokenType.FOR):
                return self.parse_list_comp(tok.line)
            elements = []
            while not self.match(TokenType.RBRACKET) and not self.at_end():
                if self.match(TokenType.SPREAD):
                    self.advance()
                    elements.append(SpreadExpr(expr=self.parse_expression(), line=tok.line))
                else:
                    elements.append(self.parse_expression())
                if self.match(TokenType.COMMA):
                    self.advance()
            self.expect(TokenType.RBRACKET)
            return ArrayLiteral(elements=elements, line=tok.line)
        
        # Dict / Set literal
        if self.match(TokenType.LBRACE):
            self.advance()
            if self.match(TokenType.RBRACE):
                self.advance()
                return DictLiteral(pairs=[], line=tok.line)
            # Dict comprehension
            if self.match(TokenType.FOR):
                return self.parse_dict_comp(tok.line)
            first = self.parse_expression()
            if self.match(TokenType.COLON):
                # Dict
                self.advance()
                value = self.parse_expression()
                pairs = [(first, value)]
                while self.match(TokenType.COMMA):
                    self.advance()
                    if self.match(TokenType.RBRACE):
                        break
                    k = self.parse_expression()
                    self.expect(TokenType.COLON)
                    v = self.parse_expression()
                    pairs.append((k, v))
                self.expect(TokenType.RBRACE)
                return DictLiteral(pairs=pairs, line=tok.line)
            else:
                # Set
                elements = [first]
                while self.match(TokenType.COMMA):
                    self.advance()
                    if self.match(TokenType.RBRACE):
                        break
                    elements.append(self.parse_expression())
                self.expect(TokenType.RBRACE)
                return SetLiteral(elements=elements, line=tok.line)
        
        # Lambda
        if self.match(TokenType.FN):
            return self.parse_lambda()
        
        # Spawn
        if self.match(TokenType.SPAWN):
            self.advance()
            if self.match(TokenType.FN):
                inner = self.parse_lambda()
            else:
                inner = self.parse_expression()
            return SpawnExpr(expr=inner, line=tok.line)
        
        # Await
        if self.match(TokenType.AWAIT):
            self.advance()
            expr = self.parse_unary()
            return AwaitExpr(expr=expr, line=tok.line)
        
        # Yield
        if self.match(TokenType.YIELD):
            self.advance()
            val = None
            if not self.match(TokenType.SEMICOLON, TokenType.RBRACE, TokenType.EOF):
                val = self.parse_expression()
            return YieldExpr(value=val, line=tok.line)
        
        # Chan
        if self.match(TokenType.CHAN):
            self.advance()
            if self.match(TokenType.LT):
                self.advance()
                cap = self.parse_expression()
                self.expect(TokenType.GT)
                return CallExpr(callee=Identifier(name="chan"),
                              args=[cap], line=tok.line)
            return Identifier(name="chan", line=tok.line)
        
        # Async
        if self.match(TokenType.ASYNC):
            self.advance()
            if self.match(TokenType.FN):
                lam = self.parse_lambda()
                lam.is_async = True
                return lam
            expr = self.parse_unary()
            return AwaitExpr(expr=expr, line=tok.line)
        
        # New
        if self.match(TokenType.NEW):
            self.advance()
            type_name = self.expect(TokenType.IDENTIFIER).value
            args = []
            if self.match(TokenType.LPAREN):
                self.advance()
                args, _ = self.parse_call_args()
                self.expect(TokenType.RPAREN)
            return NewExpr(type_name=type_name, args=args, line=tok.line)
        
        # Type cast: expr as Type
        if self.match(TokenType.AS):
            self.advance()
            target = self.parse_type_annotation()
            return TypeCastExpr(target_type=target, line=tok.line)
        
        self.error(f"Unexpected token: {tok.type.name} ({tok.value!r})")
    
    def parse_lambda(self) -> LambdaExpr:
        line = self.current().line
        self.expect(TokenType.FN)
        self.expect(TokenType.LPAREN)
        params = []
        while not self.match(TokenType.RPAREN) and not self.at_end():
            is_mut = False
            if self.match(TokenType.MUT):
                is_mut = True
                self.advance()
            name = self.expect(TokenType.IDENTIFIER).value
            type_ann = None
            if self.match(TokenType.COLON):
                self.advance()
                type_ann = self.parse_type_annotation()
            default = None
            if self.match(TokenType.ASSIGN):
                self.advance()
                default = self.parse_expression()
            params.append(Param(name=name, type_annotation=type_ann, default=default, is_mut=is_mut))
            if self.match(TokenType.COMMA):
                self.advance()
        self.expect(TokenType.RPAREN)
        
        if self.match(TokenType.FAT_ARROW):
            self.advance()
            body = self.parse_expression()
        elif self.match(TokenType.LBRACE):
            body = self.parse_block()
        else:
            self.error("Expected => or { in lambda")
        
        return LambdaExpr(params=params, body=body, line=line)
    
    def parse_list_comp(self, line):
        self.expect(TokenType.FOR)  # already peeked
        # [expr for x in iterable if condition]
        # We need to backtrack - the format is: [result_expr for var in iter if cond]
        # But we already consumed FOR, so parse from here
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        iter_expr = self.parse_expression()
        condition = None
        if self.match(TokenType.IF):
            self.advance()
            condition = self.parse_expression()
        self.expect(TokenType.RBRACKET)
        # result_expr defaults to the variable itself
        return ListComp(result_expr=Identifier(name=var_name), iter_var=var_name,
                       iter_expr=iter_expr, condition=condition, line=line)
    
    def parse_dict_comp(self, line):
        self.expect(TokenType.FOR)
        var_name = self.expect(TokenType.IDENTIFIER).value
        self.expect(TokenType.IN)
        iter_expr = self.parse_expression()
        condition = None
        if self.match(TokenType.IF):
            self.advance()
            condition = self.parse_expression()
        self.expect(TokenType.RBRACE)
        return DictComp(key_expr=Identifier(name=var_name), value_expr=Identifier(name=var_name),
                       iter_var=var_name, iter_expr=iter_expr, condition=condition, line=line)
