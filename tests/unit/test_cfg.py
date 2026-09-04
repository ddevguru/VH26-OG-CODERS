import pytest
import ast
from core.parser.ast_parser import PythonAstParser
from core.cfg.builder import CFGBuilder
from core.cfg.graph import CFG, EdgeType


def test_cfg_builder_python_ast_if_else() -> None:
    code = """
def foo(cond):
    f = open("file.txt")
    if cond:
        f.close()
    else:
        do_nothing()
"""
    parser = PythonAstParser()
    tree = parser.parse_string(code)
    func_node = tree.body[0]

    cfg_builder = CFGBuilder()
    cfg = cfg_builder.build_cfg(func_node)  # type: ignore

    assert isinstance(cfg, CFG)
    assert len(cfg.blocks) >= 4
    assert cfg.entry_block is not None
    assert cfg.exit_block is not None

    edge_types = [edge.edge_type for b in cfg.blocks for edge in b.outgoing]
    assert EdgeType.COND_TRUE in edge_types
    assert EdgeType.COND_FALSE in edge_types
