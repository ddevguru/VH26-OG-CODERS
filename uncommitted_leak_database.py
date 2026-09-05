"""UNCOMMITTED TEST FILE 2 — Unclosed Database Connection & Cursor Leak
For live terminal testing: python -m leakguard scan uncommitted_leak_database.py --voice
"""
import sqlite3

def load_user_permissions(db_file: str, user_id: int):
    # Unclosed database connection 'conn'
    with sqlite3.connect(db_file) as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT role FROM user_roles WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row[0] if row else "GUEST"
