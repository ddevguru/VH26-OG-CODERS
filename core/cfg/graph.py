import ast
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field
from core.common.models import SourceLocation, Span


class EdgeType(str, Enum):
    NORMAL = "NORMAL"
    TRUE_BRANCH = "TRUE_BRANCH"
    FALSE_BRANCH = "FALSE_BRANCH"
    LOOP_BACK = "LOOP_BACK"
    BREAK = "BREAK"
    CONTINUE = "CONTINUE"
    RETURN = "RETURN"
    RAISE = "RAISE"
    EXCEPTION = "EXCEPTION"
    FINALLY = "FINALLY"
    CONTEXT_ENTER = "CONTEXT_ENTER"
    CONTEXT_EXIT = "CONTEXT_EXIT"
    EXIT = "EXIT"

    # Compatibility Aliases
    COND_TRUE = "TRUE_BRANCH"
    COND_FALSE = "FALSE_BRANCH"
    EXCEPTIONAL = "EXCEPTION"
    FINALLY_ENTRY = "FINALLY"
    FINALLY_EXIT = "FINALLY"


@dataclass
class CFGEdge:
    source_id: int
    target_id: int
    edge_type: EdgeType = EdgeType.NORMAL
    label: Optional[str] = None


@dataclass
class CFGBlock:
    block_id: int
    statements: List[ast.AST] = field(default_factory=list)
    incoming: List[CFGEdge] = field(default_factory=list)
    outgoing: List[CFGEdge] = field(default_factory=list)
    is_entry: bool = False
    is_exit: bool = False
    is_exceptional_exit: bool = False
    span: Optional[Span] = None

    def add_statement(self, stmt: ast.AST) -> None:
        self.statements.append(stmt)
        # Update block span from statement bounds
        stmt_span = self._extract_span(stmt)
        if stmt_span:
            if self.span is None:
                self.span = stmt_span
            else:
                start = min(self.span.start.line, stmt_span.start.line)
                start_col = min(self.span.start.column, stmt_span.start.column)
                end = max(self.span.end.line, stmt_span.end.line)
                end_col = max(self.span.end.column, stmt_span.end.column)
                self.span = Span(
                    start=SourceLocation(line=start, column=start_col),
                    end=SourceLocation(line=end, column=end_col),
                )

    def _extract_span(self, node: ast.AST) -> Optional[Span]:
        lineno = getattr(node, "lineno", None)
        if lineno is None:
            return None
        col_val = getattr(node, "col_offset", None)
        col = (col_val + 1) if col_val is not None else 1
        end_line = getattr(node, "end_lineno", None) or lineno
        end_col_val = getattr(node, "end_col_offset", None)
        end_col = (end_col_val + 1) if end_col_val is not None else col
        return Span(
            start=SourceLocation(line=lineno, column=col),
            end=SourceLocation(line=end_line, column=end_col),
        )


@dataclass
class CFG:
    method_name: str
    entry_block: CFGBlock
    exit_block: CFGBlock
    exceptional_exit_block: CFGBlock
    blocks: List[CFGBlock] = field(default_factory=list)

    def get_block(self, block_id: int) -> Optional[CFGBlock]:
        for b in self.blocks:
            if b.block_id == block_id:
                return b
        return None

    def add_edge(self, source: CFGBlock, target: CFGBlock, edge_type: EdgeType = EdgeType.NORMAL, label: Optional[str] = None) -> None:
        edge = CFGEdge(source_id=source.block_id, target_id=target.block_id, edge_type=edge_type, label=label)
        source.outgoing.append(edge)
        target.incoming.append(edge)
