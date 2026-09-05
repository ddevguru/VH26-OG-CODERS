"""UNCLOSED FILE LEAK — Definite Resource Leak (LG-FILE-001)
File handle 'f' opened without close() or context manager across execution path.
"""

def parse_log_file(filename: str):
    # Definite Leak: 'f' is opened but never closed at scope exit
    f = open(filename, "r")
    content = f.read()
    if "ERROR" in content:
        return True
    return False
