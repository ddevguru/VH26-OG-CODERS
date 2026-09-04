import ast
from typing import Dict, List, Set, Tuple, Optional
from collections import deque
import uuid

from core.cfg.graph import CFG, CFGBlock, EdgeType
from core.parser.ast_parser import PythonAstParser
from core.resources.catalog import ResourceCatalog
from core.resources.state import AbstractStore
from core.ownership.tracker import OwnershipTracker
from core.common.models import (
    ResourceState,
    Classification,
    Diagnostic,
    PathStep,
    Span,
    ResourceSymbol,
    Confidence,
    Severity,
)


class DataflowAnalyzer:
    """Worklist-based path-sensitive intra-procedural dataflow analysis engine for Python stdlib ast.AST."""

    def __init__(self, catalog: Optional[ResourceCatalog] = None) -> None:
        self.catalog = catalog or ResourceCatalog()
        self.ownership_tracker = OwnershipTracker(self.catalog)

    def analyze_cfg(self, cfg: CFG, file_path: str = "<stdin>") -> List[Diagnostic]:
        in_stores: Dict[int, AbstractStore] = {b.block_id: AbstractStore() for b in cfg.blocks}
        out_stores: Dict[int, AbstractStore] = {b.block_id: AbstractStore() for b in cfg.blocks}
        path_traces: Dict[int, List[PathStep]] = {b.block_id: [] for b in cfg.blocks}

        worklist: deque[int] = deque([cfg.entry_block.block_id])
        visited_count: Dict[int, int] = {b.block_id: 0 for b in cfg.blocks}

        while worklist:
            block_id = worklist.popleft()
            block = cfg.get_block(block_id)
            if not block:
                continue

            visited_count[block_id] += 1
            if visited_count[block_id] > 50:
                continue

            merged_in = AbstractStore()
            predecessor_steps: List[PathStep] = []

            for edge in block.incoming:
                pred_out = out_stores[edge.source_id]
                merged_in = merged_in.join(pred_out)
                if path_traces[edge.source_id]:
                    predecessor_steps.extend(path_traces[edge.source_id])

            in_stores[block_id] = merged_in
            current_store = merged_in.clone()
            current_steps = list(predecessor_steps)

            for stmt in block.statements:
                span = PythonAstParser.get_span(stmt)

                # 1. Resource Acquisition via ast.Assign: f = open(...)
                if isinstance(stmt, ast.Assign) and stmt.targets:
                    target_node = stmt.targets[0]
                    if isinstance(target_node, ast.Name):
                        var_name = target_node.id
                        is_acq, res_type = self.catalog.is_acquisition_expr(stmt.value)
                        if is_acq and res_type:
                            symbol = ResourceSymbol(
                                id=f"res_{uuid.uuid4().hex[:8]}",
                                variable_name=var_name,
                                resource_type=res_type,
                                acquisition_span=span,
                            )
                            current_store.register_resource(var_name, symbol)
                            current_steps.append(
                                PathStep(
                                    step_number=len(current_steps) + 1,
                                    location=span,
                                    description=f"Resource '{var_name}' ({res_type}) acquired",
                                    state_at_step=ResourceState.OPEN_MUST_CLOSE,
                                )
                            )

                # 2. Context Manager with statement: with open(...) as f:
                elif isinstance(stmt, (ast.With, getattr(ast, "AsyncWith", ast.With))):
                    for item in stmt.items:
                        var_name: Optional[str] = None
                        if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                            var_name = item.optional_vars.id

                        is_acq, res_type = self.catalog.is_acquisition_expr(item.context_expr)
                        if var_name:
                            res_id = current_store.symbol_to_id.get(var_name)
                            if res_id and res_id in current_store.id_to_symbol:
                                current_store.id_to_symbol[res_id].is_try_with_resources = True
                                current_store.set_state(var_name, ResourceState.CLOSED)
                            elif is_acq and res_type:
                                symbol = ResourceSymbol(
                                    id=f"res_{uuid.uuid4().hex[:8]}",
                                    variable_name=var_name,
                                    resource_type=res_type,
                                    acquisition_span=span,
                                    is_try_with_resources=True,
                                )
                                current_store.register_resource(var_name, symbol)
                                current_store.set_state(var_name, ResourceState.CLOSED)

                # 3. Resource Release Call: f.close()
                is_rel, rel_var, method_name = self.catalog.is_release_invocation(stmt)
                if is_rel and rel_var:
                    if current_store.get_state(rel_var) != ResourceState.UNACQUIRED:
                        current_store.set_state(rel_var, ResourceState.CLOSED)
                        current_steps.append(
                            PathStep(
                                step_number=len(current_steps) + 1,
                                location=span,
                                description=f"Resource '{rel_var}' released via {method_name}()",
                                state_at_step=ResourceState.CLOSED,
                            )
                        )

                # 4. Ownership / Escape Analysis
                self.ownership_tracker.process_statement(stmt, current_store)

            path_traces[block_id] = current_steps

            prev_out = out_stores[block_id]
            if current_store.id_to_state != prev_out.id_to_state:
                out_stores[block_id] = current_store
                for edge in block.outgoing:
                    worklist.append(edge.target_id)

        return self._generate_diagnostics(cfg, out_stores, path_traces, file_path)

    def _generate_diagnostics(
        self,
        cfg: CFG,
        out_stores: Dict[int, AbstractStore],
        path_traces: Dict[int, List[PathStep]],
        file_path: str,
    ) -> List[Diagnostic]:

        diagnostics: List[Diagnostic] = []
        normal_exit_store = out_stores[cfg.exit_block.block_id]
        exceptional_exit_store = out_stores[cfg.exceptional_exit_block.block_id]

        all_symbols = dict(normal_exit_store.id_to_symbol)
        all_symbols.update(exceptional_exit_store.id_to_symbol)

        for res_id, symbol in all_symbols.items():
            if symbol.is_try_with_resources:
                continue

            norm_state = normal_exit_store.get_state(res_id)
            exp_state = exceptional_exit_store.get_state(res_id)

            classification: Optional[Classification] = None
            confidence = Confidence.HIGH
            reason = ""

            if norm_state == ResourceState.OPEN_MUST_CLOSE:
                classification = Classification.DEFINITE_LEAK
                confidence = Confidence.HIGH
                reason = f"Resource '{symbol.variable_name}' of type '{symbol.resource_type}' is acquired but never closed on normal execution exit path."

            elif norm_state == ResourceState.MAYBE_LEAKED:
                classification = Classification.POTENTIAL_LEAK
                confidence = Confidence.MEDIUM
                reason = f"Resource '{symbol.variable_name}' of type '{symbol.resource_type}' is closed on some execution branches but left unclosed on others."

            elif exp_state == ResourceState.OPEN_MUST_CLOSE and norm_state in (ResourceState.CLOSED, ResourceState.UNACQUIRED):
                classification = Classification.POTENTIAL_LEAK
                confidence = Confidence.MEDIUM
                reason = f"Resource '{symbol.variable_name}' of type '{symbol.resource_type}' is closed during normal execution, but an exception will bypass cleanup."

            if classification:
                steps = path_traces.get(cfg.exit_block.block_id, [])
                finding_id = f"LEAK_{hash((file_path, symbol.acquisition_span.start.line, symbol.variable_name)) & 0xFFFFFFFF:08x}"

                diagnostics.append(
                    Diagnostic(
                        finding_id=finding_id,
                        rule_id="RULE_LEAK_001",
                        classification=classification,
                        message=f"Resource leak detected: '{symbol.variable_name}' ({symbol.resource_type})",
                        file_path=file_path,
                        location=symbol.acquisition_span,
                        resource_type=symbol.resource_type,
                        resource_variable=symbol.variable_name,
                        acquisition_location=symbol.acquisition_span,
                        execution_path=steps,
                        confidence=confidence,
                        severity=Severity.ERROR if classification == Classification.DEFINITE_LEAK else Severity.WARNING,
                        reason=reason,
                    )
                )

        return diagnostics
