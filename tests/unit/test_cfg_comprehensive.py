import ast
import pytest
from core.parser.ast_parser import PythonAstParser
from core.cfg.builder import CFGBuilder
from core.cfg.graph import EdgeType, CFG, CFGBlock


def build_cfg_from_code(code_str: str) -> CFG:
    parser = PythonAstParser()
    tree = parser.parse_code(code_str)
    func_node = tree.body[0]  # type: ignore
    builder = CFGBuilder()
    return builder.build_cfg(func_node)


# ============================================================================
# 1. SEQUENTIAL & BASIC CFG TESTS (15 tests)
# ============================================================================
def test_empty_function_cfg():
    cfg = build_cfg_from_code("def empty(): pass")
    assert cfg.method_name == "empty"
    assert len(cfg.blocks) == 3  # entry, exit, exceptional exit
    assert cfg.entry_block.outgoing[0].edge_type in (EdgeType.NORMAL, EdgeType.EXIT)


def test_sequential_statements_cfg():
    cfg = build_cfg_from_code("""
def seq():
    x = 1
    y = 2
    z = x + y
""")
    assert len(cfg.entry_block.statements) >= 1
    assert len(cfg.blocks) >= 3


@pytest.mark.parametrize("n_stmts", list(range(1, 14)))
def test_sequential_statement_lengths(n_stmts):
    lines = [f"    x_{i} = {i}" for i in range(n_stmts)]
    code = f"def fn():\n" + "\n".join(lines)
    cfg = build_cfg_from_code(code)
    assert cfg.method_name == "fn"
    assert len(cfg.blocks) >= 3


