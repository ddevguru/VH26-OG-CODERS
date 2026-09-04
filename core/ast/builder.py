from typing import List, Optional, Tuple, Dict
import tree_sitter

from core.common.models import Span
from core.parser.parser import PythonParser
from core.ast.nodes import (
    ASTNode,
    Module,
    ClassDeclaration,
    FunctionDeclaration,
    Parameter,
    Statement,
    BlockStmt,
    ExpressionStmt,
    AssignmentStmt,
    IfStmt,
    WhileStmt,
    ForStmt,
    WithStmt,
    WithItem,
    TryStmt,
    ExceptHandler,
    ReturnStmt,
    RaiseStmt,
    BreakStmt,
    ContinueStmt,
    Expression,
    LiteralExpr,
    IdentifierExpr,
    AttributeAccessExpr,
    CallExpr,
    BinaryExpr,
    UnknownExpr,
)


class ASTBuilder:
    """Transforms tree-sitter Python CST nodes into LeakGuard normalized Python AST dataclasses."""

    def __init__(self, source_bytes: bytes) -> None:
        self.source_bytes = source_bytes

    def get_text(self, node: tree_sitter.Node) -> str:
        return self.source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace").strip()

    def get_span(self, node: tree_sitter.Node) -> Span:
        return PythonParser.get_span(node)

    def build_module(self, root_node: tree_sitter.Node) -> Module:
        span = self.get_span(root_node)
        statements: List[Statement] = []
        functions: List[FunctionDeclaration] = []
        classes: List[ClassDeclaration] = []

        for child in root_node.children:
            if child.type == "function_definition":
                func = self.build_function_declaration(child)
                if func:
                    functions.append(func)
            elif child.type == "class_definition":
                cls = self.build_class_declaration(child)
                if cls:
                    classes.append(cls)
            else:
                stmt = self.build_statement(child)
                if stmt:
                    statements.append(stmt)

        return Module(span=span, statements=statements, functions=functions, classes=classes)

    def build_class_declaration(self, node: tree_sitter.Node) -> Optional[ClassDeclaration]:
        span = self.get_span(node)
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node) if name_node else "AnonymousClass"

        methods: List[FunctionDeclaration] = []
        body_node = node.child_by_field_name("body")
        if body_node:
            for child in body_node.children:
                if child.type == "function_definition":
                    m = self.build_function_declaration(child)
                    if m:
                        methods.append(m)

        return ClassDeclaration(span=span, name=name, methods=methods)

    def build_function_declaration(self, node: tree_sitter.Node) -> Optional[FunctionDeclaration]:
        span = self.get_span(node)
        name_node = node.child_by_field_name("name")
        name = self.get_text(name_node) if name_node else "anonymous"

        is_async = node.type == "async_function_definition"

        parameters: List[Parameter] = []
        params_node = node.child_by_field_name("parameters")
        if params_node:
            for param_child in params_node.named_children:
                p_name = self.get_text(param_child)
                parameters.append(Parameter(span=self.get_span(param_child), name=p_name))

        body_node = node.child_by_field_name("body")
        body_stmt: Optional[BlockStmt] = None
        if body_node:
            body_stmt = self.build_block_statement(body_node)

        return FunctionDeclaration(
            span=span,
            name=name,
            parameters=parameters,
            body=body_stmt,
            is_async=is_async,
        )

    def build_statement(self, node: tree_sitter.Node) -> Statement:
        span = self.get_span(node)

        if node.type == "block":
            return self.build_block_statement(node)

        elif node.type == "expression_statement":
            expr_child = node.named_children[0] if node.named_children else None
            if expr_child and expr_child.type == "assignment":
                return self.build_statement(expr_child)
            expr = self.build_expression(expr_child) if expr_child else UnknownExpr(span=span, raw_text=self.get_text(node))
            return ExpressionStmt(span=span, expression=expr)

        elif node.type == "assignment":
            left_node = node.child_by_field_name("left") or (node.children[0] if node.children else None)
            right_node = node.child_by_field_name("right") or (node.children[-1] if len(node.children) > 1 else None)
            target = self.build_expression(left_node)
            value = self.build_expression(right_node)
            return AssignmentStmt(span=span, target=target, value=value)

        elif node.type == "if_statement":
            cond_node = node.child_by_field_name("condition")
            consequence = node.child_by_field_name("consequence")
            cond_expr = self.build_expression(cond_node) if cond_node else UnknownExpr(span=span, raw_text="")
            then_stmt = self.build_statement(consequence) if consequence else BlockStmt(span=span)

            else_stmt: Optional[Statement] = None
            elif_branches: List[Tuple[Expression, Statement]] = []

            for child in node.children:
                if child.type == "elif_clause":
                    elif_cond = child.child_by_field_name("condition")
                    elif_body = child.child_by_field_name("consequence")
                    elif_cond_expr = self.build_expression(elif_cond) if elif_cond else UnknownExpr(span=span, raw_text="")
                    elif_body_stmt = self.build_statement(elif_body) if elif_body else BlockStmt(span=span)
                    elif_branches.append((elif_cond_expr, elif_body_stmt))
                elif child.type == "else_clause":
                    else_body = child.child_by_field_name("body") or (child.named_children[0] if child.named_children else None)
                    if else_body:
                        else_stmt = self.build_statement(else_body)

            return IfStmt(span=span, condition=cond_expr, then_branch=then_stmt, elif_branches=elif_branches, else_branch=else_stmt)

        elif node.type == "while_statement":
            cond_node = node.child_by_field_name("condition")
            body_node = node.child_by_field_name("body")
            cond_expr = self.build_expression(cond_node) if cond_node else UnknownExpr(span=span, raw_text="")
            body_stmt = self.build_statement(body_node) if body_node else BlockStmt(span=span)
            return WhileStmt(span=span, condition=cond_expr, body=body_stmt)

        elif node.type == "for_statement":
            left_node = node.child_by_field_name("left")
            right_node = node.child_by_field_name("right")
            body_node = node.child_by_field_name("body")

            target = self.build_expression(left_node)
            iterable = self.build_expression(right_node)
            body_stmt = self.build_statement(body_node) if body_node else BlockStmt(span=span)

            return ForStmt(span=span, target=target, iterable=iterable, body=body_stmt)

        elif node.type in ("with_statement", "async_with_statement"):
            return self.build_with_statement(node)

        elif node.type == "try_statement":
            return self.build_try_statement(node)

        elif node.type == "return_statement":
            expr_child = node.named_children[0] if node.named_children else None
            return ReturnStmt(span=span, expression=self.build_expression(expr_child) if expr_child else None)

        elif node.type == "raise_statement":
            expr_child = node.named_children[0] if node.named_children else None
            return RaiseStmt(span=span, expression=self.build_expression(expr_child) if expr_child else None)

        elif node.type == "break_statement":
            return BreakStmt(span=span)

        elif node.type == "continue_statement":
            return ContinueStmt(span=span)

        return ExpressionStmt(span=span, expression=self.build_expression(node))

    def build_block_statement(self, node: tree_sitter.Node) -> BlockStmt:
        span = self.get_span(node)
        statements: List[Statement] = []
        for child in node.children:
            if child.type not in (":", "comment", "indent", "dedent"):
                stmt = self.build_statement(child)
                if stmt:
                    statements.append(stmt)
        return BlockStmt(span=span, statements=statements)

    def build_with_statement(self, node: tree_sitter.Node) -> WithStmt:
        span = self.get_span(node)
        items: List[WithItem] = []

        # Find with_clause or with_item
        for child in node.children:
            if child.type == "with_clause":
                for item_child in child.children:
                    if item_child.type == "with_item":
                        items.append(self.build_with_item(item_child))
            elif child.type == "with_item":
                items.append(self.build_with_item(child))

        body_node = node.child_by_field_name("body")
        body_stmt = self.build_block_statement(body_node) if body_node else BlockStmt(span=span)

        return WithStmt(span=span, items=items, body=body_stmt, is_async=node.type == "async_with_statement")

    def build_with_item(self, node: tree_sitter.Node) -> WithItem:
        span = self.get_span(node)
        ctx_expr: Expression = UnknownExpr(span=span, raw_text=self.get_text(node))
        opt_var: Optional[Expression] = None

        if node.named_children:
            first = node.named_children[0]
            if first.type == "as_pattern":
                # as_pattern: call / expr, 'as', target
                call_child = first.children[0] if first.children else None
                var_child = first.children[2] if len(first.children) >= 3 else None
                ctx_expr = self.build_expression(call_child)
                opt_var = self.build_expression(var_child)
            else:
                ctx_expr = self.build_expression(first)

        return WithItem(span=span, context_expr=ctx_expr, optional_vars=opt_var)

    def build_try_statement(self, node: tree_sitter.Node) -> TryStmt:
        span = self.get_span(node)
        body_node = node.child_by_field_name("body")
        body_stmt = self.build_block_statement(body_node) if body_node else BlockStmt(span=span)

        handlers: List[ExceptHandler] = []
        else_block: Optional[BlockStmt] = None
        finally_block: Optional[BlockStmt] = None

        for child in node.children:
            if child.type == "except_clause":
                h_span = self.get_span(child)
                type_name: Optional[str] = None
                var_name: Optional[str] = None

                # Check exception type & var
                for ec_child in child.children:
                    if ec_child.type in ("identifier", "attribute"):
                        if type_name is None:
                            type_name = self.get_text(ec_child)
                        else:
                            var_name = self.get_text(ec_child)
                    elif ec_child.type == "as_pattern":
                        if ec_child.children:
                            type_name = self.get_text(ec_child.children[0])
                        if len(ec_child.children) >= 3:
                            var_name = self.get_text(ec_child.children[2])

                h_body = child.child_by_field_name("body") or (child.children[-1] if child.children else None)
                h_body_stmt = self.build_block_statement(h_body) if h_body and h_body.type == "block" else BlockStmt(span=h_span)

                handlers.append(ExceptHandler(span=h_span, type_name=type_name, var_name=var_name, body=h_body_stmt))

            elif child.type == "else_clause":
                e_body = child.child_by_field_name("body") or (child.named_children[0] if child.named_children else None)
                if e_body:
                    else_block = self.build_block_statement(e_body)

            elif child.type == "finally_clause":
                f_body = child.child_by_field_name("body") or (child.named_children[0] if child.named_children else None)
                if f_body:
                    finally_block = self.build_block_statement(f_body)

        return TryStmt(
            span=span,
            body=body_stmt,
            handlers=handlers,
            else_block=else_block,
            finally_block=finally_block,
        )

    def build_expression(self, node: Optional[tree_sitter.Node]) -> Expression:
        if node is None:
            return UnknownExpr(span=Span(start=None, end=None), raw_text="")  # type: ignore

        span = self.get_span(node)

        if node.type in ("identifier", "as_pattern_target"):
            return IdentifierExpr(span=span, name=self.get_text(node))

        elif node.type in ("string", "integer", "float", "true", "false", "none"):
            return LiteralExpr(span=span, value=self.get_text(node), literal_type=node.type)

        elif node.type == "call":
            func_node = node.child_by_field_name("function")
            args_node = node.child_by_field_name("arguments")

            func_expr = self.build_expression(func_node)
            arguments: List[Expression] = []

            if args_node:
                for arg_child in args_node.children:
                    if arg_child.type not in ("(", ")", ","):
                        arguments.append(self.build_expression(arg_child))

            return CallExpr(span=span, function=func_expr, arguments=arguments)

        elif node.type == "attribute":
            obj_node = node.child_by_field_name("object")
            attr_node = node.child_by_field_name("attribute")

            obj_expr = self.build_expression(obj_node)
            attr_name = self.get_text(attr_node) if attr_node else "attr"
            return AttributeAccessExpr(span=span, object_expr=obj_expr, attribute_name=attr_name)

        elif node.type in ("binary_operator", "boolean_operator", "comparison_operator"):
            left_node = node.children[0] if node.children else None
            op_node = node.children[1] if len(node.children) > 1 else None
            right_node = node.children[2] if len(node.children) > 2 else None

            left_expr = self.build_expression(left_node)
            op_text = self.get_text(op_node) if op_node else "=="
            right_expr = self.build_expression(right_node)

            return BinaryExpr(span=span, left=left_expr, operator=op_text, right=right_expr)

        elif node.type == "parenthesized_expression":
            child = node.named_children[0] if node.named_children else None
            return self.build_expression(child)

        return UnknownExpr(span=span, raw_text=self.get_text(node))
