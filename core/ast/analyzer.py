import ast
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from core.scopes.scope_manager import ScopeManager, Scope
from core.symbols.table import SymbolTable, Symbol
from core.ast.visitor import LeakGuardAstVisitor
from core.common.models import Span


@dataclass
class AstAnalysisResult:
    scope_manager: ScopeManager
    functions: List[Tuple[ast.AST, str]]
    classes: List[Tuple[ast.ClassDef, str]]
    imports: List[Tuple[str, Optional[str], Span]]

    @property
    def global_scope(self) -> Scope:
        return self.scope_manager.global_scope

    def find_scope(self, fqn: str) -> Optional[Scope]:
        for s in self.scope_manager.all_scopes:
            if s.fully_qualified_name == fqn or s.name == fqn:
                return s
        return None


class AstScopeSymbolAnalyzer:
    """Facade for AST parsing, scope tree resolution, and symbol table analysis."""

    def __init__(self) -> None:
        pass

    def analyze_ast(self, tree: ast.AST) -> AstAnalysisResult:
        scope_manager = ScopeManager()
        visitor = LeakGuardAstVisitor(scope_manager=scope_manager)
        visitor.visit(tree)
        return AstAnalysisResult(
            scope_manager=visitor.scope_manager,
            functions=visitor.functions,
            classes=visitor.classes,
            imports=visitor.imports,
        )
