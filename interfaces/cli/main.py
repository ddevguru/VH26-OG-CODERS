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
def benchmark() -> None:
    """Runs the 300+ fixture static analysis benchmark suite and outputs performance & accuracy metrics."""
    from benchmarks.cli import run_benchmark_suite
    sys.exit(run_benchmark_suite())


@app.command()
def server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host IP to bind SaaS control plane server"),
    port: int = typer.Option(8000, "--port", "-p", help="Port for SaaS control plane server"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for dev mode"),
) -> None:
    """Launches the LeakGuard Commercial SaaS Control Plane API server."""
    import uvicorn
    console.print(f"[bold green]Starting LeakGuard SaaS Control Plane API at http://{host}:{port}[/bold green]")
    uvicorn.run("packages.saas.app:app", host=host, port=port, reload=reload)


@app.command()
def upload(
    target: Path = typer.Argument(Path("."), help="Directory or file path to analyze"),
    repo: str = typer.Option(..., "--repo", "-r", help="Repository name in control plane"),
    url: str = typer.Option("http://127.0.0.1:8000", "--url", help="SaaS control plane server URL"),
    token: str = typer.Option(..., "--token", "-t", help="SaaS API Bearer Token"),
    org_id: Optional[str] = typer.Option(None, "--org-id", help="Organization ID (optional)"),
) -> None:
    """Scans locally and transmits structured findings metadata (NO raw source code) to SaaS Control Plane."""
    from services.saas.sync import upload_scan_results
    try:
        config = LeakGuardConfig()
        scanner = ProjectScanner(config)
        scan_result = scanner.scan_directory(target)
        res = upload_scan_results(
            scan_result=scan_result,
            repository_name=repo,
            control_plane_url=url,
            api_token=token,
            organization_id=org_id,
        )
        console.print(f"[bold green][OK] Scan results synced to SaaS Control Plane successfully! Scan ID: {res.get('id')}[/bold green]")
    except Exception as e:
        console.print(f"[bold red][Error] SaaS Upload Failed: {e}[/bold red]")
        sys.exit(1)


@app.command()
def fix(
    target: Path = typer.Argument(Path("."), help="Directory or file path to analyze and generate AI-assisted patches"),
    apply: bool = typer.Option(False, "--apply", help="Automatically write verified patches to source code upon human confirmation"),
    api_key: Optional[str] = typer.Option(None, "--api-key", help="Optional LLM API key (defaults to LEAKGUARD_LLM_API_KEY)"),
) -> None:
    """Generates AI-assisted remediation suggestions and validates patches against a 9-step AST pipeline."""
    from services.ai.remediator import AIRemediator
    from services.ai.validator import PatchValidator
    from core.analysis.engine import AnalysisEngine

    try:
        config = LeakGuardConfig()
        scanner = ProjectScanner(config)
        scan_result = scanner.scan_directory(target) if target.is_dir() else ScanResult(
            status="success",
            scanned_files_count=1,
            duration_seconds=0.0,
            diagnostics=AnalysisEngine(config).analyze_file(target),
            policy_passed=True,
        )

        if not scan_result.diagnostics:
            console.print("[bold green][OK] Zero resource leaks detected. No fixes required.[/bold green]")
            sys.exit(0)

        remediator = AIRemediator(api_key=api_key)
        validator = PatchValidator(config)

        console.print(f"\n[bold cyan]Found {len(scan_result.diagnostics)} potential resource leaks. Initializing AI remediation & 9-step validation pipeline...[/bold cyan]\n")

        for idx, diag in enumerate(scan_result.diagnostics, 1):
            file_p = Path(diag.file_path)
            if not file_p.exists():
                continue

            orig_source = file_p.read_text(encoding="utf-8")
            rem_res = remediator.generate_candidate_patch(orig_source, diag)
            val_report = validator.validate_patch(orig_source, rem_res.candidate_code, diag, file_name=file_p.name)

            console.print(f"[bold yellow]Finding #{idx}: {diag.rule_id} at {diag.file_path}:{diag.location.start.line if diag.location else 1}[/bold yellow]")
            console.print(f"[gray]{rem_res.explanation}[/gray]")
            console.print(f"[bold font-mono text-emerald-400]Suggested Fix:[/bold font-mono text-emerald-400] {rem_res.suggested_fix} ({rem_res.provider})")

            if val_report.is_valid:
                console.print("[bold green][VALIDATED] Patch passed 9-step AST validation (Target leak cleared, 0 new leaks)[/bold green]")
                console.print("\n[bold border-gray-700]Unified Diff Preview:[/bold border-gray-700]")
                console.print(val_report.unified_diff)

                if apply:
                    file_p.write_text(rem_res.candidate_code, encoding="utf-8")
                    console.print(f"[bold green][APPLIED] Verified patch written to '{file_p}' successfully![/bold green]\n")
                else:
                    console.print(f"[bold yellow][PENDING APPROVAL] Pass '--apply' flag to apply this verified patch to '{file_p}'.[/bold yellow]\n")
            else:
                console.print(f"[bold red][REJECTED] Patch validation failed: {val_report.failure_reason}[/bold red]\n")

    except Exception as e:
        console.print(f"[bold red][Error] Remediation Failure: {e}[/bold red]")
        sys.exit(1)


@app.command()
def dashboard(
    port: int = typer.Option(3000, "--port", "-p", help="Port for LeakGuard Commercial Web Dashboard"),
) -> None:
    """Launches the LeakGuard Commercial Web Dashboard dev server."""
    import subprocess
    dash_dir = Path(__file__).parent.parent.parent / "presentation" / "dashboard"
    console.print(f"[bold green]Starting LeakGuard Web Dashboard at http://localhost:{port}[/bold green]")
    subprocess.run(["npm", "run", "dev"], cwd=dash_dir, shell=True)


@app.command()
def version() -> None:
    """Prints the version of LeakGuard."""
    console.print("[bold cyan]LeakGuard v0.1.0[/bold cyan] - Static Resource Lifetime Analysis for Python")


if __name__ == "__main__":
    app()




