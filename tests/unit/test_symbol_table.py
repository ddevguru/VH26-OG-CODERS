import pytest
from core.common.models import SourceLocation, Span
from core.symbols.table import Symbol, SymbolTable


def test_symbol_table_insert_and_lookup():
    table = SymbolTable(scope_name="test_scope")
    span1 = Span(start=SourceLocation(line=1, column=1), end=SourceLocation(line=1, column=10))
    sym = Symbol(name="var_a", scope_name="test_scope", declaration_span=span1)
    
    table.insert(sym)
    assert table.contains("var_a")
    retrieved = table.lookup("var_a")
    assert retrieved is not None
    assert retrieved.name == "var_a"
    assert retrieved.scope_name == "test_scope"
    assert retrieved.symbol_id == "test_scope::var_a"
    assert span1 in retrieved.assignment_spans


def test_symbol_table_reads_and_writes():
    table = SymbolTable(scope_name="global")
    span_write = Span(start=SourceLocation(line=2, column=5), end=SourceLocation(line=2, column=10))
    span_read = Span(start=SourceLocation(line=3, column=8), end=SourceLocation(line=3, column=12))

    table.add_write("f", span_write)
    table.add_read("f", span_read)

    sym = table.lookup("f")
    assert sym is not None
    assert span_write in sym.write_spans
    assert span_read in sym.read_spans


def test_symbol_table_alias_tracking():
    table = SymbolTable(scope_name="func_scope")
    span_a = Span(start=SourceLocation(line=1, column=1), end=SourceLocation(line=1, column=5))
    span_b = Span(start=SourceLocation(line=2, column=1), end=SourceLocation(line=2, column=5))

    table.insert(Symbol(name="res1", scope_name="func_scope", declaration_span=span_a))
    table.insert(Symbol(name="alias1", scope_name="func_scope", declaration_span=span_b))

    table.add_alias("alias1", "res1")

    sym_a = table.lookup("res1")
    sym_alias = table.lookup("alias1")

    assert sym_a is not None and sym_alias is not None
    assert "res1" in sym_alias.aliases
    assert "alias1" in sym_a.aliases
