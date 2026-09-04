from pathlib import Path
from typing import List, Union, Optional
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
        self.parser = PythonAstParser()
        self.rule = ResourceLeakRule()

    def analyze_file(self, file_path: Union[str, Path]) -> List[Diagnostic]:
        path = Path(file_path)
        if not path.exists():
            logger.error(f"File not found: {path}")
            return []

        file_size = path.stat().st_size
        if file_size > self.config.max_file_size_bytes:
            logger.warning(f"Skipping {path}: File size ({file_size} bytes) exceeds limit ({self.config.max_file_size_bytes} bytes).")
            return []

        start_time = time.time()

        try:
            ast_tree = self.parser.parse_file(path)
            diagnostics = self.rule.analyze_tree(ast_tree, str(path))

            elapsed = time.time() - start_time
            logger.debug(f"Analyzed {path} in {elapsed:.3f}s - {len(diagnostics)} findings")
            return diagnostics

        except ParserSecurityError as e:
            logger.error(f"Security error parsing {path}: {e}")
            return []
        except SyntaxError as e:
            logger.warning(f"Syntax error in {path}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error analyzing {path}: {e}", exc_info=True)
            return []

    def analyze_source_code(self, code: str, file_name: str = "<stdin>") -> List[Diagnostic]:
        ast_tree = self.parser.parse_string(code, filename=file_name)
        return self.rule.analyze_tree(ast_tree, file_name)
