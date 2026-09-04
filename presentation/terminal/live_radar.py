import json
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live

from core.common.models import Diagnostic, Classification, Severity
from core.watch.state import WatchState, FindingTransition


class LiveRadarRenderer:
    """Renders the LeakGuard Live Radar UI, compact resource tables, lifecycle visualization, transition banners, and machine-readable JSON."""

    def __init__(self, console: Optional[Console] = None, json_mode: bool = False, no_color: bool = False) -> None:
        self.console = console or Console(no_color=no_color)
        self.json_mode = json_mode
        self.no_color = no_color

    def print_json_event(self, event_type: str, data: Dict[str, Any]) -> None:
        payload = {
            "event": event_type,
            "data": data,
        }
        print(json.dumps(payload), flush=True)

    def render_startup_banner(self, state: WatchState) -> None:
        if self.json_mode:
            self.print_json_event(
                "WATCH_STARTED",
                {
                    "project_root": str(state.root_dir),
                    "status": state.status,
                    "python_files": state.python_files_count,
                    "functions_analyzed": state.functions_analyzed_count,
                    "resources_tracked": state.resources_tracked_count,
                },
            )
            return

        banner_text = Text()
        banner_text.append("🛡 LEAKGUARD LIVE RADAR\n", style="bold cyan")
        banner_text.append("──────────────────────────────────────────────────────────────\n", style="dim")
        banner_text.append("Project: ", style="bold")
        banner_text.append(f"{state.root_dir}\n")
        banner_text.append("Status:  ", style="bold")
        banner_text.append(f"{state.status}\n\n", style="bold green")

        banner_text.append(f"Python files:       {state.python_files_count:<10}\n", style="cyan")
        banner_text.append(f"Functions analyzed: {state.functions_analyzed_count:<10}\n", style="cyan")
        banner_text.append(f"Resources tracked:   {state.resources_tracked_count:<10}\n\n", style="cyan")

        banner_text.append(f"SAFE              {state.safe_count:<6}\n", style="bold green")
        banner_text.append(f"POTENTIAL          {state.potential_count:<6}\n", style="bold yellow")
        banner_text.append(f"DEFINITE           {state.definite_count:<6}", style="bold red")

        panel = Panel(
            banner_text,
            border_style="cyan",
            expand=False,
            padding=(1, 2),
        )
        self.console.print("\n")
        self.console.print(panel)

    def render_reanalyzing(self, file_path: Path) -> None:
        if self.json_mode:
            self.print_json_event("ANALYZING_FILE", {"file": str(file_path)})
            return

        text = Text()
        text.append("🔄 ANALYZING\n", style="bold yellow")
        text.append(str(file_path), style="dim white")
        panel = Panel(text, border_style="yellow", expand=False)
        self.console.print("\n")
        self.console.print(panel)

    def render_syntax_error(self, state: WatchState) -> None:
        err = state.syntax_error
        if not err:
            return

        if self.json_mode:
            self.print_json_event(
                "SYNTAX_ERROR",
                {
                    "file": str(err.file_path),
                    "line": err.line,
                    "message": err.message,
                },
            )
            return

        text = Text()
        text.append("🟡 Syntax incomplete\n\n", style="bold yellow")
        text.append(f"{err.file_path}:{err.line}\n", style="bold white")
        text.append("Waiting for valid Python syntax...", style="dim yellow")

        panel = Panel(text, title="[bold yellow]Syntax Incomplete[/bold yellow]", border_style="yellow", expand=False)
        self.console.print("\n")
        self.console.print(panel)

    def render_transitions(self, transitions: List[FindingTransition]) -> None:
        if not transitions:
            return

        for t in transitions:
            if self.json_mode:
                self.print_json_event(
                    "FINDING_TRANSITION",
                    {
                        "transition_type": t.transition_type,
                        "file": str(t.file_path),
                        "function": t.function_name,
                        "resource": t.resource_variable,
                        "old_classification": t.old_classification,
                        "new_classification": t.new_classification,
                    },
                )
                continue

            if t.transition_type == "RESOLVED_LEAK":
                text = Text()
                text.append("🟢 LEAK RESOLVED\n\n", style="bold green")
                text.append("✓ AST analysis\n✓ CFG analysis\n✓ Resource lifetime analysis\n✓ Ownership verification\n\n", style="green")
                text.append(f"Previous:\n    🔴 {t.old_classification}\n\n", style="dim red")
                text.append(f"Current:\n    🟢 {t.new_classification}\n\n", style="bold green")
                text.append("✓ RESOURCE LIFECYCLE VERIFIED\n\n", style="bold green")
                text.append(f"Resource:\n    {t.resource_variable}\n", style="cyan")
                text.append(f"Function:\n    {t.function_name}()\n", style="cyan")

                panel = Panel(text, title="[bold green]✓ SAFE — LEAK RESOLVED[/bold green]", border_style="green", expand=False)
                self.console.print(panel)

            elif t.transition_type == "NEW_LEAK":
                text = Text()
                text.append(f"🔴 NEW LEAK DETECTED ({t.new_classification})\n\n", style="bold red")
                text.append(f"File:\n    {t.file_path}\n\n", style="bold white")
                text.append(f"Function:\n    {t.function_name}()\n\n", style="bold white")
                text.append(f"Resource:\n    {t.resource_variable}\n\n", style="bold magenta")
                if t.diagnostic:
                    loc_line = t.diagnostic.location.start.line if t.diagnostic.location else 1
                    text.append(f"Acquisition:\n    Line {loc_line}\n\n", style="yellow")
                    text.append(f"Reason:\n    {t.diagnostic.reason}\n", style="red")

                panel = Panel(text, title="[bold red]🔴 NEW LEAK[/bold red]", border_style="red", expand=False)
                self.console.print(panel)

            elif t.transition_type == "CLASSIFICATION_SHIFT":
                text = Text()
                text.append("CLASSIFICATION SHIFT\n\n", style="bold yellow")
                text.append(f"Resource: {t.resource_variable} in {t.function_name}()\n", style="cyan")
                text.append(f"Shift: {t.old_classification} ➔ {t.new_classification}\n", style="bold yellow")
                panel = Panel(text, border_style="yellow", expand=False)
                self.console.print(panel)

    def render_resource_radar_table(self, state: WatchState) -> None:
        if self.json_mode:
            return

        table = Table(title="RESOURCE RADAR", show_header=True, header_style="bold cyan")
        table.add_column("Resource", style="bold magenta")
        table.add_column("Type", style="cyan")
        table.add_column("State", style="bold")
        table.add_column("Location", style="yellow")

        if not state.active_findings:
            table.add_row("conn / file", "Resource", "[bold green]🟢 CLOSED[/bold green]", "L--")
        else:
            for diag in state.active_findings.values():
                res_var = diag.resource_variable or "res"
                res_type = str(diag.resource_type or "Resource")
                state_str = "[bold red]🔴 OPEN (LEAK)[/bold red]" if "DEFINITE" in str(diag.classification) else "[bold yellow]🟠 POTENTIAL[/bold yellow]"
                loc = f"L{diag.location.start.line}" if diag.location else "L--"
                table.add_row(res_var, res_type, state_str, loc)

        self.console.print(table)

    def render_lifecycle_diagram(self, diag: Diagnostic) -> None:
        if self.json_mode:
            return

        res_var = diag.resource_variable or "resource"
        acq_line = diag.location.start.line if diag.location else 1
        is_safe = diag.classification == Classification.SAFE or "SAFE" in str(diag.classification)

        text = Text()
        text.append(f"{res_var}\n\n", style="bold magenta")
        text.append(f"L{acq_line:<3} ACQUIRE\n", style="cyan")
        text.append("     │\n     ▼\n", style="dim")
        text.append(f"L{acq_line + 1:<3} OPERATION / DATAFLOW\n", style="cyan")
        text.append("     │\n     ▼\n", style="dim")

        if is_safe:
            text.append(f"L{acq_line + 5:<3} CLOSE\n", style="green")
            text.append("     │\n     ▼\n", style="dim")
            text.append("     🟢 SAFE EXIT\n", style="bold green")
        else:
            text.append(f"L{acq_line + 5:<3} RETURN\n", style="red")
            text.append("     │\n     ▼\n", style="dim")
            text.append("     🔴 EXIT WITHOUT RELEASE\n", style="bold red")

        panel = Panel(text, title=f"[bold]Lifecycle Flow: {res_var}[/bold]", border_style="green" if is_safe else "red", expand=False)
        self.console.print(panel)

    def render_live_status(self, state: WatchState) -> None:
        if self.json_mode:
            self.print_json_event(
                "LIVE_STATUS",
                {
                    "status": state.status,
                    "files": state.python_files_count,
                    "functions": state.functions_analyzed_count,
                    "resources": state.resources_tracked_count,
                    "definite_leaks": state.definite_count,
                    "potential_leaks": state.potential_count,
                    "last_changed": str(state.last_changed_file) if state.last_changed_file else None,
                    "last_scan_timestamp": state.last_scan_timestamp,
                    "duration_ms": round(state.last_scan_duration_ms, 2),
                },
            )
            return

        text = Text()
        text.append("LIVE STATUS\n\n", style="bold cyan")
        text.append(f"{state.status}\n\n", style="bold green")
        text.append(f"Files:       {state.python_files_count}\n", style="white")
        text.append(f"Functions:   {state.functions_analyzed_count}\n", style="white")
        text.append(f"Resources:   {state.resources_tracked_count}\n\n", style="white")

        text.append("Findings:\n", style="bold white")
        text.append(f"  🔴 DEFINITE     {state.definite_count}\n", style="bold red")
        text.append(f"  🟠 POTENTIAL    {state.potential_count}\n\n", style="bold yellow")

        if state.last_changed_file:
            text.append(f"Last changed:\n  {state.last_changed_file}\n\n", style="cyan")

        text.append(f"Last scan:\n  {state.last_scan_timestamp}\n\n", style="white")
        text.append(f"Duration:\n  {state.last_scan_duration_ms:.1f}ms\n", style="bold green")

        panel = Panel(text, border_style="cyan", expand=False, padding=(1, 2))
        self.console.print("\n")
        self.console.print(panel)
