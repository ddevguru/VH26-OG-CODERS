"""UNCOMMITTED TEST FILE 1 — Unclosed File Resource Leak
For live terminal testing: python -m leakguard scan uncommitted_leak_file.py --voice
"""

def read_custom_log(log_path: str):
    # Unclosed file handle 'file_obj'
    with open(log_path, "r") as file_obj:
        lines = file_obj.readlines()
        if len(lines) > 100:
            return lines[:100]
        return lines