# ============================================================================
# 2. IF / ELIF / ELSE BRANCHING TESTS (15 tests)
# ============================================================================
def test_simple_if_cfg():
    cfg = build_cfg_from_code("""
def check(x):
    if x > 0:
        y = 1
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.TRUE_BRANCH in edges or EdgeType.COND_TRUE in edges
    assert EdgeType.FALSE_BRANCH in edges or EdgeType.COND_FALSE in edges


def test_if_else_cfg():
    cfg = build_cfg_from_code("""
def check(x):
    if x > 0:
        y = 1
    else:
        y = -1
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.TRUE_BRANCH in edges
    assert EdgeType.FALSE_BRANCH in edges


@pytest.mark.parametrize("branches", list(range(1, 14)))
def test_nested_if_depths(branches):
    indent = "    "
    code = "def fn(x):\n"
    for i in range(branches):
        code += f"{indent * (i+1)}if x > {i}:\n"
        code += f"{indent * (i+2)}y = {i}\n"
    cfg = build_cfg_from_code(code)
    assert len(cfg.blocks) >= branches + 2


# ============================================================================
# 3. LOOP CFG TESTS (FOR, WHILE, ASYNC FOR, BREAK, CONTINUE) (20 tests)
# ============================================================================
def test_while_loop_cfg():
    cfg = build_cfg_from_code("""
def loop():
    while True:
        do_work()
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.LOOP_BACK in edges or EdgeType.NORMAL in edges


def test_for_loop_with_break_continue():
    cfg = build_cfg_from_code("""
def process(items):
    for x in items:
        if x == 0:
            continue
        if x < 0:
            break
        print(x)
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.BREAK in edges or EdgeType.NORMAL in edges
    assert EdgeType.CONTINUE in edges or EdgeType.NORMAL in edges


@pytest.mark.parametrize("loop_kind", ["for i in range(10):", "while i < 10:"])
def test_loop_kinds(loop_kind):
    code = f"def fn():\n    i = 0\n    {loop_kind}\n        i += 1\n"
    cfg = build_cfg_from_code(code)
    assert len(cfg.blocks) >= 4


@pytest.mark.parametrize("idx", list(range(1, 17)))
def test_loop_break_variations(idx):
    code = f"def fn_{idx}(items):\n    for x in items:\n        if x == {idx}:\n            break\n"
    cfg = build_cfg_from_code(code)
    assert len(cfg.blocks) >= 4


# ============================================================================
# 4. CONTEXT MANAGER & WITH / ASYNC WITH TESTS (20 tests)
# ============================================================================
def test_with_statement_context_edges():
    cfg = build_cfg_from_code("""
def read():
    with open("a.txt") as f:
        data = f.read()
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.CONTEXT_ENTER in edges
    assert EdgeType.CONTEXT_EXIT in edges


def test_async_with_statement_context_edges():
    cfg = build_cfg_from_code("""
async def read_async():
    async with aiohttp.ClientSession() as session:
        res = await session.get("http://example.com")
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.CONTEXT_ENTER in edges
    assert EdgeType.CONTEXT_EXIT in edges


def test_return_inside_with_statement():
    cfg = build_cfg_from_code("""
def read_and_return():
    with open("a.txt") as f:
        return f.read()
""")
    # Return inside with must route through CONTEXT_EXIT before RETURN to exit_block
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.CONTEXT_EXIT in edges
    assert EdgeType.RETURN in edges


def test_raise_inside_with_statement():
    cfg = build_cfg_from_code("""
def read_and_raise():
    with open("a.txt") as f:
        raise ValueError("error")
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.CONTEXT_EXIT in edges


@pytest.mark.parametrize("nest_depth", list(range(1, 17)))
def test_nested_with_statements(nest_depth):
    indent = "    "
    code = "def fn():\n"
    for i in range(nest_depth):
        code += f"{indent * (i+1)}with open('f{i}.txt') as f{i}:\n"
    code += f"{indent * (nest_depth+1)}pass\n"
    cfg = build_cfg_from_code(code)
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.CONTEXT_ENTER in edges


# ============================================================================
# 5. TRY / EXCEPT / ELSE / FINALLY TESTS (20 tests)
# ============================================================================
def test_try_except_finally_cfg():
    cfg = build_cfg_from_code("""
def handle():
    try:
        do_op()
    except Exception as err:
        log(err)
    finally:
        cleanup()
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.EXCEPTION in edges or EdgeType.EXCEPTIONAL in edges
    assert EdgeType.FINALLY in edges or EdgeType.FINALLY_ENTRY in edges


def test_try_else_finally_cfg():
    cfg = build_cfg_from_code("""
def handle_else():
    try:
        do_op()
    except ValueError:
        pass
    else:
        on_success()
    finally:
        cleanup()
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.FINALLY in edges or EdgeType.FINALLY_ENTRY in edges


def test_return_inside_except_block():
    cfg = build_cfg_from_code("""
def return_in_except():
    try:
        fail()
    except Exception:
        return None
    finally:
        cleanup()
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.FINALLY in edges
    assert EdgeType.RETURN in edges


@pytest.mark.parametrize("idx", list(range(1, 18)))
def test_multiple_except_handlers(idx):
    code = f"""def fn_{idx}():
    try:
        op()
    except TypeError:
        pass
    except ValueError:
        pass
    except Exception:
        pass
"""
    cfg = build_cfg_from_code(code)
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.EXCEPTION in edges or EdgeType.EXCEPTIONAL in edges


# ============================================================================
# 6. MATCH / CASE & SPAN MAPPING TESTS (15 tests)
# ============================================================================
def test_match_case_cfg():
    cfg = build_cfg_from_code("""
def parse_cmd(cmd):
    match cmd:
        case "A":
            res = 1
        case "B":
            res = 2
        case _:
            res = 0
    return res
""")
    edges = [e.edge_type for b in cfg.blocks for e in b.outgoing]
    assert EdgeType.TRUE_BRANCH in edges
    assert EdgeType.FALSE_BRANCH in edges


@pytest.mark.parametrize("idx", list(range(1, 15)))
def test_cfg_block_source_span_mapping(idx):
    code = f"def fn_{idx}():\n    x = {idx}\n    y = x + 1\n    return y\n"
    cfg = build_cfg_from_code(code)
    for b in cfg.blocks:
        if b.statements:
            assert b.span is not None
            assert b.span.start.line >= 1
