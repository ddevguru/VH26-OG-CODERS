import time
import threading
from pathlib import Path
from typing import Callable, List, Set, Dict, Optional
from core.watch.events import FileEvent, FileEventType
from core.common.logger import get_logger

logger = get_logger("leakguard.debouncer")


class EventDebouncer:
    """Thread-safe debouncer that coalesces rapid file change events within a window (in milliseconds)."""

    def __init__(self, delay_ms: float = 300.0, callback: Optional[Callable[[List[FileEvent]], None]] = None) -> None:
        self.delay_seconds = max(0.01, delay_ms / 1000.0)
        self.callback = callback
        self._lock = threading.Lock()
        self._pending_events: Dict[Path, FileEvent] = {}
        self._timer: Optional[threading.Timer] = None
        self._is_stopped = False

    def push_event(self, event: FileEvent) -> None:
        with self._lock:
            if self._is_stopped:
                return

            # Cancel existing timer
            if self._timer is not None:
                self._timer.cancel()

            # Store / update latest event for this file path
            self._pending_events[event.path] = event

            # Reset timer
            self._timer = threading.Timer(self.delay_seconds, self._flush)
            self._timer.daemon = True
            self._timer.start()

    def _flush(self) -> None:
        events_to_emit: List[FileEvent] = []
        with self._lock:
            if not self._pending_events or self._is_stopped:
                return
            events_to_emit = list(self._pending_events.values())
            self._pending_events.clear()
            self._timer = None

        if self.callback and events_to_emit:
            try:
                self.callback(events_to_emit)
            except Exception as e:
                logger.error(f"Error in debouncer callback: {e}", exc_info=True)

    def stop(self) -> None:
        with self._lock:
            self._is_stopped = True
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
            self._pending_events.clear()
