"""
LeakGuard Sample Repo — CRITICAL / LARGE / CORRECT (#2)
-----------------------------------------------------------------
A different shape of "looks dangerous but isn't" than the previous
correct file. This one specifically targets patterns the PS calls
out as hard: resources passed across function boundaries, resources
stored on an object, and a dynamic (variable-count) set of resources
managed together. All of it is done correctly here using
contextlib.ExitStack and a generator-based acquire/release pattern.

Nothing in this file should be flagged.
"""

import sqlite3
import os
from contextlib import ExitStack, contextmanager


class ConnectionHandle:
    """
    Thin wrapper around a sqlite3 connection so it can be handed to
    other functions while still being managed centrally. This is the
    "resource stored in an object" pattern the PS flags as a known
    hard case — done correctly via ExitStack ownership below.
    """

    def __init__(self, conn):
        self.conn = conn
        self.closed = False

    def close(self):
        if not self.closed:
            self.conn.close()
            self.closed = True


def open_shard_connection(db_path):
    """
    Opens a single shard's DB connection and wraps it. Ownership is
    handed to the caller, who is responsible for closing it — this
    function itself never leaks because it never holds the resource
    past its own return; there is no code path here that opens and
    then fails to hand off the handle.
    """
    conn = sqlite3.connect(db_path)
    return ConnectionHandle(conn)


def export_all_shards(shard_paths, out_dir):
    """
    CLEAN (critical) — opens a variable, runtime-determined number of
    DB connections (one per shard) plus one output file per shard,
    using ExitStack so every single one of them is guaranteed to
    close when the function exits, regardless of how many shards
    there are or whether a later shard raises partway through.

    This is the correct answer to the reassignment/loop-leak shape
    seen in earlier LEAK examples: instead of reusing one variable
    name across iterations (which loses references), every handle
    gets pushed onto the stack immediately after it's created, so
    ExitStack — not a manually tracked variable — owns closing it.
    """
    exported = []
    with ExitStack() as stack:
        for shard_path in shard_paths:
            handle = open_shard_connection(shard_path)
            stack.callback(handle.close)   # registered immediately, before any risk of exception

            out_path = os.path.join(
                out_dir, os.path.basename(shard_path) + ".export.csv"
            )
            out_file = stack.enter_context(open(out_path, "w"))

            cursor = handle.conn.cursor()
            cursor.execute("SELECT id, value FROM records")
            for row_id, value in cursor.fetchall():
                out_file.write(f"{row_id},{value}\n")

            if value_is_suspicious(value):
                # Even though we raise mid-loop, every handle and file
                # opened so far (including this iteration's) is still
                # closed correctly because ExitStack unwinds on exit,
                # not just on normal completion.
                raise ValueError(f"Suspicious value in shard {shard_path}: {value}")

            exported.append(shard_path)
    return exported


def value_is_suspicious(value):
    """Placeholder validation used by export_all_shards above."""
    return isinstance(value, (int, float)) and value < 0


@contextmanager
def temporary_staging_table(conn, table_name):
    """
    CLEAN (critical) — a generator-based context manager. The
    resource here is a SQL side-effect (a temp table) rather than a
    file handle, but the same reachability rules apply: the `finally`
    inside a generator-based contextmanager runs on every exit from
    the `with` block, including via exception, exactly like a
    class-based __exit__ would.
    """
    conn.execute(f"CREATE TEMP TABLE {table_name} (id INTEGER, payload TEXT)")
    try:
        yield table_name
    finally:
        conn.execute(f"DROP TABLE IF EXISTS {table_name}")


def stage_and_process(db_path, rows):
    """
    CLEAN (critical) — uses two nested correctly-scoped resources:
    the outer sqlite3 connection (closed via `with`, which sqlite3's
    connection object supports as a transaction context manager and
    is additionally closed explicitly since the `with` form only
    commits/rolls back, it does not close the connection itself —
    a common real-world gotcha this function handles correctly) and
    the inner temp table from temporary_staging_table above.
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
        conn.close()   # reached on every path: success, sqlite3.Error, or any other exception