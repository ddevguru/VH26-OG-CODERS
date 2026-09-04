import pytest
import ast
from core.parser.ast_parser import PythonAstParser
from core.ast.visitor import AstFunctionCollector


def test_ast_collector() -> None:
    code = """
class MyService:
    def process_file(self, path):
        f = open(path)
        if path is None:
            return
        with open("temp.txt") as t:
            t.read()
        try:
            f.read()
        except Exception as e:
            raise e
        finally:
            f.close()
"""
    parser = PythonAstParser()
    tree = parser.parse_string(code)
    collector = AstFunctionCollector()
    collector.visit(tree)

    assert len(collector.functions) == 1
    func_node, scope = collector.functions[0]
    assert func_node.name == "process_file"  # type: ignore
    assert scope == "MyService"
