"""
TEST CASE 4 - HARD / CRITICAL
Expected result: FLAGGED, but this one is genuinely hard to get right.

Why: it stacks three things the problem statement calls out as known-hard
limitations -
  1. the resource is opened in one function and handed back to the
     caller (ownership escapes the function that opened it)
  2. the caller immediately reassigns it to a new name (conn -> db)
  3. an exception path re-raises without ever reaching close()

If your tool can't fully resolve cross-function ownership, the spec says
to scope that explicitly and document it rather than silently missing it.
This file is meant to show you which of those two outcomes you actually get.
"""

import sqlite3


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    return conn                         # ownership handed to the caller


def run_migration(db_path, statements):
    db = get_connection(db_path)        # reassigned: conn -> db

    try:
        cur = db.cursor()
        for stmt in statements:
            cur.execute(stmt)
        db.commit()
    except sqlite3.OperationalError:
        raise                           # LEAK: propagates without closing db

    db.close()                          # only reached on the success path
