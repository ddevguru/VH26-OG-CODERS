from typing import List, Optional, Union
import tree_sitter

from packages.common.models import Span
from packages.parser.parser import JavaParser
from packages.ast.nodes import (
    ASTNode,
    CompilationUnit,
    ClassDeclaration,
    MethodDeclaration,
    Parameter,
    Statement,
    BlockStmt,
    ExpressionStmt,
    LocalVarDeclStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
    EnhancedForStmt,
    TryStmt,
    TryWithResourcesStmt,
    CatchClause,
    ReturnStmt,
    ThrowStmt,
    BreakStmt,
    ContinueStmt,
    Expression,
    LiteralExpr,
    IdentifierExpr,
    MemberAccessExpr,
    MethodInvocationExpr,
    ObjectCreationExpr,
    AssignmentExpr,
    BinaryExpr,
    CastExpr,
    UnknownExpr,
)


class ASTBuilder:
    """Transforms tree-sitter CST nodes into LeakGuard normalized Java AST dataclasses."""

    def __init__(self, source_bytes: bytes) -> None:
        self.source_bytes = source_bytes

    def get_text(self, node: tree_sitter.Node) -> str:
        """Extracts UTF-8 text from source bytes for a node."""
        return self.source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()

    def get_span(self, node: tree_sitter.Node) -> Span:
        return JavaParser.get_span(node)

    def build_compilation_unit(self, root_node: tree_sitter.Node) -> CompilationUnit:
        span = self.get_span(root_node)
        package_name: Optional[str] = None
        imports: List[str] = []
        types: List[ClassDeclaration] = []

        for child in root_node.named_children:
            if child.type == "package_declaration":
                package_name = self.get_text(child)
            elif child.type == "import_declaration":
                imports.append(self.get_text(child))
            elif child.type in ("class_declaration", "interface_declaration", "enum_declaration", "record_declaration"):
                class_decl = self.build_class_declaration(child)
                if class_decl:
                    types.append(class_decl)

        return CompilationUnit(
            span=span,
            package_name=package_name,
            imports=imports,
            types=types,
        )

    def build_class_declaration(self, node: tree_sitter.Node) -> Optional[ClassDeclaration]:
        span = self.get_span(node)
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node) if name_node else "AnonymousClass"

        methods: List[MethodDeclaration] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.named_children:
                if child.type in ("method_declaration", "constructor_declaration"):
                    method_decl = self.build_method_declaration(child)
                    if method_decl:
                        methods.append(method_decl)

        return ClassDeclaration(span=span, name=name, methods=methods)

    def build_method_declaration(self, node: tree_sitter.Node) -> Optional[MethodDeclaration]:
        span = self.get_span(node)
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node) if name_node else ("<init>" if node.type == "constructor_declaration" else "unknown")

        type_node = node.child_by_field_name("type")
        return_type = self.get_text(type_node) if type_node else ("void" if node.type == "method_declaration" else "void")

        parameters: List[Parameter] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param_child in params_node.named_children:
                if param_child.type in ("formal_parameter", "spread_parameter"):
                    param_type_node = param_child.child_by_field_name("type")
                    param_name_node = param_child.child_by_field_name("name")
                    param_type = self.get_text(param_type_node) if param_type_node else "Object"
                    param_name = self.get_text(param_name_node) if param_name_node else "arg"
                    parameters.append(Parameter(span=self.get_span(param_child), type_name=param_type, name=param_name))

        throws_types: List[str] = []
        for child in node.children:
            if child.type == "throws":
                for throw_child in child.named_children:
                    throws_types.append(self.get_text(throw_child))

        body_node = node.child_by_field_name("body")
        body_stmt: Optional[BlockStmt] = None
        if body_node and body_node.type == "block":
            body_stmt = self.build_block_statement(body_node)

        return MethodDeclaration(
            span=span,
            name=name,
            return_type=return_type,
            parameters=parameters,
            body=body_stmt,
            throws_types=throws_types,
        )

    # --- Statement Construction ---

    def build_statement(self, node: tree_sitter.Node) -> Statement:
        span = self.get_span(node)

        if node.type == "block":
            return self.build_block_statement(node)

        elif node.type == "expression_statement":
            expr_child = node.named_children[0] if node.named_children else None
            expr = self.build_expression(expr_child) if expr_child else UnknownExpr(span=span, raw_text=self.get_text(node))
            return ExpressionStmt(span=span, expression=expr)

        elif node.type == "local_variable_declaration":
            return self.build_local_variable_declaration(node)

        elif node.type == "if_statement":
            cond_node = node.child_by_field_name("condition")
            then_node = node.child_by_field_name("consequence")
            else_node = node.child_by_field_name("alternative")

            cond_expr = self.build_expression(cond_node) if cond_node else UnknownExpr(span=span, raw_text="")
            then_stmt = self.build_statement(then_node) if then_node else BlockStmt(span=span)
            else_stmt = self.build_statement(else_node) if else_node else None

            return IfStmt(span=span, condition=cond_expr, then_branch=then_stmt, else_branch=else_stmt)

        elif node.type == "while_statement":
            cond_node = node.child_by_field_name("condition")
            body_node = node.child_by_field_name("body")
            cond_expr = self.build_expression(cond_node) if cond_node else UnknownExpr(span=span, raw_text="")
            body_stmt = self.build_statement(body_node) if body_node else BlockStmt(span=span)
            return WhileStmt(span=span, condition=cond_expr, body=body_stmt)

        elif node.type == "for_statement":
            init_node = node.child_by_field_name("init")
            cond_node = node.child_by_field_name("condition")
            update_node = node.child_by_field_name("update")
            body_node = node.child_by_field_name("body")

            init_ast = self.build_statement(init_node) if init_node else None
            cond_expr = self.build_expression(cond_node) if cond_node else None
            update_ast = self.build_statement(update_node) if update_node else None
            body_stmt = self.build_statement(body_node) if body_node else BlockStmt(span=span)

            return ForStmt(span=span, init=init_ast, condition=cond_expr, update=update_ast, body=body_stmt)

        elif node.type == "enhanced_for_statement":
            type_node = node.child_by_field_name("type")
            name_node = node.child_by_field_name("name")
            value_node = node.child_by_field_name("value")
            body_node = node.child_by_field_name("body")

            var_type = self.get_text(type_node) if type_node else "var"
            var_name = self.get_text(name_node) if name_node else "elem"
            iterable = self.build_expression(value_node) if value_node else UnknownExpr(span=span, raw_text="")
            body_stmt = self.build_statement(body_node) if body_node else BlockStmt(span=span)

            return EnhancedForStmt(span=span, var_type=var_type, var_name=var_name, iterable=iterable, body=body_stmt)

        elif node.type == "try_statement" or node.type == "try_with_resources_statement":
            return self.build_try_statement(node)

        elif node.type == "return_statement":
            expr_child = node.named_children[0] if node.named_children else None
            expr = self.build_expression(expr_child) if expr_child else None
            return ReturnStmt(span=span, expression=expr)

        elif node.type == "throw_statement":
            expr_child = node.named_children[0] if node.named_children else None
            expr = self.build_expression(expr_child) if expr_child else UnknownExpr(span=span, raw_text="")
            return ThrowStmt(span=span, expression=expr)

        elif node.type == "break_statement":
            label_node = node.named_children[0] if node.named_children else None
            return BreakStmt(span=span, label=self.get_text(label_node) if label_node else None)

        elif node.type == "continue_statement":
            label_node = node.named_children[0] if node.named_children else None
            return ContinueStmt(span=span, label=self.get_text(label_node) if label_node else None)

        # Generic fallback statement
        return ExpressionStmt(span=span, expression=self.build_expression(node))

    def build_block_statement(self, node: tree_sitter.Node) -> BlockStmt:
        span = self.get_span(node)
        statements: List[Statement] = []
        for child in node.named_children:
            statements.append(self.build_statement(child))
        return BlockStmt(span=span, statements=statements)

    def build_local_variable_declaration(self, node: tree_sitter.Node) -> LocalVarDeclStmt:
        span = self.get_span(node)

        if node.type == "resource":
            type_name = "var"
            var_name = "var"
            initializer: Optional[Expression] = None
            named = node.named_children
            if len(named) >= 1 and named[0].type in ("type_identifier", "generic_type", "scoped_type_identifier", "identifier"):
                type_name = self.get_text(named[0])
            if len(named) >= 2 and named[1].type in ("identifier", "variable_declarator"):
                var_name = self.get_text(named[1])
            if len(named) >= 3:
                initializer = self.build_expression(named[2])
            return LocalVarDeclStmt(span=span, type_name=type_name, var_name=var_name, initializer=initializer)

        type_node = node.child_by_field_name("type")
        type_name = self.get_text(type_node) if type_node else "var"

        var_name = "var"
        initializer = None

        declarators = [c for c in node.children if c.type in ("variable_declarator", "resource")]
        if not declarators:
            declarators = [c for c in node.named_children if c.type == "variable_declarator"]

        if declarators:
            decl = declarators[0]
            name_node = decl.child_by_field_name("name")
            value_node = decl.child_by_field_name("value")
            if name_node:
                var_name = self.get_text(name_node)
            elif decl.named_children:
                ids = [c for c in decl.named_children if c.type in ("identifier", "type_identifier")]
                if len(ids) >= 2:
                    var_name = self.get_text(ids[1])
                elif len(ids) == 1:
                    var_name = self.get_text(ids[0])

            if value_node:
                initializer = self.build_expression(value_node)

        return LocalVarDeclStmt(span=span, type_name=type_name, var_name=var_name, initializer=initializer)

    def build_try_statement(self, node: tree_sitter.Node) -> Statement:
        span = self.get_span(node)
        resources: List[LocalVarDeclStmt] = []
        
        # Check resources header for try-with-resources
        resources_node = node.child_by_field_name("resources")
        if resources_node:
            for res_child in resources_node.named_children:
                if res_child.type in ("resource", "local_variable_declaration"):
                    resources.append(self.build_local_variable_declaration(res_child))

        body_node = node.child_by_field_name("body")
        body_stmt = self.build_block_statement(body_node) if body_node else BlockStmt(span=span)

        catch_clauses: List[CatchClause] = []
        finally_block: Optional[BlockStmt] = None

        for child in node.named_children:
            if child.type == "catch_clause":
                catch_span = self.get_span(child)
                param_node = child.child_by_field_name("formal_parameter") or child.child_by_field_name("parameter")
                param_type = "Exception"
                param_name = "e"
                if param_node:
                    pt_node = param_node.child_by_field_name("type")
                    pn_node = param_node.child_by_field_name("name")
                    if pt_node:
                        param_type = self.get_text(pt_node)
                    if pn_node:
                        param_name = self.get_text(pn_node)

                catch_body = child.child_by_field_name("body")
                catch_body_stmt = self.build_block_statement(catch_body) if catch_body else BlockStmt(span=catch_span)

                catch_clauses.append(CatchClause(span=catch_span, param_type=param_type, param_name=param_name, body=catch_body_stmt))

            elif child.type == "finally_clause":
                finally_body = child.named_children[0] if child.named_children else None
                if finally_body and finally_body.type == "block":
                    finally_block = self.build_block_statement(finally_body)
                elif finally_body:
                    finally_block = BlockStmt(span=self.get_span(finally_body), statements=[self.build_statement(finally_body)])

        if resources or node.type == "try_with_resources_statement":
            return TryWithResourcesStmt(
                span=span,
                resources=resources,
                body=body_stmt,
                catch_clauses=catch_clauses,
                finally_block=finally_block,
            )

        return TryStmt(
            span=span,
            body=body_stmt,
            catch_clauses=catch_clauses,
            finally_block=finally_block,
        )

    # --- Expression Construction ---

    def build_expression(self, node: Optional[tree_sitter.Node]) -> Expression:
        if node is None:
            return UnknownExpr(span=Span(start=None, end=None), raw_text="")  # type: ignore

        span = self.get_span(node)

        if node.type in ("identifier", "type_identifier"):
            return IdentifierExpr(span=span, name=self.get_text(node))

        elif node.type in ("decimal_integer_literal", "string_literal", "boolean_literal", "null_literal", "character_literal", "decimal_floating_point_literal"):
            return LiteralExpr(span=span, value=self.get_text(node), literal_type=node.type)

        elif node.type == "method_invocation":
            target_node = node.child_by_field_name("object")
            name_node = node.child_by_field_name("name")
            args_node = node.child_by_field_name("arguments")

            target_expr = self.build_expression(target_node) if target_node else None
            method_name = self.get_text(name_node) if name_node else "unknown"

            arguments: List[Expression] = []
            if args_node:
                for arg_child in args_node.named_children:
                    arguments.append(self.build_expression(arg_child))

            return MethodInvocationExpr(span=span, target=target_expr, method_name=method_name, arguments=arguments)

        elif node.type == "object_creation_expression":
            type_node = node.child_by_field_name("type")
            args_node = node.child_by_field_name("arguments")

            type_name = self.get_text(type_node) if type_node else "Object"
            arguments = []
            if args_node:
                for arg_child in args_node.named_children:
                    arguments.append(self.build_expression(arg_child))

            return ObjectCreationExpr(span=span, type_name=type_name, arguments=arguments)

        elif node.type == "assignment_expression":
            left_node = node.child_by_field_name("left")
            right_node = node.child_by_field_name("right")

            left_expr = self.build_expression(left_node) if left_node else UnknownExpr(span=span, raw_text="")
            right_expr = self.build_expression(right_node) if right_node else UnknownExpr(span=span, raw_text="")

            return AssignmentExpr(span=span, target=left_expr, value=right_expr)

        elif node.type == "binary_expression":
            left_node = node.child_by_field_name("left")
            op_node = node.child_by_field_name("operator")
            right_node = node.child_by_field_name("right")

            left_expr = self.build_expression(left_node) if left_node else UnknownExpr(span=span, raw_text="")
            op_text = self.get_text(op_node) if op_node else "=="
            right_expr = self.build_expression(right_node) if right_node else UnknownExpr(span=span, raw_text="")

            return BinaryExpr(span=span, left=left_expr, operator=op_text, right=right_expr)

        elif node.type == "field_access":
            obj_node = node.child_by_field_name("object")
            field_node = node.child_by_field_name("field")
            obj_expr = self.build_expression(obj_node) if obj_node else UnknownExpr(span=span, raw_text="")
            field_name = self.get_text(field_node) if field_node else "field"
            return MemberAccessExpr(span=span, object_expr=obj_expr, member_name=field_name)

        elif node.type == "cast_expression":
            type_node = node.child_by_field_name("type")
            value_node = node.child_by_field_name("value")
            target_type = self.get_text(type_node) if type_node else "Object"
            val_expr = self.build_expression(value_node) if value_node else UnknownExpr(span=span, raw_text="")
            return CastExpr(span=span, target_type=target_type, expression=val_expr)

        elif node.type == "parenthesized_expression":
            child = node.named_children[0] if node.named_children else None
            return self.build_expression(child)

        return UnknownExpr(span=span, raw_text=self.get_text(node))
