from typing import Union
from pathlib import Path
import tree_sitter
import tree_sitter_python

from core.common.models import SourceLocation, Span


class ParserSecurityError(Exception):
    """Raised when parser depth or size security bounds are violated."""
    pass


class PythonParser:
    """Tree-sitter Python parser wrapper with depth checking & security bounds."""

    MAX_TREE_DEPTH = 500

    def __init__(self) -> None:
        self.language = tree_sitter.Language(tree_sitter_python.language())
        self.parser = tree_sitter.Parser(self.language)

    def parse_bytes(self, content: bytes) -> tree_sitter.Tree:
        tree = self.parser.parse(content)
        self._verify_depth(tree.root_node, depth=1)
        return tree

    def parse_string(self, source_code: str) -> tree_sitter.Tree:
        return self.parse_bytes(source_code.encode("utf-8"))

    def parse_file(self, file_path: Union[str, Path]) -> tree_sitter.Tree:
        path = Path(file_path)
        content = path.read_bytes()
        return self.parse_bytes(content)

    def _verify_depth(self, node: tree_sitter.Node, depth: int) -> None:
        if depth > self.MAX_TREE_DEPTH:
            raise ParserSecurityError(f"AST depth limit ({self.MAX_TREE_DEPTH}) exceeded. Potential malicious AST recursion.")
        for child in node.children:
            self._verify_depth(child, depth + 1)

    @staticmethod
    def get_location(point: tree_sitter.Point, byte_offset: int = 0) -> SourceLocation:
        return SourceLocation(
            line=point.row + 1,
            column=point.column + 1,
            byte_offset=byte_offset,
        )

    @staticmethod
    def get_span(node: tree_sitter.Node) -> Span:
        start_loc = PythonParser.get_location(node.start_point, node.start_byte)
        end_loc = PythonParser.get_location(node.end_point, node.end_byte)
        return Span(start=start_loc, end=end_loc)
