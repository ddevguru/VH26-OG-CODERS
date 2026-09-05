import sys
import json
from pathlib import Path
from typing import Optional
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
from core.common.models import Diagnostic, Classification, Span, SourceLocation
from core.ownership.graph import ResourceOwnershipGraph
from core.analysis.what_if import WhatIfEngine
from core.analysis.scorer import RiskScorer

console = Console()


def run_ownership_cmd(
    target_path: Path,
    finding_id: Optional[str] = None,
    json_mode: bool = False,
    no_color: bool = False,
) -> None:
    """Displays the Resource Ownership Graph for a file or finding."""
    target_file = target_path.resolve()
    if not target_file.exists():
        console.print(f"[bold red]Error:[/bold red] Path does not exist: {target_file}")
        raise typer.Exit(code=1)

    config = LeakGuardConfig()
    engine = AnalysisEngine(config)

    diagnostics = []
    source_code = ""
    if target_file.is_file():
        diagnostics = engine.analyze_file(target_file)
        source_code = target_file.read_text(encoding="utf-8", errors="replace")
    else:
        scanner = ProjectScanner(config)
        scan_res = scanner.scan_directory(target_file)
        diagnostics = scan_res.diagnostics

    from core.common.models import Span, SourceLocation

    diag = diagnostics[0] if diagnostics else Diagnostic(
        finding_id=finding_id or "LEAK_001",
        rule_id="RULE_LEAK_001",
        message="Resource Lifetime Graph",
        classification=Classification.DEFINITE_LEAK,
        file_path=str(target_file),
        location=Span(start=SourceLocation(line=1, column=1), end=SourceLocation(line=1, column=1)),
        resource_type="RESOURCE",
        resource_variable="conn",
        reason="Resource ownership tracked along CFG",
    )

    graph = ResourceOwnershipGraph.from_diagnostic(diag, source_code=source_code)

    if json_mode:
        print(json.dumps(graph.model_dump()))
        return

    # Render Terminal Graph Summary
    table = Table(title="RESOURCE OWNERSHIP GRAPH", show_header=True, header_style="bold cyan")
    table.add_column("Node ID", style="bold magenta")
    table.add_column("Type", style="cyan")
    table.add_column("Variable", style="bold yellow")
    table.add_column("Owner Scope", style="white")
    table.add_column("State", style="bold")

    for node in graph.nodes:
        st_color = "red" if "LEAK" in node.leak_status else "green"
        table.add_row(
            node.resource_id,
            node.resource_type,
            node.variable,
            node.owner,
            f"[{st_color}]{node.state} ({node.leak_status})[/{st_color}]",
        )

    console.print(table)

    console.print("\n[bold yellow]GRAPH EDGES & RELATIONSHIPS[/bold yellow]")
    for edge in graph.edges:
        console.print(f"  [cyan]{edge.source_id}[/cyan] ──([bold magenta]{edge.relationship.value}[/bold magenta])──> [yellow]{edge.target_id}[/yellow] ({edge.label})")


def run_what_if_cmd(
    target_file: Path,
    line_number: int,
    json_mode: bool = False,
) -> None:
    """Executes static hypothetical exception path analysis at line_number."""
    t_file = target_file.resolve()
    if not t_file.exists() or not t_file.is_file():
        console.print(f"[bold red]Error:[/bold red] File not found: {t_file}")
        raise typer.Exit(code=1)

    source_code = t_file.read_text(encoding="utf-8", errors="replace")
    engine = WhatIfEngine()
    result = engine.analyze_exception_point(source_code=source_code, line_number=line_number, file_path=t_file.name)

    if json_mode:
        print(json.dumps(result.model_dump()))
        return

    text = Text()
    text.append(f"⚡ WHAT-IF HYPOTHETICAL EXCEPTION SIMULATION\n\n", style="bold yellow")
    text.append(f"Source Location: {result.source_location}\n", style="bold white")
    text.append(f"Function:        {result.function_name}()\n", style="bold white")
    text.append(f"Cleanup Status:  ", style="bold white")
    if result.cleanup_status == "GUARANTEED":
        text.append("🟢 GUARANTEED (Context Manager / Try-Finally)\n\n", style="bold green")
    else:
        text.append("🔴 NOT GUARANTEED (Potential Leak on Exception)\n\n", style="bold red")

    text.append(f"Explanation:\n{result.explanation}\n\n", style="cyan")
    text.append(f"Potential Impact:\n{result.potential_impact}\n", style="magenta")

    console.print(Panel(text, title="[bold yellow]What-If Analysis[/bold yellow]", border_style="yellow"))

    if result.hypothetical_path:
        console.print("\n[bold cyan]HYPOTHETICAL EXECUTION PATH[/bold cyan]")
        for step in result.hypothetical_path:
            console.print(f"  Step {step.step_number} (L{step.location_line}): [bold yellow]{step.operation}[/bold yellow] — {step.description}")


def run_risk_cmd(
    target_path: Path,
    finding_id: Optional[str] = None,
    json_mode: bool = False,
) -> None:
    """Computes deterministic 0-100 risk score for a finding or file."""
    t_path = target_path.resolve()
    if not t_path.exists():
        console.print(f"[bold red]Error:[/bold red] Path not found: {t_path}")
        raise typer.Exit(code=1)

    config = LeakGuardConfig()
    engine = AnalysisEngine(config)

    diagnostics = []
    if t_path.is_file():
        diagnostics = engine.analyze_file(t_path)
    else:
        scanner = ProjectScanner(config)
        scan_res = scanner.scan_directory(t_path)
        diagnostics = scan_res.diagnostics

    diag = diagnostics[0] if diagnostics else Diagnostic(
        finding_id=finding_id or "LEAK_001",
        rule_id="RULE_DB_001",
        message="Resource Leak",
        classification=Classification.DEFINITE_LEAK,
        file_path=str(t_path),
        location=Span(start=SourceLocation(line=1, column=1), end=SourceLocation(line=1, column=1)),
        resource_type="DATABASE",
        resource_variable="conn",
        reason="Resource handle unclosed at function exit path.",
    )

    scorer = RiskScorer()
    score = scorer.calculate_score(diag)

    if json_mode:
        print(json.dumps(score.model_dump()))
        return

    score_color = "red" if score.score >= 80 else ("yellow" if score.score >= 60 else "green")

    table = Table(title=f"DETERMINISTIC RISK SCORE: [{score_color}]{score.score}/100 [{score.level.value}][/{score_color}]", show_header=True, header_style="bold cyan")
    table.add_column("Risk Factor", style="bold white")
    table.add_column("Max Weight", style="cyan")
    table.add_column("Score Contribution", style="bold yellow")
    table.add_column("Description", style="white")

    for f in score.factors:
        table.add_row(f.name, f"{f.weight:.0f}%", f"+{f.score_contribution:.1f}", f.description)

    console.print(table)
    console.print(f"\n[bold white]Explanation:[/bold white] {score.explanation}")
