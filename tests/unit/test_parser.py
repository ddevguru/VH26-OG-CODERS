import pytest
import ast
from core.parser.ast_parser import PythonAstParser
from core.common.models import Span


def test_python_ast_parser_basic() -> None:
    parser = PythonAstParser()
    code = "def foo():\n    print('Hello LeakGuard')\n"
    tree = parser.parse_string(code)
    assert isinstance(tree, ast.Module)
    assert len(tree.body) == 1
    assert isinstance(tree.body[0], ast.FunctionDef)


def test_python_ast_parser_span_extraction() -> None:
    parser = PythonAstParser()
    code = "x = open('test.txt')"
    tree = parser.parse_string(code)
    stmt = tree.body[0]
    span = PythonAstParser.get_span(stmt)

    assert isinstance(span, Span)
    assert span.start.line == 1
    assert span.start.column == 1
    assert span.end.line == 1
    assert span.end.column == 21
