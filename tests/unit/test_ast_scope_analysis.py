import ast
import pytest
from core.parser.ast_parser import PythonAstParser
from core.ast.analyzer import AstScopeSymbolAnalyzer
from core.scopes.scope_manager import ScopeType


def analyze_code(code_str: str):
    parser = PythonAstParser()
    tree = parser.parse_code(code_str)
    analyzer = AstScopeSymbolAnalyzer()
    return analyzer.analyze_ast(tree)


def test_functions_and_classes_scopes():
    code = """
class DataProcessor:
    def __init__(self, filename: str):
        self.filename = filename

    async def fetch_async(self):
        data = "test"
        return data

def top_level_func(a, b=10):
    c = a + b
    return c
"""
    result = analyze_code(code)
    
    # Class & methods check
    assert len(result.classes) == 1
    assert result.classes[0][0].name == "DataProcessor"

    # Function names check
    func_names = [f[0].name for f in result.functions]  # type: ignore
    assert "__init__" in func_names
    assert "fetch_async" in func_names
    assert "top_level_func" in func_names

    # Check Scope manager hierarchy
    top_scope = result.find_scope("top_level_func")
    assert top_scope is not None
    assert top_scope.scope_type == ScopeType.FUNCTION
    assert "a" in top_scope.variables
    assert "b" in top_scope.variables
    assert "c" in top_scope.variables


def test_global_and_nonlocal():
    code = """
x = 100

def outer():
    y = 50
    def inner():
        nonlocal y
        global x
        y = 60
        x = 200
    inner()
"""
    result = analyze_code(code)
    inner_scope = result.find_scope("outer.inner")
    assert inner_scope is not None
    assert "x" in inner_scope.global_vars
    assert "y" in inner_scope.nonlocal_vars


def test_closures_and_lambdas():
    code = """
def make_multiplier(n):
    return lambda x: x * n
"""
    result = analyze_code(code)
    func_scope = result.find_scope("make_multiplier")
    assert func_scope is not None
    assert "n" in func_scope.variables


def test_imports_and_aliases():
    code = """
import os
import sys as system
from pathlib import Path as FilePath
"""
    result = analyze_code(code)
    global_syms = result.global_scope.symbol_table.symbols
    assert "os" in global_syms
    assert "system" in global_syms
    assert "FilePath" in global_syms

    import_aliases = [imp[1] for imp in result.imports]
    assert "system" in import_aliases
    assert "FilePath" in import_aliases


test_assignments_and_aliases_code = """
def process():
    f = open("data.txt")
    handle = f
    return handle
"""

def test_assignments_and_aliases():
    result = analyze_code(test_assignments_and_aliases_code)
    scope = result.find_scope("process")
    assert scope is not None
    sym_handle = scope.symbol_table.lookup("handle")
    assert sym_handle is not None
    assert "f" in sym_handle.aliases


def test_comprehensions_scope():
    code = """
def get_squares(numbers):
    squares = [x * x for x in numbers if x > 0]
    return squares
"""
    result = analyze_code(code)
    func_scope = result.find_scope("get_squares")
    assert func_scope is not None
    assert "squares" in func_scope.variables
    # x should be isolated to comprehension scope
    assert "x" not in func_scope.variables


def test_async_with_and_try_except():
    code = """
async def run_task():
    try:
        async with open_res() as r:
            await r.read()
    except Exception as err:
        log(err)
    finally:
        cleanup()
"""
    result = analyze_code(code)
    func_scope = result.find_scope("run_task")
    assert func_scope is not None
    assert "r" in func_scope.variables
    assert "err" in func_scope.variables


def test_match_case_python310():
    code = """
def evaluate(command):
    match command:
        case "start":
            status = "running"
        case "stop":
            status = "stopped"
        case _:
            status = "unknown"
    return status
"""
    result = analyze_code(code)
    func_scope = result.find_scope("evaluate")
    assert func_scope is not None
    assert "command" in func_scope.variables
    assert "status" in func_scope.variables
