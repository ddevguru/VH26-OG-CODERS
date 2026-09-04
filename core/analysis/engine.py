from pathlib import Path
from typing import List, Union, Optional, Tuple
import time

from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic
from core.common.logger import get_logger
from core.parser.ast_parser import PythonAstParser, ParserSecurityError
from core.rules.base import ResourceLeakRule

logger = get_logger("leakguard.engine")


class AnalysisEngine:
    """Core Static Analysis Engine coordinating Python parsing via stdlib ast.parse(), AST visiting, and rule evaluation."""

    def __init__(self, config: Optional[LeakGuardConfig] = None) -> None:
        self.config = config or LeakGuardConfig()
        self.parser = PythonAstParser(max_depth=self.config.max_ast_depth)
        self.rule = ResourceLeakRule()

    def analyze_file(self, file_path: Union[str, Path]) -> List[Diagnostic]:
        diags, _, _, _ = self.analyze_file_with_stats(file_path)
        return diags

    def analyze_file_with_stats(self, file_path: Union[str, Path]) -> Tuple[List[Diagnostic], int, int, bool]:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {path}")
            return [], 0, 0, True

        file_size = path.stat().st_size
        if file_size > self.config.max_file_size_bytes:
            logger.warning(f"Skipping {path}: File size ({file_size} bytes) exceeds limit ({self.config.max_file_size_bytes} bytes).")
            return [], 0, 0, True

        start_time = time.time()

        try:
            ast_tree = self.parser.parse_file(path)
            diagnostics, funcs, res = self.rule.analyze_tree_with_stats(ast_tree, str(path))

            elapsed = time.time() - start_time
            logger.debug(f"Analyzed {path} in {elapsed:.3f}s - {len(diagnostics)} findings")
            return diagnostics, funcs, res, False

        except ParserSecurityError as e:
            logger.error(f"Security error parsing {path}: {e}")
            return [], 0, 0, True
        except SyntaxError as e:
            logger.warning(f"Syntax error in {path}: {e}")
            return [], 0, 0, True
        except Exception as e:
            logger.error(f"Error analyzing {path}: {e}", exc_info=True)
            return [], 0, 0, True


    def analyze_source_code(self, code: str, file_name: str = "<stdin>") -> List[Diagnostic]:
        ast_tree = self.parser.parse_string(code, filename=file_name)
        return self.rule.analyze_tree(ast_tree, file_name)

    def analyze_code(self, code: str, filename: str = "<stdin>") -> List[Diagnostic]:
        return self.analyze_source_code(code, file_name=filename)
