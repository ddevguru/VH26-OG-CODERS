import sqlite3

def get_db_connection():
    conn = sqlite3.connect("db.sqlite")
    # Ownership transferred to caller -> Safe
    return conn
