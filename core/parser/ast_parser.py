import ast
from pathlib import Path
from typing import Union, Optional

from core.common.models import SourceLocation, Span


class ParserSecurityError(Exception):
    """Raised when parser depth or size security bounds are violated."""
    pass


class PythonAstParser:
    """Safe Python source code parser wrapping standard library ast.parse()."""

    MAX_AST_DEPTH = 500

    def parse_string(self, source_code: str, filename: str = "<stdin>") -> ast.AST:
        """Parses Python source string into an ast.AST module without code execution."""
        try:
            tree = ast.parse(source_code, filename=filename, type_comments=True)
            self._verify_depth(tree, depth=1)
            return tree
        except SyntaxError as e:
            # Return empty module or reraise depending on tolerance
            raise e

    def parse_file(self, file_path: Union[str, Path]) -> ast.AST:
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.parse_string(content, filename=str(path))

    def parse_code(self, source_code: str, filename: str = "<stdin>") -> ast.AST:
        return self.parse_string(source_code, filename=filename)

    def _verify_depth(self, node: ast.AST, depth: int) -> None:
        if depth > self.MAX_AST_DEPTH:
            raise ParserSecurityError(f"AST recursion depth limit ({self.MAX_AST_DEPTH}) exceeded.")
        for child in ast.iter_child_nodes(node):
            self._verify_depth(child, depth + 1)

    @staticmethod
    def get_span(node: ast.AST) -> Span:
        """Extracts Span from standard ast.AST node location attributes."""
        lineno = getattr(node, "lineno", None) or 1
        col_offset = getattr(node, "col_offset", None)
        col_offset = (col_offset + 1) if col_offset is not None else 1

        end_lineno = getattr(node, "end_lineno", None) or lineno
        end_col_offset = getattr(node, "end_col_offset", None)
        end_col_offset = (end_col_offset + 1) if end_col_offset is not None else col_offset

        return Span(
            start=SourceLocation(line=lineno, column=col_offset),
            end=SourceLocation(line=end_lineno, column=end_col_offset),
        )
