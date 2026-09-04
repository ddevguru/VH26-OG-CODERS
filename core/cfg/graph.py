import ast
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field


class EdgeType(str, Enum):
    NORMAL = "NORMAL"
    COND_TRUE = "COND_TRUE"
    COND_FALSE = "COND_FALSE"
    EXCEPTIONAL = "EXCEPTIONAL"
    RETURN = "RETURN"
    FINALLY_ENTRY = "FINALLY_ENTRY"
    FINALLY_EXIT = "FINALLY_EXIT"


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

    def add_statement(self, stmt: ast.AST) -> None:
        self.statements.append(stmt)


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
