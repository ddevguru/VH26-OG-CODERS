from enum import Enum
from typing import List, Optional, Set
from dataclasses import dataclass, field
from core.symbols.table import SymbolTable, Symbol


class ScopeType(str, Enum):
    GLOBAL = "GLOBAL"
    MODULE = "MODULE"
    CLASS = "CLASS"
    FUNCTION = "FUNCTION"
    ASYNC_FUNCTION = "ASYNC_FUNCTION"
    LAMBDA = "LAMBDA"
    COMPREHENSION = "COMPREHENSION"


@dataclass
class Scope:
    name: str
    scope_type: ScopeType
    parent: Optional['Scope'] = None
    children: List['Scope'] = field(default_factory=list)
    variables: Set[str] = field(default_factory=set)
    global_vars: Set[str] = field(default_factory=set)
    nonlocal_vars: Set[str] = field(default_factory=set)
    symbol_table: SymbolTable = field(default_factory=SymbolTable)

    def __post_init__(self) -> None:
        if self.symbol_table.scope_name == "global":
            self.symbol_table.scope_name = self.fully_qualified_name
        if self.parent:
            self.parent.children.append(self)

    @property
    def fully_qualified_name(self) -> str:
        if self.parent and self.parent.name not in ("global", "<module>"):
            return f"{self.parent.fully_qualified_name}.{self.name}"
        return self.name

    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        """Resolves symbol following LEGB rules (Local -> Enclosing -> Global)."""
        if name in self.global_vars:
            curr = self
            while curr.parent:
                curr = curr.parent
            return curr.symbol_table.lookup(name)

        if name in self.nonlocal_vars:
            curr = self.parent
            while curr and curr.scope_type != ScopeType.GLOBAL:
                sym = curr.symbol_table.lookup(name)
                if sym:
                    return sym
                curr = curr.parent

        sym = self.symbol_table.lookup(name)
        if sym:
            return sym

        if self.parent:
            return self.parent.lookup_symbol(name)

        return None


class ScopeManager:
    """Manages nested lexical scopes, closures, global, and nonlocal variable declarations."""

    def __init__(self) -> None:
        self.global_scope = Scope(name="global", scope_type=ScopeType.GLOBAL)
        self.current_scope = self.global_scope
        self.scope_stack: List[Scope] = [self.global_scope]
        self.all_scopes: List[Scope] = [self.global_scope]

    def push_scope(self, name: str, scope_type: ScopeType) -> Scope:
        new_scope = Scope(name=name, scope_type=scope_type, parent=self.current_scope)
        self.scope_stack.append(new_scope)
        self.current_scope = new_scope
        self.all_scopes.append(new_scope)
        return new_scope

    def pop_scope(self) -> Optional[Scope]:
        if len(self.scope_stack) > 1:
            popped = self.scope_stack.pop()
            self.current_scope = self.scope_stack[-1]
            return popped
        return None

    def declare_variable(self, name: str) -> None:
        if name in self.current_scope.global_vars:
            self.global_scope.variables.add(name)
        else:
            self.current_scope.variables.add(name)

    def declare_global(self, name: str) -> None:
        self.current_scope.global_vars.add(name)

    def declare_nonlocal(self, name: str) -> None:
        self.current_scope.nonlocal_vars.add(name)

    def resolve_symbol(self, name: str) -> Optional[Symbol]:
        return self.current_scope.lookup_symbol(name)

