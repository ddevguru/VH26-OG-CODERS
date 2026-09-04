import ast
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List, Set, Tuple, Union
from core.common.models import Span, ResourceType, ResourceState
from core.resources.rules import ResourceRule, ResourceRuleRegistry


class ResourceOwnership(str, Enum):
    OWNED = "OWNED"
    BORROWED = "BORROWED"
    TRANSFERRED = "TRANSFERRED"
    ESCAPED = "ESCAPED"
    UNKNOWN = "UNKNOWN"


@dataclass
class ResourceAcquisition:
    resource_id: str
    symbol_name: str
    rule: ResourceRule
    location: Span
    expression_str: str


@dataclass
class ResourceRelease:
    resource_id: str
    symbol_name: str
    method_name: str
    location: Span


@dataclass
class ResourceTransfer:
    resource_id: str
    source_symbol: str
    destination: str
    location: Span
    transfer_type: str = "RETURN"  # RETURN, PROPERTY_ASSIGNMENT, PARAMETER_SINK


@dataclass
class ResourceEscape:
    resource_id: str
    symbol_name: str
    location: Span
    reason: str


class ResourceSemanticsEngine:
    """Evaluates Python AST expressions for resource acquisition, release, ownership, transfer, and escape semantics."""

    def __init__(self, registry: Optional[ResourceRuleRegistry] = None) -> None:
        self.registry = registry or ResourceRuleRegistry()

    def evaluate_call(self, call_node: ast.Call) -> Tuple[bool, Optional[ResourceRule], str]:
        """Evaluates whether an ast.Call represents a resource acquisition."""
        func_str = self._func_to_string(call_node.func)
        rule = self.registry.match_acquisition(func_str)
        if rule:
            return True, rule, func_str
        return False, None, func_str

    def evaluate_method_release(self, call_node: ast.Call) -> Tuple[bool, Optional[str], Optional[str]]:
        """Evaluates whether an ast.Call represents a cleanup method invocation (e.g. f.close())."""
        if isinstance(call_node.func, ast.Attribute):
            method_name = call_node.func.attr
            obj_str = self._func_to_string(call_node.func.value)
            rule = self.registry.match_release(method_name)
            if rule:
                return True, obj_str, method_name
        return False, None, None

    def evaluate_context_manager(self, with_item: ast.withitem) -> Tuple[bool, Optional[ResourceRule], Optional[str]]:
        """Evaluates withitem expression in 'with' or 'async with' statements."""
        if isinstance(with_item.context_expr, ast.Call):
            is_acq, rule, func_str = self.evaluate_call(with_item.context_expr)
            target_name = self._func_to_string(with_item.optional_vars) if with_item.optional_vars else None
            return is_acq, rule, target_name
        return False, None, None

    def _func_to_string(self, node: Optional[ast.AST]) -> str:
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            obj = self._func_to_string(node.value)
            return f"{obj}.{node.attr}" if obj else node.attr
        return ""
