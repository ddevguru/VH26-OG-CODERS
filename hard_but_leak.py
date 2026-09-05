"""
LeakGuard Sample Repo — CRITICAL / LARGE / WRONG (#2)
-----------------------------------------------------------------
Structural twin of test_critical_large_correct_2.py — same classes,
same use of ExitStack and a generator-based @contextmanager, same
"resource stored on an object" and "resource crosses a function
boundary" shapes. Every resource in this file has a close() call
somewhere in its containing scope. The bug is in exactly ONE place:
a handle is registered with ExitStack AFTER a line that can raise,
instead of immediately after it's created — so on that specific
exception, the stack never learns about the resource and can't
close it during unwind.
"""

import sqlite3
import os
from contextlib import ExitStack, contextmanager


class ConnectionHandle:
    """Identical to the correct version — this class was never the bug."""

    def __init__(self, conn):
        self.conn = conn
        self.closed = False

    def close(self):
        if not self.closed:
            self.conn.close()
            self.closed = True


def open_shard_connection(db_path):
    """Identical to the correct version — never the bug."""
    conn = sqlite3.connect(db_path)
    return ConnectionHandle(conn)


def validate_shard_path(shard_path):
    """
    A pre-flight check run on each shard path before its connection
    is registered for cleanup. Looks like an innocuous validation
    helper — but its placement in the loop below is what creates the
    leak.
    """
    if not shard_path.endswith(".db"):
        raise ValueError(f"Unexpected shard file extension: {shard_path}")


def export_all_shards(shard_paths, out_dir):
    """
    *** SEEDED LEAK ***
    Opens a variable, runtime-determined number of DB connections,
    same as the correct version. The difference: `validate_shard_path`
    is called AFTER the connection handle is opened but BEFORE it is
    registered with the ExitStack via `stack.callback(handle.close)`.

    If validation fails for a given shard, the ValueError propagates
    immediately. Because the callback registration line never ran for
    THIS shard's handle, ExitStack has no record of it and cannot
    close it during unwind — even though every other handle opened in
    earlier loop iterations (already registered) closes correctly.

    This is the exact bug class the correct twin of this file avoids
    by registering the callback immediately upon creation, before any
    other statement that could raise. A tool that just checks "is
    stack.callback(handle.close) present anywhere in this function"
    would say yes and mark this clean — it IS present, just ordered
    wrong relative to a line that can throw.
    """
    exported = []
    with ExitStack() as stack:
        for shard_path in shard_paths:
            handle = open_shard_connection(shard_path)

            validate_shard_path(shard_path)   # BUG: can raise before the next line runs
            stack.callback(handle.close)      # never reached for the failing shard's handle

            out_path = os.path.join(
                out_dir, os.path.basename(shard_path) + ".export.csv"
            )
            out_file = stack.enter_context(open(out_path, "w"))

            cursor = handle.conn.cursor()
            cursor.execute("SELECT id, value FROM records")
            for row_id, value in cursor.fetchall():
                out_file.write(f"{row_id},{value}\n")

            exported.append(shard_path)
    return exported


@contextmanager
def temporary_staging_table(conn, table_name):
    """Identical to the correct version — never the bug."""
    conn.execute(f"CREATE TEMP TABLE {table_name} (id INTEGER, payload TEXT)")
    try:
        yield table_name
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")


def stage_and_process(db_path, rows):
    """
    Identical shape to the correct version, including the sqlite3
    `with conn:` gotcha being handled properly here too — this
    function is CLEAN. It's included to prove the leak above is
    isolated to `export_all_shards` and not a repo-wide pattern,
    so your tool needs to distinguish function-by-function rather
    than flagging (or clearing) the whole file at once.
    """
    conn = sqlite3.connect(db_path)
    try:
        with temporary_staging_table(conn, "stage_import") as table_name:
            for row_id, payload in rows:
                conn.execute(
                    f"INSERT INTO {table_name} (id, payload) VALUES (?, ?)",
                    (row_id, payload),
                )
            conn.execute(
                f"INSERT INTO records (id, value) SELECT id, LENGTH(payload) FROM {table_name}"
            )
        conn.commit()
        return True
    except sqlite3.Error:
        conn.rollback()
        return False
    finally:
        conn.close()