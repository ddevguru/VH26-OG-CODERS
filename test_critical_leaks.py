"""
LeakGuard Sample Repo — CRITICAL tier
----------------------------------------
These leaks are deliberately designed to defeat pattern-matching /
text-search detectors. In every LEAK case below, the string "close()"
or "with" DOES appear somewhere in the function — so a regex-based
tool would likely call these "safe." Only a real AST + control-flow
walker that tracks reachability per path will catch them.

CLEAN cases are included so you can verify your tool doesn't
over-fire on legitimate, slightly-unusual-looking control flow
(the PS explicitly warns: a tool that cries wolf constantly is worse
than no analyzer at all).
"""

import sqlite3
import socket


# ---------------------------------------------------------------------------
# LEAK 1: closed only on the happy path — exception branch returns first
# ---------------------------------------------------------------------------
def process_upload(path, validator):
    """
    LEAK — f.close() textually exists in this function, but the
    exception path (raise -> except -> return None) never reaches it.
    Text search sees "close()" present and would false-negative this.
    """
    f = open(path, "rb")
    try:
        header = f.read(16)
        if not validator(header):
            raise ValueError(f"Invalid file header in {path}")
        payload = f.read()
        f.close()               # only reached if validation passes
        return payload
    except ValueError as e:
        print(f"Upload rejected: {e}")
        return None              # f leaks on every validation failure


# ---------------------------------------------------------------------------
# LEAK 2: early return before the close() line further down
# ---------------------------------------------------------------------------
def get_first_matching_line(path, keyword):
    """
    LEAK — the early `return line` on match skips f.close() entirely.
    close() is present in the function body, just unreachable on the
    common-case path (a match is usually found before EOF).
    """
    f = open(path, "r")
    for line in f:
        if keyword in line:
            return line.strip()    # f never closed on this path
    f.close()
    return None


# ---------------------------------------------------------------------------
# LEAK 3: resource reassigned to a new handle before the old one is closed
# ---------------------------------------------------------------------------
def rotate_log_handle(path_old, path_new):
    """
    LEAK — `f` is reassigned to the new file before the old handle is
    closed, so the reference to the original resource is lost and it
    can never be closed. The function DOES call close() — just on the
    wrong (second) resource.
    """
    f = open(path_old, "r")
    contents = f.read()
    f = open(path_new, "w")     # original handle overwritten here — leaked
    f.write(contents)
    f.close()                   # only closes the *new* handle
    return True


# ---------------------------------------------------------------------------
# LEAK 4: resource passed across a function boundary, callee stores it
# on an object and never closes it — known limitation per the PS, but
# still worth seeding since judges will specifically probe this
# ---------------------------------------------------------------------------
class ConnectionCache:
    def __init__(self):
        self._conns = {}

    def register(self, key, conn):
        # stores the connection reference; nothing in this class ever
        # calls conn.close() for entries added here
        self._conns[key] = conn


def open_and_cache_connection(db_path, cache: ConnectionCache, key):
    """
    LEAK (cross-function / cross-object) — conn is opened here, handed
    to ConnectionCache.register(), and never closed by either function.
    This is the class of leak the PS explicitly says is acceptable to
    scope out IF you document it — seed it here to prove your tool
    either catches it or clearly reports it as a known limitation
    rather than silently missing it.
    """
    conn = sqlite3.connect(db_path)
    cache.register(key, conn)
    return conn


# ---------------------------------------------------------------------------
# LEAK 5: nested try/finally where finally closes the WRONG variable
# ---------------------------------------------------------------------------
def swap_and_process(path_a, path_b):
    """
    LEAK — the finally block closes `b`, but due to the swap above it,
    `b` now refers to what was originally `a`'s handle. The *other*
    original handle is left open. A naive "there's a finally with a
    close() in it" check would mark this safe.
    """
    a = open(path_a, "r")
    b = open(path_b, "r")
    try:
        a, b = b, a              # swap references
        data = a.read()
        return data
    finally:
        b.close()                 # closes only one of the two handles


# ---------------------------------------------------------------------------
# LEAK 6: socket leaked only on a specific exception type not caught
# ---------------------------------------------------------------------------
def send_heartbeat(host, port, payload):
    """
    LEAK — only socket.timeout is handled; if send() raises
    ConnectionResetError (or anything else), the function exits via
    an uncaught exception and sock.close() in the except block is
    never reached, while a superficial reading suggests it's handled.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((host, port))
        sock.send(payload)
    except socket.timeout:
        sock.close()
        return False
    return True                   # sock never closed on the success path either


# ---------------------------------------------------------------------------
# CLEAN 1: try/finally that correctly closes on every path — should NOT flag
# ---------------------------------------------------------------------------
def process_upload_clean(path, validator):
    """CLEAN — finally guarantees close() regardless of exception."""
    f = open(path, "rb")
    try:
        header = f.read(16)
        if not validator(header):
            raise ValueError(f"Invalid file header in {path}")
        return f.read()
    finally:
        f.close()


# ---------------------------------------------------------------------------
# CLEAN 2: early return, but resource closed before every return — should
# NOT be flagged even though it superficially resembles LEAK 2 above
# ---------------------------------------------------------------------------
def get_first_matching_line_clean(path, keyword):
    """CLEAN — close() is called on every exit path via context manager."""
    with open(path, "r") as f:
        for line in f:
            if keyword in line:
                return line.strip()
    return None


# ---------------------------------------------------------------------------
# CLEAN 3: reassignment pattern, but the original handle IS closed first —
# should NOT be flagged despite superficial similarity to LEAK 3
# ---------------------------------------------------------------------------
def rotate_log_handle_clean(path_old, path_new):
    """CLEAN — old handle explicitly closed before reassignment."""
    f = open(path_old, "r")
    contents = f.read()
    f.close()                   # closed BEFORE reassignment
    f = open(path_new, "w")
    f.write(contents)
    f.close()
    return True
