import ast
import re
from abc import ABC, abstractmethod
from typing import Tuple, Optional, Dict
from core.common.models import Diagnostic


class RemediationStrategy(ABC):
    """Abstract Base Class for AI Auto Fixer Remediation Strategies."""

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @abstractmethod
    def apply(self, source_code: str, diagnostic: Diagnostic) -> Tuple[str, str]:
        """Applies the strategy to source code. Returns (candidate_code, explanation)."""
        pass


class ContextManagerStrategy(RemediationStrategy):
    """Strategy 1: Converts resource assignment to context manager ('with' / 'async with')."""

    @property
    def strategy_name(self) -> str:
        return "context-manager"

    @property
    def description(self) -> str:
        return "Converts resource acquisition to context manager ('with' statement)."

    def apply(self, source_code: str, diagnostic: Diagnostic) -> Tuple[str, str]:
        lines = source_code.splitlines()
        target_idx = (diagnostic.location.start.line - 1) if (diagnostic.location and diagnostic.location.start) else 0

        if target_idx >= len(lines):
            return source_code, "Target line out of bounds"

        target_line = lines[target_idx]
        indent = len(target_line) - len(target_line.lstrip())
        indent_str = " " * indent

        match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*(.+)$", target_line)
        if match:
            leading_ws, var_name, expr = match.groups()
            new_lines = []
            for i, l in enumerate(lines):
                if i == target_idx:
                    new_lines.append(f"{leading_ws}with {expr} as {var_name}:")
                elif i > target_idx:
                    if l.strip().startswith(f"{var_name}.close()"):
                        continue  # Omit manual close inside with block
                    if l.strip() and len(l) - len(l.lstrip()) == indent:
                        new_lines.append(f"    {l}")
                    else:
                        new_lines.append(l)
                else:
                    new_lines.append(l)

            patched = "\n".join(new_lines)
            if source_code.endswith("\n"):
                patched += "\n"
            return patched, f"Converted '{var_name} = {expr}' to 'with {expr} as {var_name}:' context manager."

        return source_code, "Unchanged"


class TryFinallyStrategy(RemediationStrategy):
    """Strategy 2: Encloses execution in try/finally block with explicit .close()."""

    @property
    def strategy_name(self) -> str:
        return "try-finally"

    @property
    def description(self) -> str:
        return "Encloses statements in try/finally block with guaranteed .close()."

    def apply(self, source_code: str, diagnostic: Diagnostic) -> Tuple[str, str]:
        lines = source_code.splitlines()
        target_idx = (diagnostic.location.start.line - 1) if (diagnostic.location and diagnostic.location.start) else 0
        var_name = diagnostic.resource_variable or "handle"

        if target_idx >= len(lines):
            return source_code, "Target line out of bounds"

        target_line = lines[target_idx]
        indent = len(target_line) - len(target_line.lstrip())
        indent_str = " " * indent

        new_lines = lines[:target_idx + 1]
        new_lines.append(f"{indent_str}try:")
        for l in lines[target_idx + 1:]:
            if l.strip():
                new_lines.append(f"    {l}")
            else:
                new_lines.append(l)

        new_lines.append(f"{indent_str}finally:")
        new_lines.append(f"{indent_str}    {var_name}.close()")

        patched = "\n".join(new_lines)
        if source_code.endswith("\n"):
            patched += "\n"
        return patched, f"Enclosed operations in try/finally with '{var_name}.close()'."


class CloseInsertionStrategy(RemediationStrategy):
    """Strategy 3: Inserts explicit .close() call prior to return or scope exit."""

    @property
    def strategy_name(self) -> str:
        return "close-insertion"

    @property
    def description(self) -> str:
        return "Inserts explicit .close() call prior to scope exit or return statement."

    def apply(self, source_code: str, diagnostic: Diagnostic) -> Tuple[str, str]:
        lines = source_code.splitlines()
        var_name = diagnostic.resource_variable or "handle"
        new_lines = []

        inserted = False
        for l in lines:
            if not inserted and (l.strip().startswith("return ") or l.strip() == "return"):
                indent = len(l) - len(l.lstrip())
                new_lines.append(f"{' ' * indent}{var_name}.close()")
                inserted = True
            new_lines.append(l)

        if not inserted:
            indent = len(lines[-1]) - len(lines[-1].lstrip()) if lines else 0
            new_lines.append(f"{' ' * indent}{var_name}.close()")

        patched = "\n".join(new_lines)
        if source_code.endswith("\n"):
            patched += "\n"
        return patched, f"Inserted '{var_name}.close()' prior to scope exit."


class ExceptionSafeCleanupStrategy(RemediationStrategy):
    """Strategy 4: Adds exception-safe try/except/finally block."""

    @property
    def strategy_name(self) -> str:
        return "exception-safe"

    @property
    def description(self) -> str:
        return "Adds exception-safe cleanup block protecting against runtime errors."

    def apply(self, source_code: str, diagnostic: Diagnostic) -> Tuple[str, str]:
        tf = TryFinallyStrategy()
        return tf.apply(source_code, diagnostic)


class AsyncCleanupStrategy(RemediationStrategy):
    """Strategy 5: Converts async resources to 'async with' or 'await res.close()'."""

    @property
    def strategy_name(self) -> str:
        return "async-cleanup"

    @property
    def description(self) -> str:
        return "Refactors async resource to 'async with' context manager or 'await close()'."

    def apply(self, source_code: str, diagnostic: Diagnostic) -> Tuple[str, str]:
        lines = source_code.splitlines()
        target_idx = (diagnostic.location.start.line - 1) if (diagnostic.location and diagnostic.location.start) else 0

        if target_idx >= len(lines):
            return source_code, "Target line out of bounds"

        target_line = lines[target_idx]
        indent = len(target_line) - len(target_line.lstrip())
        leading_ws = " " * indent

        match = re.match(r"^(\s*)([a-zA-Z_]\w*)\s*=\s*(.+)$", target_line)
        if match:
            _, var_name, expr = match.groups()
            new_lines = []
            for i, l in enumerate(lines):
                if i == target_idx:
                    new_lines.append(f"{leading_ws}async with {expr} as {var_name}:")
                elif i > target_idx:
                    if l.strip() and len(l) - len(l.lstrip()) == indent:
                        new_lines.append(f"    {l}")
                    else:
                        new_lines.append(l)
                else:
                    new_lines.append(l)

            patched = "\n".join(new_lines)
            if source_code.endswith("\n"):
                patched += "\n"
            return patched, f"Converted async resource '{var_name}' to 'async with {expr} as {var_name}:'."

        return source_code, "Unchanged"


STRATEGY_MAP: Dict[str, RemediationStrategy] = {
    "context-manager": ContextManagerStrategy(),
    "try-finally": TryFinallyStrategy(),
    "close-insertion": CloseInsertionStrategy(),
    "exception-safe": ExceptionSafeCleanupStrategy(),
    "async-cleanup": AsyncCleanupStrategy(),
}
