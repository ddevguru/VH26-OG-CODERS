import ast
from typing import Optional
from core.resources.state import AbstractStore
from core.resources.catalog import ResourceCatalog
from core.common.models import ResourceState


class OwnershipTracker:
    """Performs escape analysis & ownership tracking for stdlib ast.AST Python nodes."""

    def __init__(self, catalog: ResourceCatalog) -> None:
        self.catalog = catalog

    def process_statement(self, stmt: ast.AST, store: AbstractStore) -> None:
        """Updates AbstractStore ownership state based on ast.AST statement semantics."""

        if isinstance(stmt, ast.Return) and stmt.value and isinstance(stmt.value, ast.Name):
            var_name = stmt.value.id
            if store.get_state(var_name) == ResourceState.OPEN_MUST_CLOSE:
                store.set_state(var_name, ResourceState.TRANSFERRED)

        elif isinstance(stmt, ast.Assign) and stmt.targets:
            target = stmt.targets[0]

            # Field assignment: self.connection = conn
            if isinstance(target, ast.Attribute) and isinstance(stmt.value, ast.Name):
                rhs_var = stmt.value.id
                if store.get_state(rhs_var) == ResourceState.OPEN_MUST_CLOSE:
                    store.set_state(rhs_var, ResourceState.TRANSFERRED)

            # Variable aliasing: conn2 = conn1
            elif isinstance(target, ast.Name) and isinstance(stmt.value, ast.Name):
                lhs_var = target.id
                rhs_var = stmt.value.id
                if store.get_state(rhs_var) != ResourceState.UNACQUIRED:
                    store.add_alias(lhs_var, rhs_var)
