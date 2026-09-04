import ast
from typing import List, Tuple
from core.parser.ast_parser import PythonAstParser


class AstFunctionCollector(ast.NodeVisitor):
    """Walks a Python stdlib ast.AST module and collects all function definitions (functions & methods)."""

    def __init__(self) -> None:
        self.functions: List[Tuple[ast.AST, str]] = []  # List of (ast.FunctionDef/AsyncFunctionDef, scope_name)
        self.current_scope: List[str] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        scope = ".".join(self.current_scope) if self.current_scope else "global"
        self.functions.append((node, scope))
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        scope = ".".join(self.current_scope) if self.current_scope else "global"
        self.functions.append((node, scope))
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()
