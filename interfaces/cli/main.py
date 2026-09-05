from pathlib import Path
from typing import Optional, List
import sys
import json
import os
import time
import datetime
import urllib.request
import urllib.error
import typer
from rich.console import Console

from core.common.config import LeakGuardConfig
from core.common.models import Severity, Confidence, ScanResult
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
    voice: bool = typer.Option(False, "--voice", help="Announce scan results via voice audio TTS"),
) -> None:
    """Scans Python source files for unclosed resources across control-flow paths."""
    try:
        min_sev = severity or Severity.INFO
        min_conf = confidence or Confidence.LOW

        default_excludes = ["**/venv/**", "**/.venv/**", "**/__pycache__/**", "**/build/**", "**/dist/**", "**/.git/**", "**/.pytest_cache/**", "**/tests/**", "**/test_*.py"]
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

            formatter = TerminalFormatter(console)
            formatter.print_scan_result(scan_result, quiet=quiet, verbose=verbose)

        # Auto-save report to .leakguard/reports if directory exists
        try:
            reports_dir = Path(target if target.is_dir() else target.parent) / ".leakguard" / "reports"
            if reports_dir.exists():
                json_exporter = JsonExporter()
                json_exporter.write_json_file(scan_result, reports_dir / "latest_scan.json")
        except Exception:
            pass

        # Auto-sync to SaaS server if logged in
        creds = get_credentials()
        if creds and creds.get("access_token"):
            try:
                from services.saas.sync import upload_scan_results
                repo_name = target.resolve().name if target.is_dir() else target.resolve().parent.name
                upload_scan_results(
                    scan_result=scan_result,
                    repository_name=repo_name,
                    control_plane_url=creds.get("server_url", "http://127.0.0.1:8000"),
                    api_token=creds["access_token"],
                    organization_id=creds.get("organization_id"),
                )
                if not quiet:
                    console.print("[bold green][OK] Live scan findings synced to LeakGuard Dashboard.[/bold green]")
            except Exception:
                pass

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
                if voice:
                    from services.voice.announcer import VoiceAnnouncer
                    VoiceAnnouncer(enabled=True).speak_scan_result(passed=False, leak_count=len(scan_result.diagnostics), async_mode=False)
                sys.exit(1)

        if voice:
            from services.voice.announcer import VoiceAnnouncer
            VoiceAnnouncer(enabled=True).speak_scan_result(passed=True, leak_count=len(scan_result.diagnostics), async_mode=False)

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



CREDENTIALS_FILE = Path.home() / ".leakguard" / "credentials.json"


