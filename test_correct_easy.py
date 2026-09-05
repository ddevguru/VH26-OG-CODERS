"""
LeakGuard Sample Repo — CORRECT / EASY (should NOT be flagged)
-----------------------------------------------------------------
True negative, base case. Single resource, context manager, no
branching at all. If your tool flags this, something is fundamentally
broken in the base case — this is the simplest possible "definitely
safe" shape there is.
"""


def load_users_from_csv(path):
    """CLEAN (easy) — `with` guarantees close on every path, only one path exists."""
    users = []
    with open(path, "r") as f:
        for line in f:
            name, email = line.strip().split(",")
            users.append({"name": name, "email": email})
    return users


def copy_file_contents(src_path, dst_path):
    """CLEAN (easy) — two resources, both via `with`, no branching."""
    with open(src_path, "r") as src, open(dst_path, "w") as dst:
        dst.write(src.read())
    return True
