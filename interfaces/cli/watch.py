import sys
import time
from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console

from core.common.config import LeakGuardConfig
from core.common.models import Severity, Confidence
from core.common.logger import get_logger
from services.scan.scanner import ProjectScanner
from core.analysis.engine import AnalysisEngine
from core.parser.ast_parser import ParserSecurityError
from core.watch.events import FileEvent, FileEventType
from core.watch.debouncer import EventDebouncer
from core.watch.watcher import FileWatcher
from core.watch.state import WatchState
from presentation.terminal.live_radar import LiveRadarRenderer

logger = get_logger("leakguard.cli.watch")


def run_watch_mode(
    target: Path = Path("."),
    debounce: int = 300,
    quiet: bool = False,
    verbose: bool = False,
    json_output: bool = False,
    no_color: bool = False,
    exclude: Optional[List[str]] = None,
    include: Optional[List[str]] = None,
    severity: Optional[Severity] = None,
    confidence: Optional[Confidence] = None,
) -> None:
    """Executes live file watcher and Live Resource Radar UI for interactive static leak detection."""
    target_path = target.resolve()
    if not target_path.exists():
        console = Console(no_color=no_color)
        console.print(f"[bold red]Error: Target path '{target}' does not exist.[/bold red]")
        raise typer.Exit(code=1)

    root_dir = target_path if target_path.is_dir() else target_path.parent

    default_excludes = [
        "**/venv/**",
        "**/.venv/**",
        "**/__pycache__/**",
        "**/build/**",
        "**/dist/**",
        "**/.git/**",
        "**/.pytest_cache/**",
        "**/.next/**",
        "**/node_modules/**",
        "**/.leakguard/**",
    ]
    combined_excludes = default_excludes + (exclude if exclude else [])

    config = LeakGuardConfig(
        min_severity=severity or Severity.INFO,
        min_confidence=confidence or Confidence.LOW,
        exclude_patterns=combined_excludes,
        include_patterns=include or ["**/*.py"],
        quiet=quiet,
        verbose=verbose,
    )

    scanner = ProjectScanner(config)
    engine = AnalysisEngine(config)
    state = WatchState(root_dir=root_dir)
    renderer = LiveRadarRenderer(json_mode=json_output, no_color=no_color)

    # Initial Discovery & Scan
    try:
        discovered_files, _ = scanner.discover_files(root_dir)
        state.python_files_count = len(discovered_files)

        # Execute initial static analysis across project
        initial_scan = scanner.scan_directory(root_dir)
        state.functions_analyzed_count = initial_scan.statistics.functions_analyzed
        state.resources_tracked_count = initial_scan.statistics.resources_analyzed
        state.last_scan_duration_ms = initial_scan.statistics.duration_seconds * 1000.0

        for diag in initial_scan.diagnostics:
            key = f"{Path(diag.file_path).name}::{diag.function_name or 'global'}::{diag.resource_variable or 'res'}::{diag.location.start.line if diag.location else 0}::{diag.rule_id}"
            state.active_findings[key] = diag

        def_cnt = sum(1 for d in initial_scan.diagnostics if "DEFINITE" in str(d.classification))
        pot_cnt = len(initial_scan.diagnostics) - def_cnt
        state.definite_count = def_cnt
        state.potential_count = pot_cnt
        state.safe_count = max(0, state.resources_tracked_count - (def_cnt + pot_cnt))

    except Exception as e:
        logger.error(f"Error during initial watch scan: {e}")

    # Render Startup Banner
    renderer.render_startup_banner(state)

    # Handler for debounced file events
    def handle_debounced_events(events: List[FileEvent]) -> None:
        for ev in events:
            if ev.event_type in (FileEventType.CREATED, FileEventType.MODIFIED, FileEventType.RENAMED):
                if not ev.path.exists() or ev.path.suffix != ".py":
                    continue

                renderer.render_reanalyzing(ev.path)
                start_time = time.time()

                try:
                    diags, funcs, res_cnt, is_skipped = engine.analyze_file_with_stats(ev.path)
                    elapsed_ms = (time.time() - start_time) * 1000.0

                    if is_skipped:
                        continue

                    # Update watch state & compute finding diff transitions
                    discovered, _ = scanner.discover_files(root_dir)
                    transitions = state.update_scan_results(
                        target_file=ev.path,
                        diagnostics=diags,
                        total_files=len(discovered),
                        total_functions=max(state.functions_analyzed_count, funcs),
                        total_resources=max(state.resources_tracked_count, res_cnt),
                        duration_ms=elapsed_ms,
                    )

                    # Render transitions, compact resource table, and lifecycle visualization
                    renderer.render_transitions(transitions)
                    renderer.render_resource_radar_table(state)

                    if diags:
                        for d in diags[:2]:
                            renderer.render_lifecycle_diagram(d)

                    renderer.render_live_status(state)

                except SyntaxError as syn_err:
                    state.record_syntax_error(
                        file_path=ev.path,
                        line=getattr(syn_err, "lineno", 1) or 1,
                        message=str(syn_err),
                    )
                    renderer.render_syntax_error(state)

                except Exception as ex:
                    state.record_syntax_error(
                        file_path=ev.path,
                        line=1,
                        message=f"Analysis paused: {ex}",
                    )
                    renderer.render_syntax_error(state)

            elif ev.event_type == FileEventType.DELETED:
                discovered, _ = scanner.discover_files(root_dir)
                state.update_scan_results(
                    target_file=ev.path,
                    diagnostics=[],
                    total_files=len(discovered),
                    total_functions=state.functions_analyzed_count,
                    total_resources=state.resources_tracked_count,
                    duration_ms=0.0,
                )
                renderer.render_live_status(state)

    # Initialize debouncer & watcher
    debouncer = EventDebouncer(delay_ms=float(debounce), callback=handle_debounced_events)

    def on_watcher_event(ev: FileEvent) -> None:
        debouncer.push_event(ev)

    watcher = FileWatcher(root_dir=root_dir, on_event=on_watcher_event, config=config)
    watcher.start()

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        if not json_output:
            console = Console(no_color=no_color)
            console.print("\n[bold yellow]Shutting down LeakGuard watch mode cleanly...[/bold yellow]")
    finally:
        watcher.stop()
        debouncer.stop()
        if not json_output:
            console = Console(no_color=no_color)
            console.print("[bold green][OK] LeakGuard watch mode exited.[/bold green]\n")
