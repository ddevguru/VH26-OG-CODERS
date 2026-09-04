from pathlib import Path
from typing import Optional, List
import sys
import json
import typer
from rich.console import Console

from core.common.config import LeakGuardConfig
from core.common.models import Severity, Confidence
from services.scan.scanner import ProjectScanner
from services.baseline.engine import BaselineEngine
from presentation.terminal.formatter import TerminalFormatter
from presentation.sarif.exporter import SarifExporter
from presentation.json.exporter import JsonExporter

app = typer.Typer(
    name="leakguard",
    help="AST-Based Static Resource Lifetime Analysis for Python",
    add_completion=False,
)
console = Console()

SEVERITY_ORDER = {
    Severity.INFO: 1,
    Severity.WARNING: 2,
    Severity.ERROR: 3,
    Severity.CRITICAL: 4,
}


@app.command()
def scan(
    target: Path = typer.Argument(Path("."), help="Directory or file path to analyze"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text | json | sarif"),
    severity: Optional[Severity] = typer.Option(None, "--severity", "-s", help="Filter minimum severity threshold"),
    confidence: Optional[Confidence] = typer.Option(None, "--confidence", "-c", help="Filter minimum confidence threshold"),
    exclude: Optional[List[str]] = typer.Option(None, "--exclude", "-e", help="Glob pattern to exclude"),
    include: Optional[List[str]] = typer.Option(None, "--include", "-i", help="Glob pattern to include"),
    changed_only: bool = typer.Option(False, "--changed-only", help="Scan only git modified files"),
    baseline: Optional[Path] = typer.Option(None, "--baseline", "-b", help="Path to baseline JSON file"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of parallel worker processes"),
    fail_on: str = typer.Option("error", "--fail-on", help="Threshold for non-zero exit code: error | warning | critical | info | none"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress output summary"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    out: Optional[Path] = typer.Option(None, "--out", "-o", help="File path to save JSON or SARIF report"),
    update_baseline: bool = typer.Option(False, "--update-baseline", help="Update or create baseline file with current findings"),
) -> None:
    """Scans Python source files for unclosed resources across control-flow paths."""
    try:
        min_sev = severity or Severity.INFO
        min_conf = confidence or Confidence.LOW

        default_excludes = ["**/venv/**", "**/.venv/**", "**/__pycache__/**", "**/build/**", "**/dist/**", "**/.git/**", "**/.pytest_cache/**"]
        combined_excludes = default_excludes + (exclude if exclude else [])

        config = LeakGuardConfig(
            fail_on=fail_on.lower(),
            min_severity=min_sev,
            min_confidence=min_conf,
            exclude_patterns=combined_excludes,
            include_patterns=include or ["**/*.py"],
            changed_only=changed_only,
            baseline_file=str(baseline) if baseline else None,
            workers=workers,
            output_format=format.lower(),
            report_file=str(out) if out else None,
            quiet=quiet,
            verbose=verbose,
        )

        scanner = ProjectScanner(config)
        scan_result = scanner.scan_directory(target)

        if update_baseline and (baseline or out):
            target_base_path = baseline or out
            baseline_engine = BaselineEngine()
            baseline_engine.save_baseline(scan_result.diagnostics, target_base_path)
            if not quiet:
                console.print(f"[bold green][OK] Baseline updated at '{target_base_path}'[/bold green]")

        # Format output
        fmt = format.lower()
        if fmt == "sarif":
            sarif_exporter = SarifExporter()
            if out:
                sarif_exporter.write_sarif_file(scan_result, out)
                if not quiet:
                    console.print(f"[bold green][OK] SARIF 2.1.0 report written to '{out}'[/bold green]")
            else:
                sarif_dict = sarif_exporter.to_sarif_dict(scan_result)
                console.print_json(json.dumps(sarif_dict))

        elif fmt == "json":
            json_exporter = JsonExporter()
            if out:
                json_exporter.write_json_file(scan_result, out)
                if not quiet:
                    console.print(f"[bold green][OK] JSON report written to '{out}'[/bold green]")
            else:
                json_dict = json_exporter.to_json_dict(scan_result)
                console.print_json(json.dumps(json_dict))

        else:  # text / cli
            formatter = TerminalFormatter(console)
            formatter.print_scan_result(scan_result, quiet=quiet, verbose=verbose)

        # Fail-on threshold evaluation
        fail_threshold = fail_on.lower()
        if fail_threshold != "none":
            blocking_level = {
                "info": 1,
                "warning": 2,
                "error": 3,
                "critical": 4,
            }.get(fail_threshold, 3)

            has_blocking = False
            for diag in scan_result.diagnostics:
                d_level = SEVERITY_ORDER.get(diag.severity, 2)
                if d_level >= blocking_level:
                    has_blocking = True
                    break

            if has_blocking:
                if not quiet:
                    console.print(f"\n[bold red][X] Scan Failed: Findings violate '--fail-on {fail_threshold}' threshold.[/bold red]")
                sys.exit(1)

        sys.exit(0)

    except (FileNotFoundError, ValueError) as e:
        if not quiet:
            console.print(f"[bold red][Error] Scanner Failure: {e}[/bold red]")
        sys.exit(2)
    except Exception as e:
        if not quiet:
            console.print(f"[bold red][Error] Scanner Failure: {e}[/bold red]")
        sys.exit(2)


@app.command()
def version() -> None:
    """Prints the version of LeakGuard."""
    console.print("[bold cyan]LeakGuard v0.1.0[/bold cyan] - Static Resource Lifetime Analysis for Python")


if __name__ == "__main__":
    app()
