"""Inline Comment Mapper — maps diagnostic line numbers to GitHub diff positions.

GitHub's pull request review API requires a 'line' parameter (line number on
the right side of the diff) for inline comments. We parse the diff hunks to
validate that a finding's line is within the PR's changed lines.
"""
import re
from typing import Dict, List, Optional, Set, Tuple

from core.common.models import Diagnostic


class InlineCommentMapper:
    """Maps LeakGuard diagnostic line numbers to GitHub PR diff positions.

    Only creates inline comments for findings on lines that appear in the
    PR diff. For findings outside the diff, we include them in the summary
    comment only.
    """

    def __init__(self) -> None:
        pass

    def parse_changed_lines(self, patch: str) -> Set[int]:
        """Parse a file's unified diff patch to extract changed line numbers.

        Returns a set of line numbers (1-indexed, right side / new file) that
        appear as additions (+) in the diff. These are the only lines where
        GitHub allows inline review comments.
        """
        changed_lines: Set[int] = set()
        if not patch:
            return changed_lines

        current_line = 0
        for line in patch.splitlines():
            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
            if hunk_match:
                current_line = int(hunk_match.group(1)) - 1
                continue

            if line.startswith("+") and not line.startswith("+++"):
                current_line += 1
                changed_lines.add(current_line)
            elif line.startswith("-") and not line.startswith("---"):
                pass  # Removed lines don't advance new file counter
            else:
                current_line += 1

        return changed_lines

    def build_file_changed_lines_map(
        self, pr_files: list
    ) -> Dict[str, Set[int]]:
        """Build a mapping of filename → set of changed line numbers from PR files.

        Args:
            pr_files: List of PRFile objects from GitHubPullRequestService.
        """
        result = {}
        for f in pr_files:
            result[f.filename] = self.parse_changed_lines(f.patch)
        return result

    def filter_inline_eligible(
        self,
        diagnostics: List[Diagnostic],
        changed_lines_map: Dict[str, Set[int]],
        file_path_prefix: str = "",
    ) -> Tuple[List[Tuple[Diagnostic, int]], List[Diagnostic]]:
        """Split diagnostics into inline-eligible and summary-only.

        Returns:
            (inline_list, summary_only_list)
            inline_list: [(diagnostic, line_number)] for findings on changed lines
            summary_only_list: diagnostics outside the PR diff
        """
        inline = []
        summary_only = []

        for d in diagnostics:
            # Normalize file path
            file_path = d.file_path
            if file_path_prefix and file_path.startswith(file_path_prefix):
                file_path = file_path[len(file_path_prefix):].lstrip("/\\")

            line = d.location.start.line if (d.location and d.location.start) else None
            if line is None:
                summary_only.append(d)
                continue

            changed = changed_lines_map.get(file_path, set())
            if line in changed:
                inline.append((d, line))
            else:
                # Also try with nearby lines (±3) for context
                nearby_match = any(
                    abs(l - line) <= 3 for l in changed
                )
                if nearby_match:
                    # Use the closest changed line
                    closest = min(changed, key=lambda l: abs(l - line)) if changed else line
                    inline.append((d, closest))
                else:
                    summary_only.append(d)

        return inline, summary_only
