"""TEST FILE 5 — Multi-Resource Leaks in Single Function
Test CLI scan: python -m leakguard scan uncommitted_test_multi_resource.py --voice
Test CLI fix:  python -m leakguard fix uncommitted_test_multi_resource.py
"""
import sqlite3

def export_logs_to_database(log_file_path: str, target_db_path: str):
    # Unclosed file handle 'log_file'
    with open(log_file_path, "r") as log_file:
        log_lines = log_file.readlines()
    
        # Unclosed database handle 'db_conn'
        db_conn = sqlite3.connect(target_db_path)
        db_cursor = db_conn.cursor()
        for line in log_lines:
            db_cursor.execute("INSERT INTO logs (entry) VALUES (?)", (line.strip(),))
    
        return len(log_lines)
