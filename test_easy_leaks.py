"""
LeakGuard Sample Repo — EASY tier
-----------------------------------
These leaks are structurally simple: no branching, no exceptions,
no reassignment. Any AST walker that pairs "resource opened" with
"resource closed in the same function" should catch every LEAK case
below with high confidence, and should NOT flag the CLEAN cases.

Each function is tagged in its docstring as LEAK or CLEAN so you can
script your FP/FN report directly off this file.
"""

import sqlite3
import socket


# ---------------------------------------------------------------------------
# LEAK 1: plain file handle, never closed anywhere in the function
# ---------------------------------------------------------------------------
def read_config(path):
    """LEAK — f is opened and never closed."""
    f = open(path, "r")
    data = f.read()
    lines = data.splitlines()
    settings = {}
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            settings[key.strip()] = value.strip()
    return settings


# ---------------------------------------------------------------------------
# LEAK 2: database connection opened, cursor used, connection never closed
# ---------------------------------------------------------------------------
def fetch_user(db_path, user_id):
    """LEAK — conn.close() is missing entirely."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return {"name": row[0], "email": row[1]} if row else None


# ---------------------------------------------------------------------------
# LEAK 3: raw socket opened, used, never closed
# ---------------------------------------------------------------------------
def ping_host(host, port):
    """LEAK — sock is opened and never closed."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    sock.connect((host, port))
    sock.send(b"PING\n")
    response = sock.recv(1024)
    return response.decode(errors="ignore")


# ---------------------------------------------------------------------------
# LEAK 4: two resources opened in sequence, only the second is closed
# ---------------------------------------------------------------------------
def merge_files(path_a, path_b, out_path):
    """LEAK — file_a is never closed (file_b and out are fine)."""
    file_a = open(path_a, "r")
    file_b = open(path_b, "r")
    out = open(out_path, "w")

    out.write(file_a.read())
    out.write(file_b.read())

    file_b.close()
    out.close()
    # file_a.close() intentionally omitted — this is the seeded leak


# ---------------------------------------------------------------------------
# LEAK 5: file opened for writing inside a simple loop, handle overwritten
# each iteration so only the final one could ever be closed — and isn't
# ---------------------------------------------------------------------------
def dump_records(records, out_dir):
    """LEAK — a new file handle is opened per record and never closed."""
    for i, record in enumerate(records):
        f = open(f"{out_dir}/record_{i}.txt", "w")
        f.write(str(record))
    # no close() call anywhere — every handle in every iteration leaks


# ---------------------------------------------------------------------------
# CLEAN 1: correct use of a context manager — should NOT be flagged
# ---------------------------------------------------------------------------
def read_config_clean(path):
    """CLEAN — uses `with`, resource is guaranteed to close."""
    with open(path, "r") as f:
        data = f.read()
    return data.splitlines()


# ---------------------------------------------------------------------------
# CLEAN 2: explicit close() with no branching — should NOT be flagged
# ---------------------------------------------------------------------------
def fetch_user_clean(db_path, user_id):
    """CLEAN — conn.close() is called before every return."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name, email FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    result = {"name": row[0], "email": row[1]} if row else None
    cursor.close()
    conn.close()
    return result


# ---------------------------------------------------------------------------
# CLEAN 3: multiple resources, all closed, order doesn't matter here
# ---------------------------------------------------------------------------
def merge_files_clean(path_a, path_b, out_path):
    """CLEAN — every opened handle has a matching close()."""
    file_a = open(path_a, "r")
    file_b = open(path_b, "r")
    out = open(out_path, "w")

    out.write(file_a.read())
    out.write(file_b.read())

    file_a.close()
    file_b.close()
    out.close()