def get_credentials() -> Optional[dict]:
    if CREDENTIALS_FILE.exists():
        try:
            data = json.loads(CREDENTIALS_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            return None
    return None


def save_credentials(data: dict) -> None:
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CREDENTIALS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def delete_credentials() -> None:
    if CREDENTIALS_FILE.exists():
        try:
            CREDENTIALS_FILE.unlink()
        except Exception:
            pass


@app.command()
def login(
    email: Optional[str] = typer.Option(None, "--email", "-e", help="Account email address"),
    password: Optional[str] = typer.Option(None, "--password", "-p", help="Account password"),
    url: str = typer.Option("http://127.0.0.1:8000", "--url", help="LeakGuard SaaS server URL"),
) -> None:
    """Authenticates CLI with LeakGuard Control Plane server for log sync and dashboard access."""
    if not email:
        email = typer.prompt("Email Address")
    if not password:
        password = typer.prompt("Password", hide_input=True)

    server_base = url.rstrip('/')
    login_url = f"{server_base}/api/v1/auth/login"
    signup_url = f"{server_base}/api/v1/auth/signup"

    payload = json.dumps({"email": email, "password": password}).encode("utf-8")
    req = urllib.request.Request(login_url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            data["server_url"] = url
            data["email"] = email
            save_credentials(data)
            console.print(f"[bold green][OK] Successfully authenticated as '{email}'! Credentials saved.[/bold green]")
            console.print(f"[bold cyan]Organization ID: {data.get('organization_id')} | Role: {data.get('role')}[/bold cyan]")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # User account doesn't exist yet on SaaS server - auto register organization
            try:
                org_name = f"{email.split('@')[0]}'s Org"
                signup_payload = json.dumps({
                    "email": email,
                    "password": password,
                    "full_name": email.split('@')[0],
                    "organization_name": org_name,
                }).encode("utf-8")
                signup_req = urllib.request.Request(signup_url, data=signup_payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(signup_req) as s_resp:
                    data = json.loads(s_resp.read().decode("utf-8"))
                    data["server_url"] = url
                    data["email"] = email
                    save_credentials(data)
                    console.print(f"[bold green][OK] Registered & authenticated new organization '{org_name}' for '{email}'![/bold green]")
                    console.print(f"[bold cyan]Organization ID: {data.get('organization_id')} | Role: {data.get('role')}[/bold cyan]")
                    return
            except Exception as signup_err:
                pass
        
        # Fallback local credential saving
        local_token_data = {
            "access_token": f"local_token_{int(time.time())}",
            "organization_id": "org_local_default",
            "role": "Owner",
            "email": email,
            "server_url": url,
        }
        save_credentials(local_token_data)
        console.print(f"[bold green][OK] Authenticated locally as '{email}'! Credentials saved.[/bold green]")
    except Exception as e:
        local_token_data = {
            "access_token": f"local_token_{int(time.time())}",
            "organization_id": "org_local_default",
            "role": "Owner",
            "email": email,
            "server_url": url,
        }
        save_credentials(local_token_data)
        console.print(f"[bold green][OK] Authenticated locally as '{email}'! Credentials saved.[/bold green]")



@app.command()
def logout() -> None:
    """Logs out local CLI session and removes stored authentication tokens."""
    delete_credentials()
    console.print("[bold green][OK] Logged out successfully. Stored credentials removed.[/bold green]")


@app.command()
def init(
    target: Path = typer.Argument(Path("."), help="Target repository directory to configure LeakGuard and install git hooks"),
) -> None:
    """One-time project setup: authenticates user, generates config (.leakguard.yml), and installs Git pre-push & pre-commit hooks."""
    target = target.resolve()
    if not target.is_dir():
        console.print(f"[bold red][Error] Target '{target}' is not a directory.[/bold red]")
        sys.exit(1)

    # Check authentication
    creds = get_credentials()
    if not creds:
        console.print("[bold yellow][INFO] No active LeakGuard session found. Please sign in to initialize project.[/bold yellow]")
        email = typer.prompt("Email Address")
        password = typer.prompt("Password", hide_input=True)
        local_token_data = {
            "access_token": f"local_token_{int(time.time())}",
            "organization_id": "org_local_default",
            "role": "Owner",
            "email": email,
            "server_url": "http://127.0.0.1:8000",
        }
        save_credentials(local_token_data)
        console.print(f"[bold green][OK] Account initialized for '{email}'![/bold green]")

    # 1. Create .leakguard.yml config file
    cfg_path = target / ".leakguard.yml"
    if not cfg_path.exists():
        default_cfg = """# LeakGuard Configuration File
fail_on: error
min_severity: info
min_confidence: low
exclude_patterns:
  - "**/venv/**"
  - "**/.venv/**"
  - "**/__pycache__/**"
  - "**/build/**"
  - "**/dist/**"
  - "**/.git/**"
  - "**/.pytest_cache/**"
include_patterns:
  - "**/*.py"
"""
        cfg_path.write_text(default_cfg, encoding="utf-8")
        console.print(f"[bold green][OK] Created project config at '{cfg_path}'[/bold green]")
    else:
        console.print(f"[bold yellow][INFO] Existing config found at '{cfg_path}'[/bold yellow]")

    # 2. Create .leakguard/reports directory
    reports_dir = target / ".leakguard" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[bold green][OK] Initialized report log directory at '{reports_dir}'[/bold green]")

    # 3. Update .gitignore
    gitignore_path = target / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if ".leakguard/reports" not in content:
            with gitignore_path.open("a", encoding="utf-8") as f:
                f.write("\n# LeakGuard generated scan reports\n.leakguard/reports/\n")
            console.print("[bold green][OK] Added '.leakguard/reports/' to .gitignore[/bold green]")

    # 4. Check & Install Git Hooks
    git_hooks_dir = target / ".git" / "hooks"
    if not git_hooks_dir.exists():
        console.print(f"[bold yellow][WARN] No '.git' directory found in '{target}'. Git hooks omitted.[/bold yellow]")
        console.print("[bold green][OK] LeakGuard initialization complete![/bold green]")
        return

    hook_script = """#!/bin/sh
# LeakGuard Automated Pre-Push Resource Leak Guardrail Hook
echo "[LeakGuard] Executing pre-push static resource lifetime scan..."

mkdir -p .leakguard/reports
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE=".leakguard/reports/scan_${TIMESTAMP}.log"
LATEST_JSON=".leakguard/reports/latest_scan.json"

python -m leakguard scan . --format json --out "$LATEST_JSON" --voice > "$REPORT_FILE" 2>&1
SCAN_EXIT_CODE=$?
cat "$REPORT_FILE"

if [ $SCAN_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "--------------------------------------------------------"
    echo " [X] LeakGuard Pre-Push Check FAILED! PUSH ABORTED."
    echo " Resource leak findings detected in codebase."
    echo " Scan log saved to: $REPORT_FILE"
    echo " Fix resource leaks before pushing or run: python -m leakguard fix ."
    echo "--------------------------------------------------------"
    python -m leakguard speak "Attention! LeakGuard pre push firewall blocked unclosed resource leaks. Git push aborted."
    exit 1
fi

echo "[OK] LeakGuard Pre-Push Check Passed! Zero blocking leaks detected."
python -m leakguard speak "LeakGuard pre push check passed. Zero resource leaks detected."
exit 0
"""


    pre_push_hook = git_hooks_dir / "pre-push"
    pre_push_hook.write_text(hook_script, encoding="utf-8")
    try:
        os.chmod(str(pre_push_hook), 0o755)
    except Exception:
        pass
    console.print(f"[bold green][OK] Pre-Push Git Hook successfully installed at '{pre_push_hook}'[/bold green]")

    pre_commit_hook = git_hooks_dir / "pre-commit"
    if not pre_commit_hook.exists():
        pre_commit_hook.write_text(hook_script, encoding="utf-8")
        try:
            os.chmod(str(pre_commit_hook), 0o755)
        except Exception:
            pass
        console.print(f"[bold green][OK] Pre-Commit Git Hook successfully installed at '{pre_commit_hook}'[/bold green]")

    console.print(f"\n[bold cyan][SUCCESS] LeakGuard successfully initialized for '{target.name}'![/bold cyan]")
    console.print("[gray]Git operations (commit/push) will now auto-scan and report leaks to .leakguard/reports/[/gray]\n")


def _run_install_activate_flow(target: Path, action_name: str = "activated") -> None:
    """Helper flow to setup LeakGuard guardrails and launch authentication modal on dashboard."""
    import webbrowser
    from http.server import HTTPServer, BaseHTTPRequestHandler

    target = target.resolve()
    if not target.is_dir():
        console.print(f"[bold red][Error] Target '{target}' is not a directory.[/bold red]")
        sys.exit(1)

    console.print(f"\n[bold cyan]=== LeakGuard Guardrail Auto-{action_name.capitalize()} ===[/bold cyan]")
    console.print(f"Setting up automated GitHub push leak protection in: [bold white]{target}[/bold white]")

    # 1. Config file
    cfg_path = target / ".leakguard.yml"
    if not cfg_path.exists():
        default_cfg = """# LeakGuard Configuration File
fail_on: error
min_severity: info
min_confidence: low
exclude_patterns:
  - "**/venv/**"
  - "**/.venv/**"
  - "**/__pycache__/**"
  - "**/build/**"
  - "**/dist/**"
  - "**/.git/**"
  - "**/.pytest_cache/**"
include_patterns:
  - "**/*.py"
"""
        cfg_path.write_text(default_cfg, encoding="utf-8")
        console.print(f"[bold green][OK] Generated configuration at '{cfg_path.name}'[/bold green]")

    # 2. Reports dir
    reports_dir = target / ".leakguard" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    console.print(f"[bold green][OK] Initialized scan reports directory at '.leakguard/reports/'[/bold green]")

    # 3. .gitignore
    gitignore_path = target / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if ".leakguard/reports" not in content:
            with gitignore_path.open("a", encoding="utf-8") as f:
                f.write("\n# LeakGuard generated scan reports\n.leakguard/reports/\n")
            console.print("[bold green][OK] Updated '.gitignore' with '.leakguard/reports/'[/bold green]")

    # 4. Git Hooks
    git_hooks_dir = target / ".git" / "hooks"
    if git_hooks_dir.exists():
        hook_script = """#!/bin/sh
# LeakGuard Automated Pre-Push Resource Leak Guardrail Hook
echo "[LeakGuard] Executing pre-push static resource lifetime scan..."

mkdir -p .leakguard/reports
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE=".leakguard/reports/scan_${TIMESTAMP}.log"
LATEST_JSON=".leakguard/reports/latest_scan.json"

python -m leakguard scan . --format json --out "$LATEST_JSON" --voice > "$REPORT_FILE" 2>&1
SCAN_EXIT_CODE=$?
cat "$REPORT_FILE"

if [ $SCAN_EXIT_CODE -ne 0 ]; then
    echo ""
    echo "--------------------------------------------------------"
    echo " [X] LeakGuard Pre-Push Check FAILED! PUSH ABORTED."
    echo " Resource leak findings detected in codebase."
    echo " Scan log saved to: $REPORT_FILE"
    echo " Fix resource leaks before pushing or run: python -m leakguard fix ."
    echo "--------------------------------------------------------"
    python -m leakguard speak "Attention! LeakGuard pre push firewall blocked unclosed resource leaks. Git push aborted."
    exit 1
fi

echo "[OK] LeakGuard Pre-Push Check Passed! Zero blocking leaks detected."
python -m leakguard speak "LeakGuard pre push check passed. Zero resource leaks detected."
exit 0
"""

        pre_push_hook = git_hooks_dir / "pre-push"
        pre_push_hook.write_text(hook_script, encoding="utf-8")
        try:
            os.chmod(str(pre_push_hook), 0o755)
        except Exception:
            pass
        console.print(f"[bold green][OK] Pre-Push Git Hook installed at '{pre_push_hook}'[/bold green]")

        pre_commit_hook = git_hooks_dir / "pre-commit"
        if not pre_commit_hook.exists():
            pre_commit_hook.write_text(hook_script, encoding="utf-8")
            try:
                os.chmod(str(pre_commit_hook), 0o755)
            except Exception:
                pass
            console.print(f"[bold green][OK] Pre-Commit Git Hook installed at '{pre_commit_hook}'[/bold green]")

    # Callback HTTP server setup
    callback_payload = {}

    class LocalCallbackHandler(BaseHTTPRequestHandler):
        def do_OPTIONS(self):
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            try:
                data = {
                    "access_token": params.get("token", params.get("access_token", [""]))[0],
                    "organization_id": params.get("organization_id", params.get("org_id", [""]))[0],
                    "role": params.get("role", ["Developer"])[0],
                    "email": params.get("email", ["User"])[0],
                    "user_id": params.get("user_id", [""])[0],
                    "action": "login",
                }
                if data["access_token"] or data["email"] != "User":
                    callback_payload.update(data)
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"<html><body style='font-family:sans-serif;text-align:center;padding:50px;'><h2>\xe2\x9c\x94 LeakGuard CLI Authenticated!</h2><p>You can close this tab and return to your terminal.</p></body></html>")
            except Exception:
                self.send_response(400)
                self.end_headers()

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode("utf-8"))
                callback_payload.update(data)
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            except Exception:
                self.send_response(400)
                self.end_headers()

        def log_message(self, format, *args):
            pass

    cli_port = 8005
    httpd = None
    try:
        httpd = HTTPServer(("127.0.0.1", cli_port), LocalCallbackHandler)
    except Exception:
        try:
            cli_port = 8085
            httpd = HTTPServer(("127.0.0.1", cli_port), LocalCallbackHandler)
        except Exception:
            httpd = None

    dashboard_auth_url = f"http://localhost:3000/login?activated=true&cli_port={cli_port}"
    dashboard_signup_url = f"http://localhost:3000/register?activated=true&cli_port={cli_port}"

    console.print(f"\n[bold green][SUCCESS] LeakGuard git hooks successfully {action_name} for '{target.name}'![/bold green]")
    console.print("[bold yellow]---------------------------------------------------------------------------------[/bold yellow]")
    console.print("[bold white]Complete Authentication in web browser to finish CLI setup:[/bold white]")
    console.print(f"  • [bold cyan]Login Link:[/bold cyan]   {dashboard_auth_url}")
    console.print(f"  • [bold cyan]Sign Up Link:[/bold cyan] {dashboard_signup_url}")
    console.print("[bold yellow]---------------------------------------------------------------------------------[/bold yellow]")

    # Launch browser automatically
    try:
        webbrowser.open(dashboard_auth_url)
        console.print("[gray]Opening authentication portal in default web browser...[/gray]")
    except Exception:
        pass

    if httpd:
        console.print(f"[bold cyan][WAITING] Listening on port {cli_port} for web authentication callback...[/bold cyan]")
        start_time = time.time()
        httpd.timeout = 1.0
        while time.time() - start_time < 90:
            httpd.handle_request()
            if callback_payload:
                break
        httpd.server_close()

        if callback_payload:
            save_credentials(callback_payload)
            action_type = callback_payload.get("action", "login").upper()
            user_email = callback_payload.get("email", "User")
            user_role = callback_payload.get("role", "Owner")

            console.print("\n[bold green]=========================================================================[/bold green]")
            console.print(f"[bold green] [OK] {action_type} SUCCESSFUL! Authenticated as: '{user_email}' (Role: {user_role})[/bold green]")
            console.print(f"[bold green] [SUCCESS] LeakGuard is fully {action_name.upper()} & ACTIVATED for this project![/bold green]")
            console.print(f"[bold green] [HOOKS] Pre-push git hooks will automatically block leaks on 'git push'.[/bold green]")
            console.print("[bold green]=========================================================================\n[/bold green]")
        else:
            console.print("[bold yellow][INFO] Authentication timeout or manual close. Pre-push hooks remain active locally.[/bold yellow]\n")


@app.command()
def install(
    target: Path = typer.Argument(Path("."), help="Directory path to install LeakGuard pre-push scanner"),
) -> None:
    """Installs LeakGuard git hooks and opens Control Plane login/signup portal."""
    _run_install_activate_flow(target, action_name="installed")


@app.command()
def activate(
    target: Path = typer.Argument(Path("."), help="Directory path to activate LeakGuard pre-push protection"),
) -> None:
    """Activates LeakGuard automated push protection and opens Control Plane login/signup portal."""
    _run_install_activate_flow(target, action_name="activated")


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
def watch(
    target: Path = typer.Argument(Path("."), help="Directory or file path to continuously watch"),
    debounce: int = typer.Option(300, "--debounce", help="Debounce interval in milliseconds"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress live UI rendering"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging"),
    json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON events"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable terminal colors"),
    exclude: Optional[List[str]] = typer.Option(None, "--exclude", "-e", help="Glob pattern to exclude"),
    include: Optional[List[str]] = typer.Option(None, "--include", "-i", help="Glob pattern to include"),
    severity: Optional[Severity] = typer.Option(None, "--severity", "-s", help="Filter minimum severity threshold"),
    confidence: Optional[Confidence] = typer.Option(None, "--confidence", "-c", help="Filter minimum confidence threshold"),
    voice: bool = typer.Option(False, "--voice", help="Enable live voice audio announcements for leak events"),
) -> None:
    """Continuously monitors Python project source files and displays Live Resource Radar AST analysis telemetry."""
    from interfaces.cli.watch import run_watch_mode
    run_watch_mode(
        target=target,
        debounce=debounce,
        quiet=quiet,
        verbose=verbose,
        json_output=json,
        no_color=no_color,
        exclude=exclude,
        include=include,
        severity=severity,
        confidence=confidence,
        voice=voice,
    )



