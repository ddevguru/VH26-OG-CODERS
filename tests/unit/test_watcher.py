import time
import tempfile
from pathlib import Path
import pytest

from core.common.models import Classification, Diagnostic, SourceLocation, Span
from core.watch.events import FileEvent, FileEventType
from core.watch.debouncer import EventDebouncer
from core.watch.watcher import FileWatcher, PollingWatcher
from core.watch.state import WatchState, get_finding_key
from presentation.terminal.live_radar import LiveRadarRenderer


def test_watch_state_initialization() -> None:
    root = Path(".").resolve()
    state = WatchState(root_dir=root)
    assert state.python_files_count == 0
    assert state.status == "● WATCHING"
    assert state.safe_count == 0


def test_watch_state_syntax_error() -> None:
    root = Path(".").resolve()
    state = WatchState(root_dir=root)
    dummy_file = root / "services" / "database.py"

    state.record_syntax_error(dummy_file, line=4, message="invalid syntax")
    assert state.syntax_error is not None
    assert state.syntax_error.line == 4
    assert "syntax" in state.syntax_error.message

    state.clear_syntax_error()
    assert state.syntax_error is None


def test_watch_state_finding_transitions() -> None:
    root = Path(".").resolve()
    state = WatchState(root_dir=root)

    file_a = root / "database.py"
    span = Span(start=SourceLocation(line=10, column=1), end=SourceLocation(line=10, column=10))

    diag_leak = Diagnostic(
        finding_id="LEAK-001",
        rule_id="FILE-001",
        message="Unclosed resource handle",
        resource_type="FILE",
        classification=Classification.DEFINITE_LEAK,
        file_path=str(file_a),
        location=span,
        function_name="fetch_users",
        resource_variable="conn",
        reason="Unclosed resource handle",
    )

    # 1. New leak detected
    transitions1 = state.update_scan_results(
        target_file=file_a,
        diagnostics=[diag_leak],
        total_files=10,
        total_functions=25,
        total_resources=5,
        duration_ms=45.0,
    )

    assert len(transitions1) == 1
    assert transitions1[0].transition_type == "NEW_LEAK"
    assert state.definite_count == 1

    # 2. Leak resolved (re-analyze with 0 diagnostics)
    transitions2 = state.update_scan_results(
        target_file=file_a,
        diagnostics=[],
        total_files=10,
        total_functions=25,
        total_resources=5,
        duration_ms=20.0,
    )

    assert len(transitions2) == 1
    assert transitions2[0].transition_type == "RESOLVED_LEAK"
    assert state.definite_count == 0


def test_event_debouncer_coalescing() -> None:
    received_events = []

    def on_debounced(events):
        received_events.extend(events)

    debouncer = EventDebouncer(delay_ms=50.0, callback=on_debounced)
    test_path = Path("/tmp/test.py")

    for _ in range(5):
        debouncer.push_event(
            FileEvent(
                path=test_path,
                event_type=FileEventType.MODIFIED,
                timestamp=time.time(),
            )
        )

    # Sleep slightly more than delay to allow debounce timer to flush
    time.sleep(0.12)
    debouncer.stop()

    assert len(received_events) == 1
    assert received_events[0].path == test_path


def test_polling_watcher_ignores_non_python_and_hidden_dirs(tmp_path: Path) -> None:
    events = []

    def on_event(ev: FileEvent) -> None:
        events.append(ev)

    watcher = PollingWatcher(root_dir=tmp_path, on_event=on_event, poll_interval=0.05)

    # Create ignored folder and file
    node_dir = tmp_path / "node_modules"
    node_dir.mkdir()
    (node_dir / "app.py").write_text("print('node_modules')")

    # Create normal python file
    py_file = tmp_path / "main.py"
    py_file.write_text("x = 1")

    # Create non-python file
    txt_file = tmp_path / "readme.txt"
    txt_file.write_text("hello")

    watcher.start()
    time.sleep(0.1)

    # Modify main.py
    py_file.write_text("x = 2")
    time.sleep(0.15)

    watcher.stop()

    # Node modules and txt_file should be ignored, only main.py events present
    event_paths = [e.path for e in events]
    assert py_file.resolve() in event_paths
    assert not any("node_modules" in str(p) for p in event_paths)
    assert not any("readme.txt" in str(p) for p in event_paths)


def test_file_watcher_instantiation(tmp_path: Path) -> None:
    events = []
    watcher = FileWatcher(root_dir=tmp_path, on_event=lambda e: events.append(e), force_polling=True)
    if watcher._polling_watcher:
        watcher._polling_watcher.poll_interval = 0.05
    watcher.start()
    time.sleep(0.1)

    py_file = tmp_path / "service.py"
    py_file.write_text("def test(): pass")
    time.sleep(0.15)

    watcher.stop()
    assert len(events) >= 1
    assert events[0].path.name == "service.py"


def test_live_radar_renderer_json_mode(capsys: pytest.CaptureFixture) -> None:
    root = Path(".").resolve()
    state = WatchState(root_dir=root)
    renderer = LiveRadarRenderer(json_mode=True)

    renderer.render_startup_banner(state)
    captured = capsys.readouterr()
    assert '"event": "WATCH_STARTED"' in captured.out

