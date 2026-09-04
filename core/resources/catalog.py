import ast
from typing import Optional, Tuple, List
from core.resources.rules import ResourceRuleRegistry, ResourceRule, ResourceType


class ResourceCatalog:
    """Catalog wrapper around ResourceRuleRegistry for ast.AST acquisition and release matching."""

    def __init__(self, registry: Optional[ResourceRuleRegistry] = None) -> None:
        self.registry = registry or ResourceRuleRegistry()

    def is_acquisition_expr(self, expr: Optional[ast.AST]) -> Tuple[bool, Optional[str]]:
        if expr is None:
            return False, None
        if isinstance(expr, ast.Await):
            expr = expr.value
        if not isinstance(expr, ast.Call):
            return False, None

        func_str = self._call_func_to_string(expr.func)
        if not func_str:
            return False, None

        rule = self.registry.match_acquisition(func_str)
        if rule:
            return True, func_str

        return False, None

    def is_release_invocation(self, expr: Optional[ast.AST]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Returns (is_release, target_var_name, release_method_name)"""
        if expr is None:
            return False, None, None

        call_expr: Optional[ast.Call] = None
        if isinstance(expr, ast.Expr) and isinstance(expr.value, ast.Call):
            call_expr = expr.value
        elif isinstance(expr, ast.Call):
            call_expr = expr

        if call_expr and isinstance(call_expr.func, ast.Attribute):
            attr_name = call_expr.func.attr
            target_var = self._call_func_to_string(call_expr.func.value)
            rule = self.registry.match_release(attr_name)
            if rule and target_var:
                return True, target_var, attr_name

        return False, None, None

    def _call_func_to_string(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            obj = self._call_func_to_string(node.value)
            return f"{obj}.{node.attr}" if obj else node.attr
        return ""
