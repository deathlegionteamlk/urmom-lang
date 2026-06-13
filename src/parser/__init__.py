"""
Urmom Lang Parser.
Recursive descent parser that converts tokens into an AST.
"""

from __future__ import annotations
from src.lexer.tokens import Token, TokenType
from src.nodes import *


class ParseError(Exception):
    def __init__(self, message: str, token: Token):
        self.message = message
        self.token = token
        super().__init__(f"Parse error at L{token.line}:{token.column} - {message}")


class Parser:
    """Recursive descent parser for Urmom Lang."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.position = 0

    # ========== Token Helpers ==========

    def _current(self) -> Token:
        if self.position < len(self.tokens):
            return self.tokens[self.position]
        return self.tokens[-1]  # EOF

    def _peek(self, offset: int = 0) -> Token:
        pos = self.position + offset
        if pos < len(self.tokens):
            return self.tokens[pos]
        return self.tokens[-1]

    def _advance(self) -> Token:
        tok = self._current()
        if self.position < len(self.tokens) - 1:
            self.position += 1
        return tok

    def _match(self, *types: TokenType) -> Optional[Token]:
        if self._current().type in types:
            return self._advance()
        return None

    def _expect(self, type: TokenType, message: str = None) -> Token:
        tok = self._current()
        if tok.type != type:
            msg = message or f"Expected {type.name}, got {tok.type.name} ({tok.literal!r})"
            raise ParseError(msg, tok)
        return self._advance()

    def _check(self, type: TokenType) -> bool:
        return self._current().type == type

    def _check_ahead(self, type: TokenType, offset: int = 1) -> bool:
        return self._peek(offset).type == type

    def _skip_newlines(self):
        while self._check(TokenType.NEWLINE):
            self._advance()

    def _skip_terminators(self):
        """Skip newlines and optional semicolons."""
        while self._current().type in (TokenType.NEWLINE, TokenType.SEMICOLON):
            self._advance()

    # ========== Program ==========

    def parse(self) -> Program:
        """Parse the entire program."""
        statements = []
        declarations = []
        imports = []
        self._skip_newlines()

        while not self._check(TokenType.EOF):
            self._skip_newlines()
            if self._check(TokenType.EOF):
                break

            if self._check(TokenType.IMPORT) or self._check(TokenType.FROM):
                imports.append(self._parse_import())
            elif self._check(TokenType.FN) or (self._check(TokenType.PUB) and self._check_ahead(TokenType.FN)):
                declarations.append(self._parse_function_decl())
            elif self._check(TokenType.STRUCT) or (self._check(TokenType.PUB) and self._check_ahead(TokenType.STRUCT)):
                declarations.append(self._parse_struct_decl())
            elif self._check(TokenType.TRAIT) or (self._check(TokenType.PUB) and self._check_ahead(TokenType.TRAIT)):
                declarations.append(self._parse_trait_decl())
            elif self._check(TokenType.ENUM) or (self._check(TokenType.PUB) and self._check_ahead(TokenType.ENUM)):
                declarations.append(self._parse_enum_decl())
            elif self._check(TokenType.IMPL):
                declarations.append(self._parse_impl_decl())
            elif self._check(TokenType.TYPE):
                declarations.append(self._parse_type_alias())
            else:
                stmt = self._parse_statement()
                if stmt:
                    statements.append(stmt)

            self._skip_terminators()

        return Program(statements=statements, declarations=declarations, imports=imports)

    # ========== Imports ==========

    def _parse_import(self) -> ImportDecl:
        if self._check(TokenType.FROM):
            self._advance()  # from
            module_path = self._expect(TokenType.IDENT).literal
            # Handle dotted paths like std.fs
            while self._match(TokenType.DOT):
                module_path += "." + self._expect(TokenType.IDENT).literal
            self._expect(TokenType.IMPORT, "Expected 'import' after 'from'")
            items = []
            if self._check(TokenType.LBRACKET):
                self._advance()  # [
                self._skip_newlines()
                while not self._check(TokenType.RBRACKET):
                    items.append(self._expect(TokenType.IDENT).literal)
                    self._skip_newlines()
                    self._match(TokenType.COMMA)
                    self._skip_newlines()
                self._advance()  # ]
            else:
                items.append(self._expect(TokenType.IDENT).literal)
                while self._match(TokenType.COMMA):
                    self._skip_newlines()
                    items.append(self._expect(TokenType.IDENT).literal)
            alias = None
            if self._match(TokenType.AS):
                alias = self._expect(TokenType.IDENT).literal
            return ImportDecl(module_path=module_path, items=items, alias=alias, is_from_import=True)
        else:
            self._advance()  # import
            module_path = self._expect(TokenType.IDENT).literal
            while self._match(TokenType.DOT):
                module_path += "." + self._expect(TokenType.IDENT).literal
            alias = None
            if self._match(TokenType.AS):
                alias = self._expect(TokenType.IDENT).literal
            return ImportDecl(module_path=module_path, alias=alias)

    # ========== Declarations ==========

    def _parse_function_decl(self) -> FunctionDecl:
        is_public = bool(self._match(TokenType.PUB))
        self._expect(TokenType.FN)
        name = self._expect(TokenType.IDENT).literal
        self._expect(TokenType.LPAREN)
        params = self._parse_params()
        self._expect(TokenType.RPAREN)
        return_type = None
        if self._match(TokenType.ARROW):
            return_type = self._parse_type_annotation()
        self._skip_newlines()
        body = self._parse_block()
        return FunctionDecl(name=name, params=params, return_type=return_type,
                          body=body, is_public=is_public)

    def _parse_params(self) -> list[FunctionParam]:
        params = []
        self._skip_newlines()
        while not self._check(TokenType.RPAREN):
            is_variadic = bool(self._match(TokenType.DOT))  # simplified: . instead of ...
            if is_variadic:
                self._match(TokenType.DOT)  # consume second dot
                self._match(TokenType.DOT)  # consume third dot
            name = self._expect(TokenType.IDENT).literal
            type_ann = None
            if self._match(TokenType.COLON):
                type_ann = self._parse_type_annotation()
            default_value = None
            if self._match(TokenType.ASSIGN):
                default_value = self._parse_expression()
            params.append(FunctionParam(name=name, type_annotation=type_ann,
                                       default_value=default_value, is_variadic=is_variadic))
            self._skip_newlines()
            if not self._match(TokenType.COMMA):
                break
            self._skip_newlines()
        return params

    def _parse_struct_decl(self) -> StructDecl:
        is_public = bool(self._match(TokenType.PUB))
        self._expect(TokenType.STRUCT)
        name = self._expect(TokenType.IDENT).literal
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        self._skip_newlines()
        fields = []
        while not self._check(TokenType.RBRACE):
            field_public = bool(self._match(TokenType.PUB))
            field_name = self._expect(TokenType.IDENT).literal
            self._expect(TokenType.COLON)
            field_type = self._parse_type_annotation()
            default_val = None
            if self._match(TokenType.ASSIGN):
                default_val = self._parse_expression()
            fields.append(StructField(name=field_name, type_annotation=field_type,
                                      default_value=default_val, is_public=field_public))
            self._skip_terminators()
        self._advance()  # }
        return StructDecl(name=name, fields=fields, is_public=is_public)

    def _parse_trait_decl(self) -> TraitDecl:
        is_public = bool(self._match(TokenType.PUB))
        self._expect(TokenType.TRAIT)
        name = self._expect(TokenType.IDENT).literal
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        self._skip_newlines()
        methods = []
        while not self._check(TokenType.RBRACE):
            self._skip_newlines()
            if self._check(TokenType.RBRACE):
                break
            methods.append(self._parse_function_decl())
            self._skip_terminators()
        self._advance()  # }
        return TraitDecl(name=name, methods=methods, is_public=is_public)

    def _parse_impl_decl(self) -> ImplDecl:
        self._expect(TokenType.IMPL)
        trait_name = None
        target = self._expect(TokenType.IDENT).literal
        if self._match(TokenType.FOR):
            trait_name = target
            target = self._expect(TokenType.IDENT).literal
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        self._skip_newlines()
        methods = []
        while not self._check(TokenType.RBRACE):
            self._skip_newlines()
            if self._check(TokenType.RBRACE):
                break
            methods.append(self._parse_function_decl())
            self._skip_terminators()
        self._advance()  # }
        return ImplDecl(target=target, trait_name=trait_name, methods=methods)

    def _parse_enum_decl(self) -> EnumDecl:
        is_public = bool(self._match(TokenType.PUB))
        self._expect(TokenType.ENUM)
        name = self._expect(TokenType.IDENT).literal
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        self._skip_newlines()
        variants = []
        while not self._check(TokenType.RBRACE):
            v_name = self._expect(TokenType.IDENT).literal
            fields = []
            values = []
            if self._match(TokenType.LPAREN):
                while not self._check(TokenType.RPAREN):
                    fields.append(self._parse_type_annotation())
                    if not self._match(TokenType.COMMA):
                        break
                self._expect(TokenType.RPAREN)
            elif self._match(TokenType.ASSIGN):
                values.append(self._parse_expression())
                while self._match(TokenType.COMMA):
                    values.append(self._parse_expression())
            variants.append(EnumVariant(name=v_name, fields=fields, values=values))
            self._skip_terminators()
        self._advance()  # }
        return EnumDecl(name=name, variants=variants, is_public=is_public)

    def _parse_type_alias(self) -> TypeAliasDecl:
        is_public = bool(self._match(TokenType.PUB))
        self._expect(TokenType.TYPE)
        name = self._expect(TokenType.IDENT).literal
        self._expect(TokenType.ASSIGN)
        target = self._parse_type_annotation()
        return TypeAliasDecl(name=name, target=target, is_public=is_public)

    # ========== Type Annotations ==========

    def _parse_type_annotation(self) -> TypeAnnotation:
        name = self._expect(TokenType.IDENT).literal
        generics = []
        if self._match(TokenType.LBRACKET):
            while not self._check(TokenType.RBRACKET):
                generics.append(self._parse_type_annotation())
                if not self._match(TokenType.COMMA):
                    break
            self._expect(TokenType.RBRACKET)
        # Handle optional type (name?)
        if self._match(TokenType.QUESTION_MARK if hasattr(TokenType, 'QUESTION_MARK') else -1):
            return OptionalType(inner=TypeAnnotation(name=name, generics=generics))
        return TypeAnnotation(name=name, generics=generics)

    # ========== Statements ==========

    def _parse_statement(self) -> Optional[Statement]:
        tok = self._current()

        if tok.type == TokenType.LET:
            return self._parse_let_stmt()
        elif tok.type == TokenType.CONST:
            return self._parse_const_stmt()
        elif tok.type == TokenType.RETURN:
            return self._parse_return_stmt()
        elif tok.type == TokenType.BREAK:
            self._advance()
            return BreakStmt()
        elif tok.type == TokenType.CONTINUE:
            self._advance()
            return ContinueStmt()
        elif tok.type == TokenType.THROW:
            return self._parse_throw_stmt()
        elif tok.type == TokenType.DEFER:
            return self._parse_defer_stmt()
        elif tok.type == TokenType.IF:
            return self._parse_if_stmt()
        elif tok.type == TokenType.WHILE:
            return self._parse_while_stmt()
        elif tok.type == TokenType.FOR:
            return self._parse_for_stmt()
        elif tok.type == TokenType.MATCH:
            return self._parse_match_stmt()
        elif tok.type == TokenType.TRY:
            return self._parse_try_catch_stmt()
        elif tok.type == TokenType.LBRACE:
            return self._parse_block()
        else:
            return self._parse_expression_stmt()

    def _parse_let_stmt(self) -> LetStmt:
        self._expect(TokenType.LET)
        mutable = bool(self._match(TokenType.MUT))
        name = self._expect(TokenType.IDENT).literal
        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_annotation()
        value = None
        if self._match(TokenType.ASSIGN):
            value = self._parse_expression()
        return LetStmt(name=name, type_annotation=type_ann, value=value, mutable=mutable)

    def _parse_const_stmt(self) -> ConstStmt:
        self._expect(TokenType.CONST)
        name = self._expect(TokenType.IDENT).literal
        type_ann = None
        if self._match(TokenType.COLON):
            type_ann = self._parse_type_annotation()
        self._expect(TokenType.ASSIGN)
        value = self._parse_expression()
        return ConstStmt(name=name, type_annotation=type_ann, value=value)

    def _parse_return_stmt(self) -> ReturnStmt:
        self._expect(TokenType.RETURN)
        value = None
        if not self._check(TokenType.NEWLINE) and not self._check(TokenType.SEMICOLON) and not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            value = self._parse_expression()
        return ReturnStmt(value=value)

    def _parse_throw_stmt(self) -> ThrowStmt:
        self._expect(TokenType.THROW)
        value = self._parse_expression()
        return ThrowStmt(value=value)

    def _parse_defer_stmt(self) -> DeferStmt:
        self._expect(TokenType.DEFER)
        expr = self._parse_expression()
        if not isinstance(expr, CallExpr):
            raise ParseError("defer requires a function call", self._current())
        return DeferStmt(call=expr)

    def _parse_if_stmt(self) -> IfStmt:
        self._expect(TokenType.IF)
        condition = self._parse_expression()
        self._skip_newlines()
        consequence = self._parse_block()
        elif_clauses = []
        while self._match(TokenType.ELIF):
            elif_cond = self._parse_expression()
            self._skip_newlines()
            elif_body = self._parse_block()
            elif_clauses.append((elif_cond, elif_body))
        alternative = None
        if self._match(TokenType.ELSE):
            self._skip_newlines()
            alternative = self._parse_block()
        return IfStmt(condition=condition, consequence=consequence,
                     alternative=alternative, elif_clauses=elif_clauses)

    def _parse_while_stmt(self) -> WhileStmt:
        self._expect(TokenType.WHILE)
        condition = self._parse_expression()
        self._skip_newlines()
        body = self._parse_block()
        return WhileStmt(condition=condition, body=body)

    def _parse_for_stmt(self) -> Statement:
        self._expect(TokenType.FOR)
        # Check if it's a for-in loop
        if self._check(TokenType.IDENT) and self._check_ahead(TokenType.IN):
            name = self._advance().literal
            self._expect(TokenType.IN)
            iterable = self._parse_expression()
            self._skip_newlines()
            body = self._parse_block()
            return ForInStmt(name=name, iterable=iterable, body=body)
        # Traditional for loop
        init = self._parse_statement() if not self._check(TokenType.SEMICOLON) else None
        self._expect(TokenType.SEMICOLON)
        condition = self._parse_expression() if not self._check(TokenType.SEMICOLON) else None
        self._expect(TokenType.SEMICOLON)
        update = self._parse_expression() if not self._check(TokenType.LBRACE) else None
        self._skip_newlines()
        body = self._parse_block()
        return ForStmt(init=init, condition=condition, update=update, body=body)

    def _parse_match_stmt(self) -> MatchStmt:
        self._expect(TokenType.MATCH)
        subject = self._parse_expression()
        self._skip_newlines()
        self._expect(TokenType.LBRACE)
        self._skip_newlines()
        arms = []
        while not self._check(TokenType.RBRACE):
            pattern = self._parse_expression()
            guard = None
            if self._match(TokenType.WHERE):
                guard = self._parse_expression()
            self._expect(TokenType.FAT_ARROW)
            self._skip_newlines()
            body = self._parse_block()
            arms.append(MatchArm(pattern=pattern, guard=guard, body=body))
            self._skip_terminators()
        self._advance()  # }
        return MatchStmt(subject=subject, arms=arms)

    def _parse_try_catch_stmt(self) -> TryCatchStmt:
        self._expect(TokenType.TRY)
        self._skip_newlines()
        try_block = self._parse_block()
        catch_var = None
        catch_block = None
        if self._match(TokenType.CATCH):
            if self._check(TokenType.IDENT):
                catch_var = self._advance().literal
            self._skip_newlines()
            catch_block = self._parse_block()
        finally_block = None
        if self._match(TokenType.FINALLY):
            self._skip_newlines()
            finally_block = self._parse_block()
        return TryCatchStmt(try_block=try_block, catch_var=catch_var,
                          catch_block=catch_block, finally_block=finally_block)

    def _parse_block(self) -> Block:
        self._expect(TokenType.LBRACE)
        self._skip_newlines()
        stmts = []
        while not self._check(TokenType.RBRACE) and not self._check(TokenType.EOF):
            self._skip_newlines()
            if self._check(TokenType.RBRACE):
                break
            stmt = self._parse_statement()
            if stmt:
                stmts.append(stmt)
            self._skip_terminators()
        self._expect(TokenType.RBRACE)
        return Block(statements=stmts)

    def _parse_expression_stmt(self) -> ExpressionStmt:
        expr = self._parse_expression()
        # Check for assignment
        if self._check(TokenType.ASSIGN):
            self._advance()
            value = self._parse_expression()
            return AssignStmt(target=expr, value=value)
        # Check for compound assignment
        compound_ops = {
            TokenType.PLUS_ASSIGN: "+=",
            TokenType.MINUS_ASSIGN: "-=",
            TokenType.STAR_ASSIGN: "*=",
            TokenType.SLASH_ASSIGN: "/=",
        }
        for tok_type, op in compound_ops.items():
            if self._check(tok_type):
                self._advance()
                value = self._parse_expression()
                return CompoundAssignStmt(target=expr, operator=op, value=value)
        return ExpressionStmt(expression=expr)

    # ========== Expressions (Precedence Climbing) ==========

    def _parse_expression(self) -> Expression:
        return self._parse_or()

    def _parse_or(self) -> Expression:
        left = self._parse_and()
        while self._match(TokenType.OR):
            right = self._parse_and()
            left = InfixExpr(left=left, operator="||", right=right)
        return left

    def _parse_and(self) -> Expression:
        left = self._parse_equality()
        while self._match(TokenType.AND):
            right = self._parse_equality()
            left = InfixExpr(left=left, operator="&&", right=right)
        return left

    def _parse_equality(self) -> Expression:
        left = self._parse_comparison()
        while True:
            if self._match(TokenType.EQ):
                right = self._parse_comparison()
                left = InfixExpr(left=left, operator="==", right=right)
            elif self._match(TokenType.NOT_EQ):
                right = self._parse_comparison()
                left = InfixExpr(left=left, operator="!=", right=right)
            else:
                break
        return left

    def _parse_comparison(self) -> Expression:
        left = self._parse_bitwise()
        while True:
            if self._match(TokenType.LT):
                right = self._parse_bitwise()
                left = InfixExpr(left=left, operator="<", right=right)
            elif self._match(TokenType.GT):
                right = self._parse_bitwise()
                left = InfixExpr(left=left, operator=">", right=right)
            elif self._match(TokenType.LTE):
                right = self._parse_bitwise()
                left = InfixExpr(left=left, operator="<=", right=right)
            elif self._match(TokenType.GTE):
                right = self._parse_bitwise()
                left = InfixExpr(left=left, operator=">=", right=right)
            else:
                break
        return left

    def _parse_bitwise(self) -> Expression:
        left = self._parse_range()
        while True:
            if self._match(TokenType.BIT_AND):
                right = self._parse_range()
                left = InfixExpr(left=left, operator="&", right=right)
            elif self._match(TokenType.BIT_OR):
                right = self._parse_range()
                left = InfixExpr(left=left, operator="|", right=right)
            elif self._match(TokenType.BIT_XOR):
                right = self._parse_range()
                left = InfixExpr(left=left, operator="^", right=right)
            elif self._match(TokenType.LSHIFT):
                right = self._parse_range()
                left = InfixExpr(left=left, operator="<<", right=right)
            elif self._match(TokenType.RSHIFT):
                right = self._parse_range()
                left = InfixExpr(left=left, operator=">>", right=right)
            else:
                break
        return left

    def _parse_range(self) -> Expression:
        left = self._parse_addition()
        if self._match(TokenType.DOTDOT if hasattr(TokenType, 'DOTDOT') else -1):
            right = self._parse_addition()
            return RangeExpr(start=left, end=right, inclusive=False)
        return left

    def _parse_addition(self) -> Expression:
        left = self._parse_multiplication()
        while True:
            if self._match(TokenType.PLUS):
                right = self._parse_multiplication()
                left = InfixExpr(left=left, operator="+", right=right)
            elif self._match(TokenType.MINUS):
                right = self._parse_multiplication()
                left = InfixExpr(left=left, operator="-", right=right)
            else:
                break
        return left

    def _parse_multiplication(self) -> Expression:
        left = self._parse_power()
        while True:
            if self._match(TokenType.STAR):
                right = self._parse_power()
                left = InfixExpr(left=left, operator="*", right=right)
            elif self._match(TokenType.SLASH):
                right = self._parse_power()
                left = InfixExpr(left=left, operator="/", right=right)
            elif self._match(TokenType.PERCENT):
                right = self._parse_power()
                left = InfixExpr(left=left, operator="%", right=right)
            else:
                break
        return left

    def _parse_power(self) -> Expression:
        left = self._parse_unary()
        if self._match(TokenType.POWER):
            right = self._parse_unary()
            left = InfixExpr(left=left, operator="**", right=right)
        return left

    def _parse_unary(self) -> Expression:
        if self._match(TokenType.NOT):
            right = self._parse_unary()
            return PrefixExpr(operator="!", right=right)
        if self._match(TokenType.MINUS):
            right = self._parse_unary()
            return PrefixExpr(operator="-", right=right)
        if self._match(TokenType.BIT_NOT):
            right = self._parse_unary()
            return PrefixExpr(operator="~", right=right)
        if self._check(TokenType.SPAWN):
            return self._parse_spawn_expr()
        if self._check(TokenType.AWAIT):
            return self._parse_await_expr()
        if self._check(TokenType.CHAN):
            return self._parse_chan_expr()
        return self._parse_postfix()

    def _parse_spawn_expr(self) -> SpawnExpr:
        self._expect(TokenType.SPAWN)
        # spawn { ... } - spawn a block
        if self._check(TokenType.LBRACE):
            block = self._parse_block()
            fn_expr = LambdaExpr(params=[], body=block)
            return SpawnExpr(call=CallExpr(function=fn_expr, arguments=[]))
        # spawn fn(params) { block } - spawn a function literal with block body
        if self._check(TokenType.FN):
            saved = self.position
            try:
                lambda_expr = self._parse_spawn_lambda()
                return SpawnExpr(call=CallExpr(function=lambda_expr, arguments=[]))
            except ParseError:
                self.position = saved
        # spawn fn_call() - spawn an existing function call
        expr = self._parse_postfix()
        if isinstance(expr, CallExpr):
            return SpawnExpr(call=expr)
        raise ParseError("spawn requires a function call or block", self._current())

    def _parse_spawn_lambda(self) -> LambdaExpr:
        """Parse fn(params) { block } syntax for spawn (no fat arrow required)."""
        self._expect(TokenType.FN)
        self._expect(TokenType.LPAREN)
        params = self._parse_params()
        self._expect(TokenType.RPAREN)
        return_type = None
        if self._match(TokenType.ARROW):
            return_type = self._parse_type_annotation()
        # Accept both { block } and => { block } / => expr
        if self._match(TokenType.FAT_ARROW):
            if self._check(TokenType.LBRACE):
                body = self._parse_block()
            else:
                expr = self._parse_expression()
                body = Block(statements=[ReturnStmt(value=expr)])
        else:
            body = self._parse_block()
        return LambdaExpr(params=params, body=body, return_type=return_type)

    def _parse_await_expr(self) -> AwaitExpr:
        self._expect(TokenType.AWAIT)
        expr = self._parse_postfix()
        return AwaitExpr(expr=expr)

    def _parse_chan_expr(self) -> ChanExpr:
        self._expect(TokenType.CHAN)
        element_type = None
        capacity = None
        if self._match(TokenType.LBRACKET):
            element_type = self._parse_type_annotation()
            self._expect(TokenType.RBRACKET)
        if self._match(TokenType.LPAREN):
            capacity = self._parse_expression()
            self._expect(TokenType.RPAREN)
        return ChanExpr(element_type=element_type, capacity=capacity)

    def _parse_postfix(self) -> Expression:
        expr = self._parse_primary()
        while True:
            if self._match(TokenType.DOT):
                member = self._expect(TokenType.IDENT).literal
                if self._match(TokenType.LPAREN):
                    # Method call
                    args = self._parse_arguments()
                    self._expect(TokenType.RPAREN)
                    expr = MethodCallExpr(obj=expr, method=member, arguments=args)
                else:
                    expr = MemberExpr(obj=expr, member=member)
            elif self._match(TokenType.LPAREN):
                # Function call
                args = self._parse_arguments()
                self._expect(TokenType.RPAREN)
                expr = CallExpr(function=expr, arguments=args)
            elif self._match(TokenType.LBRACKET):
                # Index or slice
                if self._check(TokenType.COLON):
                    # Slice [:]
                    self._advance()
                    end = None
                    if not self._check(TokenType.RBRACKET):
                        end = self._parse_expression()
                    self._expect(TokenType.RBRACKET)
                    expr = SliceExpr(obj=expr, start=None, end=end, step=None)
                else:
                    index = self._parse_expression()
                    if self._match(TokenType.COLON):
                        # Slice [start:end] or [start:end:step]
                        end = None
                        step = None
                        if not self._check(TokenType.COLON) and not self._check(TokenType.RBRACKET):
                            end = self._parse_expression()
                        if self._match(TokenType.COLON):
                            if not self._check(TokenType.RBRACKET):
                                step = self._parse_expression()
                        self._expect(TokenType.RBRACKET)
                        expr = SliceExpr(obj=expr, start=index, end=end, step=step)
                    else:
                        self._expect(TokenType.RBRACKET)
                        expr = IndexExpr(obj=expr, index=index)
            elif self._match(TokenType.LARROW if hasattr(TokenType, 'LARROW') else -1):
                # Channel send: ch <- value (we'll use <- as a special token)
                pass
            else:
                break
        return expr

    def _parse_arguments(self) -> list[Expression]:
        args = []
        self._skip_newlines()
        while not self._check(TokenType.RPAREN) and not self._check(TokenType.EOF):
            args.append(self._parse_expression())
            self._skip_newlines()
            if not self._match(TokenType.COMMA):
                break
            self._skip_newlines()
        return args

    def _parse_primary(self) -> Expression:
        tok = self._current()

        # Literals
        if tok.type == TokenType.INT:
            self._advance()
            # Handle hex/binary
            if tok.literal.startswith("0x") or tok.literal.startswith("0X"):
                return IntLiteral(value=int(tok.literal.replace("_", ""), 16))
            elif tok.literal.startswith("0b") or tok.literal.startswith("0B"):
                return IntLiteral(value=int(tok.literal.replace("_", ""), 2))
            return IntLiteral(value=int(tok.literal.replace("_", "")))
        elif tok.type == TokenType.FLOAT:
            self._advance()
            return FloatLiteral(value=float(tok.literal.replace("_", "")))
        elif tok.type == TokenType.STRING:
            self._advance()
            return StringLiteral(value=tok.literal)
        elif tok.type == TokenType.TRUE:
            self._advance()
            return BoolLiteral(value=True)
        elif tok.type == TokenType.FALSE:
            self._advance()
            return BoolLiteral(value=False)
        elif tok.type == TokenType.NONE:
            self._advance()
            return NoneLiteral()
        # Identifier
        elif tok.type == TokenType.IDENT:
            self._advance()
            return Identifier(name=tok.literal)
        # Grouped expression
        elif tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            # Check for tuple
            if self._match(TokenType.COMMA):
                elements = [expr]
                while not self._check(TokenType.RPAREN):
                    elements.append(self._parse_expression())
                    if not self._match(TokenType.COMMA):
                        break
                self._expect(TokenType.RPAREN)
                return TupleLiteral(elements=elements)
            self._expect(TokenType.RPAREN)
            return expr
        # Array literal
        elif tok.type == TokenType.LBRACKET:
            self._advance()
            elements = []
            self._skip_newlines()
            while not self._check(TokenType.RBRACKET) and not self._check(TokenType.EOF):
                elements.append(self._parse_expression())
                self._skip_newlines()
                if not self._match(TokenType.COMMA):
                    self._skip_newlines()
                    break
                self._skip_newlines()
            self._expect(TokenType.RBRACKET)
            return ArrayLiteral(elements=elements)
        # Dict literal
        elif tok.type == TokenType.LBRACE:
            # Check if it's a dict or a block
            # Dict: {key: value, ...}
            # Block: {stmt; stmt; ...}
            # Heuristic: look ahead for colon after first expression
            saved = self.position
            self._advance()  # {
            self._skip_newlines()
            if self._check(TokenType.RBRACE):
                self._advance()
                return DictLiteral(pairs=[])
            # Try to parse as dict
            try:
                first_expr = self._parse_expression()
                if self._check(TokenType.COLON):
                    # It's a dict
                    self._advance()  # :
                    first_val = self._parse_expression()
                    pairs = [(first_expr, first_val)]
                    self._skip_newlines()
                    while self._match(TokenType.COMMA):
                        self._skip_newlines()
                        if self._check(TokenType.RBRACE):
                            break
                        key = self._parse_expression()
                        self._expect(TokenType.COLON)
                        val = self._parse_expression()
                        pairs.append((key, val))
                        self._skip_newlines()
                    self._expect(TokenType.RBRACE)
                    return DictLiteral(pairs=pairs)
                else:
                    # Not a dict, restore and parse as block
                    self.position = saved
                    return self._parse_block()
            except ParseError:
                self.position = saved
                return self._parse_block()
        # Lambda: |params| => body or fn(params) => body
        elif tok.type == TokenType.FN:
            return self._parse_lambda()

        raise ParseError(f"Unexpected token {tok.type.name} ({tok.literal!r})", tok)

    def _parse_lambda(self) -> LambdaExpr:
        self._expect(TokenType.FN)
        self._expect(TokenType.LPAREN)
        params = self._parse_params()
        self._expect(TokenType.RPAREN)
        return_type = None
        if self._match(TokenType.ARROW):
            return_type = self._parse_type_annotation()
        # Support both fn(params) { block } and fn(params) => expr/block
        if self._check(TokenType.LBRACE):
            body = self._parse_block()
        elif self._match(TokenType.FAT_ARROW):
            # Single expression body or block
            if self._check(TokenType.LBRACE):
                body = self._parse_block()
            else:
                expr = self._parse_expression()
                body = Block(statements=[ReturnStmt(value=expr)])
        else:
            raise ParseError("Expected '=>' or '{' after function parameters", self._current())
        return LambdaExpr(params=params, body=body, return_type=return_type)
