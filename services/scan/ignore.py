from pathlib import Path
from typing import List, Union, Optional
import fnmatch


class IgnoreFilter:
    """Parses and applies .gitignore, .leakguardignore, and explicit glob patterns."""

    def __init__(self, root_dir: Union[str, Path], extra_excludes: Optional[List[str]] = None, extra_includes: Optional[List[str]] = None) -> None:
        self.root = Path(root_dir).resolve()
        self.patterns: List[str] = []
        self.includes: List[str] = extra_includes or []

        # Default excludes
        default_excludes = ["**/.git/**", "**/venv/**", "**/.venv/**", "**/__pycache__/**", "**/build/**", "**/dist/**", "**/.pytest_cache/**"]
        self.patterns.extend(default_excludes)

        if extra_excludes:
            self.patterns.extend(extra_excludes)

        # Parse .gitignore
        gitignore_path = self.root / ".gitignore"
        if gitignore_path.is_file():
            self._load_ignore_file(gitignore_path)

        # Parse .leakguardignore
        leakguardignore_path = self.root / ".leakguardignore"
        if leakguardignore_path.is_file():
            self._load_ignore_file(leakguardignore_path)

    def _load_ignore_file(self, file_path: Path) -> None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line.endswith("/"):
                    clean = line.rstrip("/")
                    self.patterns.append(f"**/{clean}/**")
                    self.patterns.append(f"{clean}/**")
                else:
                    self.patterns.append(line)
        except Exception:
            pass

    @staticmethod
    def _match_glob(rel_str: str, filename: str, pattern: str) -> bool:
        pattern_clean = pattern.lstrip("/")
        if fnmatch.fnmatch(rel_str, pattern_clean) or fnmatch.fnmatch(filename, pattern_clean):
            return True
        if pattern_clean.startswith("**/"):
            sub_pat = pattern_clean[3:]
            if fnmatch.fnmatch(rel_str, sub_pat) or fnmatch.fnmatch(filename, sub_pat):
                return True
        if pattern_clean.endswith("/**"):
            sub_pat = pattern_clean[:-3]
            if fnmatch.fnmatch(rel_str, sub_pat) or fnmatch.fnmatch(filename, sub_pat):
                return True
        return False

    def is_ignored(self, file_path: Union[str, Path]) -> bool:
        path = Path(file_path).resolve()
        try:
            rel_str = str(path.relative_to(self.root)).replace("\\", "/")
        except ValueError:
            rel_str = str(path).replace("\\", "/")

        filename = path.name

        # If explicit includes are provided, must match at least one include
        if self.includes:
            matched_include = False
            for inc in self.includes:
                if self._match_glob(rel_str, filename, inc):
                    matched_include = True
                    break
            if not matched_include:
                return True

        # Check excludes / ignore patterns
        for pattern in self.patterns:
            if self._match_glob(rel_str, filename, pattern):
                return True
            parts = rel_str.split("/")
            for i in range(1, len(parts)):
                dir_path = "/".join(parts[:i])
                if self._match_glob(dir_path, parts[i-1], pattern):
                    return True

        return False
