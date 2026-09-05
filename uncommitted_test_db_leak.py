"""TEST FILE 2 — Unclosed SQLite Database & Cursor Leak
Test CLI scan: python -m leakguard scan uncommitted_test_db_leak.py --voice
Test CLI fix:  python -m leakguard fix uncommitted_test_db_leak.py
"""
import sqlite3

def fetch_admin_users(db_path: str):
    # Unclosed database connection 'db_conn' and cursor 'db_cursor'
    with sqlite3.connect(db_path) as db_conn:
        with db_conn.cursor() as db_cursor:
            db_cursor.execute("SELECT id, username FROM users WHERE is_admin = 1")
            admins = db_cursor.fetchall()
            return admins
