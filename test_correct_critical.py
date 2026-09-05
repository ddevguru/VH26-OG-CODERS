"""
LeakGuard Sample Repo — CORRECT / CRITICAL (should NOT be flagged)
-----------------------------------------------------------------
True negatives, false-positive trap tier. These are deliberately
written to LOOK dangerous (multiple early returns, an exception
branch, a reassignment, resources passed to a helper) so they test
whether your control-flow analysis is actually precise, rather than
just being lenient because nothing looks obviously wrong.

Each function here is the "correct twin" of a leak pattern from
test_critical_leaks.py — same shape, but every exit path really does
close its resource.
"""

import sqlite3


def fetch_active_user(db_path, user_id):
    """
    CLEAN (critical) — twin of the LEAK-1 pattern (open -> branch ->
    multiple returns -> exception). conn.close() is reachable from
    every single exit point:
      - invalid id  -> closed before return (resource never opened)
      - not found   -> closed before return
      - inactive    -> closed before return
      - db error    -> closed in except before return
      - success     -> closed in finally before return
    """
    if user_id is None or user_id < 0:
        return None  # no resource opened yet on this path — nothing to close

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, email, active FROM users WHERE id = ?", (user_id,)
        )
        row = cursor.fetchone()

        if row is None:
            return None                      # early return #1

        name, email, active = row
        if not active:
            return None                      # early return #2 (different branch)

        return {"name": name, "email": email}  # normal success path

    except sqlite3.Error as e:
        print(f"DB error while fetching user {user_id}: {e}")
        return None                          # exception path

    finally:
        conn.close()                          # reached on EVERY path above


def rotate_log_handle_safe(path_old, path_new):
    """
    CLEAN (critical) — twin of the LEAK-3 reassignment pattern. The
    variable `f` is reassigned to a second resource, but the original
    handle is explicitly closed BEFORE the reassignment happens, so
    no reference is ever lost while still open.
    """
    f = open(path_old, "r")
    contents = f.read()
    f.close()                # closed BEFORE reassignment — original handle safe
    f = open(path_new, "w")
    f.write(contents)
    f.close()                # second handle also closed
    return True


def read_with_retry(path, max_attempts=3):
    """
    CLEAN (critical) — twin of the LEAK-6 partial-exception-handling
    pattern. This one actually handles the retry loop correctly: the
    file handle for a failed attempt is always closed before the next
    attempt opens a new one, and the final successful handle is closed
    via `with` semantics on the last try.
    """
    last_error = None
    for attempt in range(max_attempts):
        f = open(path, "rb")
        try:
            data = f.read()
            f.close()
            return data
        except OSError as e:
            last_error = e
            f.close()        # closed even on the failing attempt
            continue
    raise last_error
