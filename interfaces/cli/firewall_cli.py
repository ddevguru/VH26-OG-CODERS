import sys
import json
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from core.analysis.engine import AnalysisEngine
from services.scan.scanner import ProjectScanner
from core.common.config import LeakGuardConfig
from core.common.models import Diagnostic, Classification
from services.firewall.engine import FirewallEngine, FirewallResult
from services.diff.engine import PRDiffEngine, PRDiffResult

console = Console()


def run_firewall_cmd(
    target_path: Path,
    config_file: Optional[Path] = None,
    json_mode: bool = False,
    strict: bool = False,
) -> None:
    """Evaluates developer firewall policy rules on target directory or file."""
    t_path = target_path.resolve()
    if not t_path.exists():
        console.print(f"[bold red]Error:[/bold red] Path does not exist: {t_path}")
        raise typer.Exit(code=1)

    config = LeakGuardConfig()
    engine = AnalysisEngine(config)

    diagnostics: List[Diagnostic] = []
    if t_path.is_file():
        diagnostics = engine.analyze_file(t_path)
    else:
        scanner = ProjectScanner(config)
        scan_res = scanner.scan_directory(t_path)
        diagnostics = scan_res.diagnostics

    firewall = FirewallEngine(config_file or t_path / ".leakguard.yml" if (t_path / ".leakguard.yml").exists() else None)
    res = firewall.evaluate(diagnostics)

    if json_mode:
        print(json.dumps(res.model_dump()))
        if not res.passed:
            raise typer.Exit(code=1)
        return

    # Render Firewall Pipeline Header
    pipeline_text = Text()
    pipeline_text.append("Developer", style="bold cyan")
    pipeline_text.append("   ↓   \n", style="dim white")
    pipeline_text.append("Commit / PR", style="bold cyan")
    pipeline_text.append("   ↓   \n", style="dim white")
    pipeline_text.append("LeakGuard Firewall", style="bold magenta")
    pipeline_text.append("   ↓   \n", style="dim white")
    pipeline_text.append("Policy Engine", style="bold yellow")
    pipeline_text.append("   ↓   \n", style="dim white")

    if res.passed:
        pipeline_text.append("🟢 PASS", style="bold green")
    else:
        pipeline_text.append("🔴 BLOCK", style="bold red")

    console.print(Panel(pipeline_text, title="[bold magenta]🧱 LEAKGUARD FIREWALL PIPELINE[/bold magenta]", border_style="magenta", expand=False))

    # Findings Breakdown
    if res.blocked_findings:
        b_table = Table(title=f"🔴 BLOCKED LEAKS ({len(res.blocked_findings)})", show_header=True, header_style="bold red")
        b_table.add_column("Rule ID", style="bold yellow")
        b_table.add_column("File Location", style="white")
        b_table.add_column("Resource", style="cyan")
        b_table.add_column("Action", style="bold red")

        for d in res.blocked_findings:
            loc_str = f"{d.file_path}:{d.location.start.line}" if d.location else d.file_path
            b_table.add_row(d.rule_id, loc_str, f"{d.resource_type} ({d.resource_variable})", "BLOCK")

        console.print(b_table)

    if res.warned_findings:
        w_table = Table(title=f"🟡 WARNED LEAKS ({len(res.warned_findings)})", show_header=True, header_style="bold yellow")
        w_table.add_column("Rule ID", style="bold yellow")
        w_table.add_column("File Location", style="white")
        w_table.add_column("Resource", style="cyan")
        w_table.add_column("Action", style="bold yellow")

        for d in res.warned_findings:
            loc_str = f"{d.file_path}:{d.location.start.line}" if d.location else d.file_path
            w_table.add_row(d.rule_id, loc_str, f"{d.resource_type} ({d.resource_variable})", "WARN")

        console.print(w_table)

    console.print()
    if res.passed:
        console.print(f"[bold green]✔ Leak Firewall Policy Enforced: ALL CHECKS PASSED.[/bold green]")
        raise typer.Exit(code=0)
    else:
        console.print(f"[bold red]✖ Leak Firewall Policy Enforced: COMMIT BLOCKED ({len(res.blocked_findings)} blocking leaks found).[/bold red]")
        raise typer.Exit(code=1)


def run_pr_diff_cmd(
    before_path: Path,
    after_path: Path,
    pr_number: Optional[str] = "42",
    json_mode: bool = False,
) -> None:
    """Compares Before (base) vs After (head) findings and outputs PR Leak Diff."""
    b_path = before_path if before_path.exists() else Path(".")
    a_path = after_path if after_path.exists() else Path(".")

    config = LeakGuardConfig()
    engine = AnalysisEngine(config)

    def scan(p: Path, changed_only: bool = False) -> List[Diagnostic]:
        cfg = LeakGuardConfig(changed_only=changed_only)
        if p.is_file():
            return engine.analyze_file(p)
        scanner = ProjectScanner(cfg)
        return scanner.scan_directory(p).diagnostics

    # If git ref passed, scan base directory vs changed files
    is_git_ref = (not before_path.exists() or not after_path.exists())
    before_diags = scan(b_path, changed_only=False) if not is_git_ref else []
    after_diags = scan(a_path, changed_only=is_git_ref)

    diff_engine = PRDiffEngine()
    result = diff_engine.compare(before=before_diags, after=after_diags, pr_number=pr_number)

    if json_mode:
        print(json.dumps(result.model_dump()))
        return

    # Render Visual PR Diff Layout matching requested specification
    pr_str = f"PR #{result.pr_number}" if result.pr_number else "PR Leak Diff Comparison"
    
    diff_text = Text()
    diff_text.append(f"🔀 {pr_str}\n\n", style="bold yellow")
    diff_text.append(f"Before     After\n", style="bold white")
    diff_text.append(f"{result.before_count:<10} ", style="bold white")
    diff_text.append(f"{result.after_count} 🔴\n\n", style="bold red")

    diff_text.append(f"Resolved:  {result.resolved_count}\n", style="bold green")
    diff_text.append(f"New:       {result.new_count}\n", style="bold red" if result.new_count > 0 else "bold white")
    diff_text.append(f"Potential: {result.potential_delta:+d}\n\n", style="bold cyan")

    diff_text.append(f"Status:\n", style="bold white")
    diff_text.append(f"🟢 {result.resolved_count} leaks fixed\n", style="bold green")
    diff_text.append(f"🔴 {result.new_count} new leaks\n", style="bold red" if result.new_count > 0 else "bold white")

    console.print(Panel(diff_text, title="[bold yellow]🔀 PR LEAK DIFF COMPARISON[/bold yellow]", border_style="yellow", expand=False))