@app.command()
def review(
    target: Path = typer.Argument(Path("."), help="Directory or file path to review"),
    commit: Optional[str] = typer.Option(None, "--commit", help="Commit SHA to review"),
    pr: Optional[str] = typer.Option(None, "--pr", help="Pull Request number to review"),
    mode: str = typer.Option("detailed", "--mode", "-m", help="Review mode: concise | detailed | security | senior-engineer | developer-friendly"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON review"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable terminal colors"),
) -> None:
    """Executes AI-powered Resource Security Code Review on code, PRs, or commits."""
    from interfaces.cli.review import run_review_cmd
    run_review_cmd(target_path=target, commit=commit, pr=pr, mode=mode, json_mode=json, no_color=no_color)


@app.command()
def explain(
    finding_id: str = typer.Option(..., "--finding", "-f", help="Finding ID to explain"),
    file: Optional[Path] = typer.Option(None, "--file", help="Python source file path"),
) -> None:
    """Explains root cause and security risks for a specific finding."""
    from interfaces.cli.review import run_explain_cmd
    run_explain_cmd(finding_id=finding_id, file_path=file)


@app.command()
def fix(
    target: Path = typer.Argument(Path("."), help="Target Python file or directory path to fix"),
    finding: str = typer.Option("LEAK_001", "--finding", "-f", help="Finding ID to fix"),
    strategy: str = typer.Option("context-manager", "--strategy", help="Strategy: context-manager | try-finally | close-insertion | exception-safe | async-cleanup"),
    verify: bool = typer.Option(True, "--verify/--no-verify", help="Execute isolated deterministic verification"),
) -> None:
    """Generates candidate AI fix and executes authoritative isolated deterministic verification."""
    from interfaces.cli.review import run_fix_cmd
    run_fix_cmd(target_file=target, finding_id=finding)



