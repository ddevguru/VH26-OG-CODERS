import ast
from typing import List, Union, Tuple
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
        diags, _, _ = self.analyze_tree_with_stats(tree, file_path)
        return diags

    def analyze_tree_with_stats(self, tree: ast.AST, file_path: str) -> Tuple[List[Diagnostic], int, int]:
        diagnostics: List[Diagnostic] = []
        collector = AstFunctionCollector()
        collector.visit(tree)

        functions_count = len(collector.functions)
        resources_count = 0

        for func_node, scope in collector.functions:
            if func_node.body:  # type: ignore
                cfg = self.cfg_builder.build_cfg(func_node)  # type: ignore
                diags = self.dataflow_analyzer.analyze_cfg(cfg, file_path)
                diagnostics.extend(diags)

                # Count resources in function
                if hasattr(self.dataflow_analyzer, '_last_out_stores'):
                    pass
                for block in cfg.blocks:
                    for stmt in block.statements:
                        if isinstance(stmt, ast.Assign):
                            is_acq, _ = self.dataflow_analyzer.catalog.is_acquisition_expr(stmt.value)
                            if is_acq:
                                resources_count += 1

        return diagnostics, functions_count, resources_count

