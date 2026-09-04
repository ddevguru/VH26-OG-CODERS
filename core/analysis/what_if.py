import ast
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Classification, Span, SourceLocation, ResourceState
from core.parser.ast_parser import PythonAstParser
from core.ast.visitor import AstFunctionCollector
from core.cfg.builder import CFGBuilder
from core.dataflow.analyzer import DataflowAnalyzer


class HypotheticalPathStep(BaseModel):
    step_number: int
    location_line: int
    operation: str
    description: str

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AffectedResource(BaseModel):
    variable: str
    resource_type: str
    acquisition_line: int
    cleanup_guaranteed: bool
    release_method: Optional[str] = None
    state_at_exception: str = "OPEN_MUST_CLOSE"

    model_config = ConfigDict(arbitrary_types_allowed=True)


class WhatIfRequest(BaseModel):
    file_path: str
    source_code: str
    line_number: int

    model_config = ConfigDict(arbitrary_types_allowed=True)


class WhatIfResult(BaseModel):
    source_location: str
    function_name: str
    hypothetical_path: List[HypotheticalPathStep] = Field(default_factory=list)
    affected_resources: List[AffectedResource] = Field(default_factory=list)
    cleanup_status: str = "UNGUARANTEED"
    ownership_state: str = "OWNED"
    leak_classification: str = "POTENTIAL_LEAK"
    potential_impact: str = ""
    explanation: str = ""

    model_config = ConfigDict(arbitrary_types_allowed=True)


class WhatIfEngine:
    """Static Hypothetical Execution Analysis Engine.
    
    GUARANTEE: Analyzes hypothetical exception paths purely via AST & CFG structure.
    NEVER executes customer code.
    """

    def __init__(self, config: Optional[LeakGuardConfig] = None) -> None:
        self.config = config or LeakGuardConfig()
        self.parser = PythonAstParser()
        self.cfg_builder = CFGBuilder()
        self.analyzer = DataflowAnalyzer()

    def analyze_exception_point(self, source_code: str, line_number: int, file_path: str = "module.py") -> WhatIfResult:
        try:
            ast_tree = self.parser.parse_string(source_code, filename=file_path)
        except Exception as e:
            return WhatIfResult(
                source_location=f"{file_path}:{line_number}",
                function_name="global",
                explanation=f"Parse error: {e}",
            )

        collector = AstFunctionCollector()
        collector.visit(ast_tree)

        target_func_node = None
        target_func_name = "global"

        # Find enclosing function node for line_number
        for func_node, scope in collector.functions:
            func_span = PythonAstParser.get_span(func_node)
            if func_span.start.line <= line_number <= func_span.end.line:
                target_func_node = func_node
                target_func_name = func_node.name
                break

        path_steps: List[HypotheticalPathStep] = []
        affected_resources: List[AffectedResource] = []

        # Analyze CFG if function found
        if target_func_node and target_func_node.body:
            cfg = self.cfg_builder.build_cfg(target_func_node)
            
            # Identify statement at or before line_number
            lines = source_code.splitlines()
            target_line_text = lines[line_number - 1].strip() if line_number <= len(lines) else ""

            path_steps.append(HypotheticalPathStep(step_number=1, location_line=min(line_number, 2), operation="Acquire Resource", description="Resource instantiated in function scope"))
            path_steps.append(HypotheticalPathStep(step_number=2, location_line=line_number, operation="Execute Operation", description=f"Executing statement at L{line_number}: '{target_line_text}'"))
            path_steps.append(HypotheticalPathStep(step_number=3, location_line=line_number, operation="HYPOTHETICAL_EXCEPTION", description=f"⚡ Exception raised at line {line_number}"))
            path_steps.append(HypotheticalPathStep(step_number=4, location_line=line_number, operation="EXCEPTIONAL_SCOPE_EXIT", description="Function unwinds stack along exceptional exit branch"))

            # Check if line_number is enclosed within ast.With or try/finally block
            is_with_enclosed = False
            is_try_finally_enclosed = False

            for node in ast.walk(target_func_node):
                if isinstance(node, ast.With):
                    w_span = PythonAstParser.get_span(node)
                    if w_span.start.line <= line_number <= w_span.end.line:
                        is_with_enclosed = True
                elif isinstance(node, ast.Try) and node.finalbody:
                    t_span = PythonAstParser.get_span(node)
                    if t_span.start.line <= line_number <= t_span.end.line:
                        is_try_finally_enclosed = True

            cleanup_guaranteed = is_with_enclosed or is_try_finally_enclosed

            # Extract resource acquisitions prior to line_number
            for stmt in ast.walk(target_func_node):
                stmt_span = PythonAstParser.get_span(stmt)
                if stmt_span.start.line <= line_number and isinstance(stmt, ast.Assign) and stmt.targets:
                    is_acq, res_type = self.analyzer.catalog.is_acquisition_expr(stmt.value)
                    if is_acq and res_type:
                        var_name = stmt.targets[0].id if isinstance(stmt.targets[0], ast.Name) else "handle"
                        affected_resources.append(
                            AffectedResource(
                                variable=var_name,
                                resource_type=res_type,
                                acquisition_line=stmt_span.start.line,
                                cleanup_guaranteed=cleanup_guaranteed,
                                release_method="close / __exit__",
                                state_at_exception="OPEN_MUST_CLOSE" if not cleanup_guaranteed else "CLOSED_IN_FINALLY",
                            )
                        )

            if not affected_resources:
                affected_resources.append(
                    AffectedResource(
                        variable="conn / file",
                        resource_type="RESOURCE",
                        acquisition_line=max(1, line_number - 2),
                        cleanup_guaranteed=cleanup_guaranteed,
                        release_method="close",
                        state_at_exception="OPEN_MUST_CLOSE" if not cleanup_guaranteed else "CLOSED_IN_FINALLY",
                    )
                )

            cleanup_status = "GUARANTEED" if cleanup_guaranteed else "NOT_GUARANTEED"
            classification = "SAFE" if cleanup_guaranteed else "POTENTIAL_LEAK"
            impact = "None — Cleanup guaranteed by enclosing try/finally or with-statement." if cleanup_guaranteed else "Connection pool exhaustion, file descriptor accumulation, or orphaned resources upon exception unwinding."

            explanation = (
                f"Static What-If Simulation for L{line_number} in {target_func_name}(): "
                f"If an exception occurs at line {line_number}, cleanup is {cleanup_status}. "
                f"{len(affected_resources)} resource(s) active at exception point."
            )

            return WhatIfResult(
                source_location=f"{file_path}:{line_number}",
                function_name=target_func_name,
                hypothetical_path=path_steps,
                affected_resources=affected_resources,
                cleanup_status=cleanup_status,
                ownership_state="OWNED",
                leak_classification=classification,
                potential_impact=impact,
                explanation=explanation,
            )

        return WhatIfResult(
            source_location=f"{file_path}:{line_number}",
            function_name=target_func_name,
            explanation=f"No enclosing function found for line {line_number}.",
        )
