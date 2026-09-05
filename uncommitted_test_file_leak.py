"""TEST FILE 1 — Unclosed File Handle Leak
Test CLI scan: python -m leakguard scan uncommitted_test_file_leak.py --voice
Test CLI fix:  python -m leakguard fix uncommitted_test_file_leak.py
"""

def parse_server_log(log_path: str, keyword: str):
    # Unclosed file handle 'f_handle'
    with open(log_path, "r", encoding="utf-8") as f_handle:
        matches = [line for line in f_handle if keyword in line]
        if len(matches) > 50:
            return matches[:50]
        return matches
