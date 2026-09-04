from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from core.common.models import Diagnostic, Classification, Severity, Confidence, ScanStatistics, ScanResult


class TerminalFormatter:
    """Formats diagnostic findings into visual terminal tables, statistics panels, and execution traces using Rich."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()

    def print_scan_result(self, result: ScanResult, quiet: bool = False, verbose: bool = False) -> None:
        if not quiet:
            self.print_diagnostics(result.diagnostics)
            self.print_statistics(result.statistics, baseline_suppressed=result.baseline_suppressed_count)

    def print_diagnostics(self, diagnostics: List[Diagnostic]) -> None:
        if not diagnostics:
            self.console.print("\n[bold green][OK] No resource leaks detected.[/bold green]\n")
            return

        table = Table(title="LeakGuard Resource Lifetime Scan Results", show_lines=True)
        table.add_column("Finding ID", style="cyan", no_wrap=True)
        table.add_column("Classification", style="bold")
        table.add_column("Resource", style="magenta")
        table.add_column("Location", style="yellow")
        table.add_column("Reason / Explanation")

        for diag in diagnostics:
            class_color = "red" if diag.classification == Classification.DEFINITE_LEAK else "yellow"
            class_text = f"[{class_color}]{diag.classification.value}[/{class_color}]"

            loc_str = f"{diag.file_path}:{diag.location.start.line}:{diag.location.start.column}"
            res_str = f"{diag.resource_variable or 'res'} ({diag.resource_type})"

            table.add_row(
                diag.finding_id,
                class_text,
                res_str,
                loc_str,
                diag.reason,
            )

        self.console.print("\n")
        self.console.print(table)
        self.console.print(f"\n[bold red]Total Resource Leak Findings: {len(diagnostics)}[/bold red]\n")

    def print_statistics(self, stats: ScanStatistics, baseline_suppressed: int = 0) -> None:
        stats_text = (
            f"[bold cyan]Files Scanned:[/bold cyan] {stats.files_scanned}  |  "
            f"[bold cyan]Files Skipped:[/bold cyan] {stats.files_skipped}\n"
            f"[bold cyan]Functions Analyzed:[/bold cyan] {stats.functions_analyzed}  |  "
            f"[bold cyan]Resources Analyzed:[/bold cyan] {stats.resources_analyzed}\n"
            f"[bold cyan]Findings Found:[/bold cyan] {stats.findings_count}"
        )
        if baseline_suppressed > 0:
            stats_text += f"  (Baseline Suppressed: {baseline_suppressed})"
        stats_text += (
            f"\n[bold cyan]Scan Duration:[/bold cyan] {stats.duration_seconds}s  |  "
            f"[bold cyan]Throughput:[/bold cyan] {stats.throughput_files_per_sec} files/sec"
        )

        panel = Panel(
            Text.from_markup(stats_text),
            title="[bold green]Scan Performance Statistics[/bold green]",
            border_style="green",
            expand=False,
        )
        self.console.print(panel)

    def print_path_trace(self, diagnostic: Diagnostic) -> None:
        if not diagnostic.execution_path:
            return

        self.console.print(f"[bold cyan]Execution Path Trace for {diagnostic.finding_id}:[/bold cyan]")
        for step in diagnostic.execution_path:
            loc = step.location
            self.console.print(f"  [yellow]Step {step.step_number}[/yellow] ({loc.start.line}:{loc.start.column}) -> {step.description}")
        self.console.print("\n")

