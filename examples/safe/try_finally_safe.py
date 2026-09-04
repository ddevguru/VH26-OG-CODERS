import sqlite3

def query_safe():
    conn = None
    try:
        conn = sqlite3.connect("db.sqlite")
    finally:
        if conn:
            conn.close()
