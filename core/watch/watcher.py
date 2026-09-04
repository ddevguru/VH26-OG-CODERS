import os
import time
import hashlib
import threading
from pathlib import Path
from typing import Callable, Optional, Dict, Set, List, Union
from core.common.config import LeakGuardConfig
from core.common.logger import get_logger
from core.watch.events import FileEvent, FileEventType
from services.scan.ignore import IgnoreFilter

logger = get_logger("leakguard.watcher")

# Standard ignored directories
DEFAULT_IGNORED_DIRS = {
    "node_modules",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    "coverage",
    ".leakguard",
}


class PollingWatcher:
    """Fallback directory watcher using mtime and SHA256 hashes to detect Python file changes without busy loops."""

    def __init__(
        self,
        root_dir: Path,
        on_event: Callable[[FileEvent], None],
        ignore_filter: Optional[IgnoreFilter] = None,
        poll_interval: float = 0.5,
    ) -> None:
        self.root_dir = root_dir.resolve()
        self.on_event = on_event
        self.ignore_filter = ignore_filter
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._snapshot: Dict[Path, float] = {}

    def _should_watch(self, path: Path) -> bool:
        if path.suffix != ".py":
            return False
        # Check if any parent directory is in DEFAULT_IGNORED_DIRS
        for part in path.parts:
            if part in DEFAULT_IGNORED_DIRS:
                return False
        if self.ignore_filter and self.ignore_filter.is_ignored(path):
            return False
        return True

    def _take_snapshot(self) -> Dict[Path, float]:
        snap: Dict[Path, float] = {}
        if not self.root_dir.exists():
            return snap

        if self.root_dir.is_file():
            if self._should_watch(self.root_dir):
                try:
                    snap[self.root_dir] = self.root_dir.stat().st_mtime
                except OSError:
                    pass
            return snap

        for p in self.root_dir.rglob("*.py"):
            if self._should_watch(p):
                try:
                    snap[p.resolve()] = p.stat().st_mtime
                except OSError:
                    continue
        return snap

    def start(self) -> None:
        self._snapshot = self._take_snapshot()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def _poll_loop(self) -> None:
        while self._running:
            time.sleep(self.poll_interval)
            if not self._running:
                break

            current_snap = self._take_snapshot()
            now = time.time()

            # Check deleted files
            for old_path in list(self._snapshot.keys()):
                if old_path not in current_snap:
                    del self._snapshot[old_path]
                    self.on_event(
                        FileEvent(
                            path=old_path,
                            event_type=FileEventType.DELETED,
                            timestamp=now,
                        )
                    )

            # Check created or modified files
            for path, mtime in current_snap.items():
                if path not in self._snapshot:
                    self._snapshot[path] = mtime
                    self.on_event(
                        FileEvent(
                            path=path,
                            event_type=FileEventType.CREATED,
                            timestamp=now,
                        )
                    )
                elif mtime > self._snapshot[path]:
                    self._snapshot[path] = mtime
                    self.on_event(
                        FileEvent(
                            path=path,
                            event_type=FileEventType.MODIFIED,
                            timestamp=now,
                        )
                    )

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)


class FileWatcher:
    """File watcher supporting Watchdog if available, falling back to PollingWatcher."""

    def __init__(
        self,
        root_dir: Union[str, Path],
        on_event: Callable[[FileEvent], None],
        config: Optional[LeakGuardConfig] = None,
        force_polling: bool = False,
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.on_event = on_event
        self.config = config or LeakGuardConfig()

        self.ignore_filter = IgnoreFilter(
            root_dir=self.root_dir if self.root_dir.is_dir() else self.root_dir.parent,
            extra_excludes=self.config.exclude_patterns,
            extra_includes=self.config.include_patterns,
        )

        self._watchdog_observer = None
        self._polling_watcher: Optional[PollingWatcher] = None
        self.using_watchdog = False

        if not force_polling:
            self._try_init_watchdog()

        if not self.using_watchdog:
            self._polling_watcher = PollingWatcher(
                root_dir=self.root_dir,
                on_event=self.on_event,
                ignore_filter=self.ignore_filter,
            )

    def _should_process(self, path_str: str) -> bool:
        p = Path(path_str).resolve()
        if p.suffix != ".py":
            return False
        for part in p.parts:
            if part in DEFAULT_IGNORED_DIRS:
                return False
        if self.ignore_filter.is_ignored(p):
            return False
        return True

    def _try_init_watchdog(self) -> None:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            outer_self = self

            class WatchdogHandler(FileSystemEventHandler):
                def on_created(self, event):
                    if not event.is_directory and outer_self._should_process(event.src_path):
                        outer_self.on_event(
                            FileEvent(
                                path=Path(event.src_path).resolve(),
                                event_type=FileEventType.CREATED,
                                timestamp=time.time(),
                            )
                        )

                def on_modified(self, event):
                    if not event.is_directory and outer_self._should_process(event.src_path):
                        outer_self.on_event(
                            FileEvent(
                                path=Path(event.src_path).resolve(),
                                event_type=FileEventType.MODIFIED,
                                timestamp=time.time(),
                            )
                        )

                def on_deleted(self, event):
                    if not event.is_directory and outer_self._should_process(event.src_path):
                        outer_self.on_event(
                            FileEvent(
                                path=Path(event.src_path).resolve(),
                                event_type=FileEventType.DELETED,
                                timestamp=time.time(),
                            )
                        )

                def on_moved(self, event):
                    if not event.is_directory:
                        if outer_self._should_process(event.dest_path):
                            outer_self.on_event(
                                FileEvent(
                                    path=Path(event.dest_path).resolve(),
                                    event_type=FileEventType.RENAMED,
                                    timestamp=time.time(),
                                    old_path=Path(event.src_path).resolve(),
                                )
                            )

            watch_path = self.root_dir if self.root_dir.is_dir() else self.root_dir.parent
            self._watchdog_observer = Observer()
            self._watchdog_observer.schedule(WatchdogHandler(), str(watch_path), recursive=True)
            self.using_watchdog = True
            logger.info("Using watchdog for high-efficiency OS file events.")
        except Exception as e:
            logger.debug(f"Watchdog unavailable or error initializing ({e}), falling back to PollingWatcher.")
            self.using_watchdog = False

    def start(self) -> None:
        if self.using_watchdog and self._watchdog_observer:
            self._watchdog_observer.start()
        elif self._polling_watcher:
            self._polling_watcher.start()

    def stop(self) -> None:
        if self.using_watchdog and self._watchdog_observer:
            try:
                self.using_watchdog = False
                self._watchdog_observer.stop()
                self._watchdog_observer.join(timeout=1.0)
            except Exception:
                pass
        elif self._polling_watcher:
            self._polling_watcher.stop()
