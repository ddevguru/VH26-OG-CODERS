"""SAFE TEST FILE — Zero Resource Leaks
Uses explicit try-finally block to guarantee resource cleanup.
"""
import sqlite3

def safe_db_op(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        return cursor.fetchone()
    finally:
        # Safe: explicitly closed in finally block
        conn.close()
