from typing import Union
from pathlib import Path
import tree_sitter
import tree_sitter_java

from packages.common.models import SourceLocation, Span


class JavaParser:
    """Wrapper around tree-sitter Java parser providing structured CST nodes and Spans."""

    def __init__(self) -> None:
        self.language = tree_sitter.Language(tree_sitter_java.language())
        self.parser = tree_sitter.Parser(self.language)

    def parse_bytes(self, content: bytes) -> tree_sitter.Tree:
        return self.parser.parse(content)

    def parse_string(self, source_code: str) -> tree_sitter.Tree:
        return self.parse_bytes(source_code.encode("utf-8"))

    def parse_file(self, file_path: Union[str, Path]) -> tree_sitter.Tree:
        path = Path(file_path)
        content = path.read_bytes()
        return self.parse_bytes(content)

    @staticmethod
    def get_location(point: tree_sitter.Point, byte_offset: int = 0) -> SourceLocation:
        """Converts tree-sitter 0-indexed Point to LeakGuard 1-indexed SourceLocation."""
        return SourceLocation(
            line=point.row + 1,
            column=point.column + 1,
            byte_offset=byte_offset,
        )

    @staticmethod
    def get_span(node: tree_sitter.Node) -> Span:
        """Extracts Span from a tree-sitter Node."""
        start_loc = JavaParser.get_location(node.start_point, node.start_byte)
        end_loc = JavaParser.get_location(node.end_point, node.end_byte)
        return Span(start=start_loc, end=end_loc)
