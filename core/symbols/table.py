from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
from core.common.models import Span


@dataclass
class Symbol:
    name: str
    scope_name: str = "global"
    symbol_id: Optional[str] = None
    type_annotation: Optional[str] = None
    declaration_span: Optional[Span] = None
    assignment_spans: List[Span] = field(default_factory=list)
    read_spans: List[Span] = field(default_factory=list)
    write_spans: List[Span] = field(default_factory=list)
    aliases: Set[str] = field(default_factory=set)
    is_resource: bool = False
    resource_type: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.symbol_id:
            self.symbol_id = f"{self.scope_name}::{self.name}"
        if self.declaration_span and self.declaration_span not in self.assignment_spans:
            self.assignment_spans.append(self.declaration_span)


class SymbolTable:
    """Symbol Table tracking variable bindings, declarations, references, reads, writes, and aliases within a scope."""

    def __init__(self, scope_name: str = "global") -> None:
        self.scope_name = scope_name
        self.symbols: Dict[str, Symbol] = {}

    def insert(self, symbol: Symbol) -> Symbol:
        if symbol.name in self.symbols:
            existing = self.symbols[symbol.name]
            if symbol.declaration_span and symbol.declaration_span not in existing.assignment_spans:
                existing.assignment_spans.append(symbol.declaration_span)
            if symbol.type_annotation:
                existing.type_annotation = symbol.type_annotation
            return existing
        else:
            self.symbols[symbol.name] = symbol
            return symbol

    def lookup(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def contains(self, name: str) -> bool:
        return name in self.symbols

    def add_assignment(self, name: str, span: Span) -> Optional[Symbol]:
        sym = self.lookup(name)
        if not sym:
            sym = Symbol(name=name, scope_name=self.scope_name, declaration_span=span)
            self.insert(sym)
        elif span not in sym.assignment_spans:
            sym.assignment_spans.append(span)
        return sym

    def add_read(self, name: str, span: Span) -> Optional[Symbol]:
        sym = self.lookup(name)
        if sym and span not in sym.read_spans:
            sym.read_spans.append(span)
        return sym

    def add_write(self, name: str, span: Span) -> Optional[Symbol]:
        sym = self.lookup(name)
        if not sym:
            sym = Symbol(name=name, scope_name=self.scope_name, declaration_span=span)
            self.insert(sym)
        if span not in sym.write_spans:
            sym.write_spans.append(span)
        return sym

    def add_alias(self, name: str, alias_name: str) -> None:
        sym = self.lookup(name)
        if sym:
            sym.aliases.add(alias_name)
        alias_sym = self.lookup(alias_name)
        if alias_sym:
            alias_sym.aliases.add(name)

