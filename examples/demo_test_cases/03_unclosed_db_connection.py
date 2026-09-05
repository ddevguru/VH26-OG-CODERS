"""UNCLOSED DB CONNECTION LEAK — Critical Resource Leak (LG-DB-001)
Database connection 'conn' allocated without close() or try-finally block.
"""
import sqlite3

def query_records(db_name: str):
    # Critical Leak: 'conn' database connection handle is unclosed
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM records")
    results = cursor.fetchall()
    return results
