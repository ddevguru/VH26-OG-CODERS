"""SAFE TEST FILE — Zero Resource Leaks
Uses Python standard context managers ('with' statements) for guaranteed automatic resource release.
"""
import sqlite3

def read_config_safe(filepath: str) -> str:
    # Safe: wrapped in context manager
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def fetch_user_safe(db_path: str):
    # Safe: DB connection wrapped in context manager
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()
