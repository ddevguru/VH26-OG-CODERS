import sqlite3

def fetch_data(query):
    conn = sqlite3.connect("db.sqlite")
    cursor = conn.cursor()
    cursor.execute(query)
    conn.close()