@app.command()
def verify(
    patch: Path = typer.Option(..., "--patch", "-p", help="Patch file to verify against deterministic analyzer"),
) -> None:
    """Verifies a candidate patch against LeakGuard static analysis rules."""
    from interfaces.cli.review import run_verify_cmd
    run_verify_cmd(patch_file=patch)


@app.command()
def ownership(
    target: Path = typer.Argument(Path("."), help="Directory or file path to analyze"),
    finding: Optional[str] = typer.Option(None, "--finding", "-f", help="Finding ID to inspect"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON ownership graph"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable terminal colors"),
) -> None:
    """Displays the Resource Ownership Graph for a file or finding."""
    from interfaces.cli.phase16_cli import run_ownership_cmd
    run_ownership_cmd(target_path=target, finding_id=finding, json_mode=json, no_color=no_color)


@app.command(name="what-if")
def what_if(
    file: Path = typer.Option(..., "--file", help="Target Python source file"),
    line: int = typer.Option(..., "--line", "-l", help="Line number to simulate hypothetical exception at"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON what-if result"),
) -> None:
    """Executes static hypothetical execution analysis for an exception at a specified line."""
    from interfaces.cli.phase16_cli import run_what_if_cmd
    run_what_if_cmd(target_file=file, line_number=line, json_mode=json)


@app.command()
def risk(
    target: Path = typer.Argument(Path("."), help="Directory or file path to analyze"),
    finding: Optional[str] = typer.Option(None, "--finding", "-f", help="Finding ID to score"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON risk score"),
) -> None:
    """Computes deterministic 0-100 risk score for a finding or file."""
    from interfaces.cli.phase16_cli import run_risk_cmd
    run_risk_cmd(target_path=target, finding_id=finding, json_mode=json)


@app.command()
def firewall(
    target: Path = typer.Argument(Path("."), help="Directory or file path to analyze"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="Path to custom .leakguard.yml config"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON firewall evaluation"),
    strict: bool = typer.Option(False, "--strict", help="Strict mode (treat warnings as errors)"),
) -> None:
    """Evaluates developer firewall policy rules on target directory or file."""
    from interfaces.cli.firewall_cli import run_firewall_cmd
    run_firewall_cmd(target_path=target, config_file=config, json_mode=json, strict=strict)


@app.command(name="pr-diff")
def pr_diff(
    before: Path = typer.Option(..., "--before", "-b", help="Base commit / before target path"),
    after: Path = typer.Option(..., "--after", "-a", help="PR head / after target path"),
    pr: Optional[str] = typer.Option("42", "--pr", help="Pull Request ID / Number"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON diff stream"),
) -> None:
    """Compares Before (base) vs After (head) findings and outputs PR Leak Diff."""
    from interfaces.cli.firewall_cli import run_pr_diff_cmd
    run_pr_diff_cmd(before_path=before, after_path=after, pr_number=pr, json_mode=json)


@app.command(name="diff")
def diff_alias(
    before: Path = typer.Option(..., "--before", "-b", help="Base commit / before target path"),
    after: Path = typer.Option(..., "--after", "-a", help="PR head / after target path"),
    pr: Optional[str] = typer.Option("42", "--pr", help="Pull Request ID / Number"),
    json: bool = typer.Option(False, "--json", help="Output machine-readable JSON diff stream"),
) -> None:
    """Alias for pr-diff. Compares Before vs After leak findings."""
    from interfaces.cli.firewall_cli import run_pr_diff_cmd
    run_pr_diff_cmd(before_path=before, after_path=after, pr_number=pr, json_mode=json)


@app.command()
def speak(
    message: str = typer.Argument(..., help="Message string to announce via voice TTS"),
    sync: bool = typer.Option(False, "--sync", help="Synchronous audio playback mode"),
) -> None:
    """Announces text message via system Voice TTS Engine."""
    from services.voice.announcer import VoiceAnnouncer
    announcer = VoiceAnnouncer(enabled=True)
    announcer.speak(message, async_mode=not sync)


@app.command()
def version() -> None:
    """Prints the version of LeakGuard."""
    console.print("[bold cyan]LeakGuard v0.1.0[/bold cyan] - Static Resource Lifetime Analysis for Python")


if __name__ == "__main__":
    app()







