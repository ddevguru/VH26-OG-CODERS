"""
LeakGuard Sample Repo — CRITICAL / LARGE / CORRECT
-----------------------------------------------------------------
This is the structural twin of test_critical_large_wrong.py. Same
classes, same responsibilities, same shape of control flow (custom
context manager, long-lived DB connection, per-file loop with a
narrow except clause, a "space-check-then-write" archive helper).

The ONLY difference from the wrong version is that `_archive_original`
below correctly wraps the space-check-and-open sequence so the
handle is closed on every exit path, including the disk-space
failure path. Every other resource here behaves the same as the
wrong version — this file should be reported 100% clean.
"""

import sqlite3
import socket
import os
import tempfile


class RemoteLogger:
    """Identical to the wrong version — this class was never the bug."""

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(3)
        self.sock.connect((self.host, self.port))
        return self

    def log(self, message):
        if self.sock is not None:
            self.sock.send((message + "\n").encode())

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.sock is not None:
            self.sock.close()
            self.sock = None
        return False


class BatchFileProcessor:
    """
    Same responsibilities as the wrong version: owns a DB connection
    and a remote logging socket for a batch run, processes each file,
    writes a report, and archives the original.
    """

    def __init__(self, db_path, log_host, log_port, archive_dir):
        self.db_path = db_path
        self.log_host = log_host
        self.log_port = log_port
        self.archive_dir = archive_dir
        self.conn = None

    def run(self, file_paths):
        """CLEAN — conn.close() is in a finally, reached on every path."""
        self.conn = sqlite3.connect(self.db_path)
        results = []
        try:
            with RemoteLogger(self.log_host, self.log_port) as logger:
                for path in file_paths:
                    try:
                        status = self._process_one(path, logger)
                        results.append((path, status))
                    except FileNotFoundError:
                        logger.log(f"SKIP missing file: {path}")
                        results.append((path, "missing"))
        finally:
            self.conn.close()
        return results

    def _process_one(self, path, logger):
        if not os.path.exists(path):
            raise FileNotFoundError(path)

        report_path = self._write_report(path)
        self._archive_original(path)
        logger.log(f"OK processed: {path} -> {report_path}")
        return "ok"

    def _write_report(self, path):
        """CLEAN — unchanged from the wrong version; was never buggy."""
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".report", delete=False
        )
        try:
            with open(path, "r") as src:
                content = src.read()

            if len(content) == 0:
                raise ValueError(f"Empty file, cannot report: {path}")

            tmp.write(f"REPORT for {path}\n")
            tmp.write(f"length={len(content)}\n")
            return tmp.name
        finally:
            tmp.close()

    def _archive_original(self, path):
        """
        CLEAN (critical) — this is the fixed twin of the seeded leak.
        The space check now happens BEFORE the archive file is
        opened, so there is no window where a handle exists but is
        unreachable on the failure path. Once `archive_handle` is
        opened, it's wrapped in try/finally so it closes on every
        exit — success, exception during write, anything.
        """
        archive_path = os.path.join(
            self.archive_dir, os.path.basename(path) + ".bak"
        )

        free_space = os.statvfs(self.archive_dir).f_bavail if hasattr(os, "statvfs") else 1_000_000
        if free_space < 1:
            # No resource has been opened yet on this path — safe to raise.
            raise OSError(f"Not enough disk space to archive {path}")

        archive_handle = open(archive_path, "wb")
        try:
            with open(path, "rb") as src:
                archive_handle.write(src.read())
        finally:
            archive_handle.close()   # reached on every path once opened, including write errors
