import ast
from typing import List, Union
from pathlib import Path

from core.parser.ast_parser import PythonAstParser
from core.ast.visitor import AstFunctionCollector
from core.cfg.builder import CFGBuilder
from core.dataflow.analyzer import DataflowAnalyzer
from core.common.models import Diagnostic


class BaseRule:
    rule_id: str = "BASE_RULE"
    description: str = "Base static analysis rule"

    def analyze_tree(self, tree: ast.AST, file_path: str) -> List[Diagnostic]:
        raise NotImplementedError


class ResourceLeakRule(BaseRule):
    """Rule detecting resource leaks across Python function control flow graphs using stdlib ast.AST."""

    rule_id = "RULE_LEAK_001"
    description = "AST & Control-Flow based Static Resource Lifetime Analysis for Python"

    def __init__(self) -> None:
        self.cfg_builder = CFGBuilder()
        self.dataflow_analyzer = DataflowAnalyzer()

    def analyze_tree(self, tree: ast.AST, file_path: str) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []

        collector = AstFunctionCollector()
        collector.visit(tree)

        for func_node, scope in collector.functions:
            if func_node.body:  # type: ignore
                cfg = self.cfg_builder.build_cfg(func_node)  # type: ignore
                diags = self.dataflow_analyzer.analyze_cfg(cfg, file_path)
                diagnostics.extend(diags)

        return diagnostics
