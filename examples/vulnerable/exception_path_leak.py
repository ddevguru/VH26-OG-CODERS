import sqlite3

def fetch_data(query):
    conn = sqlite3.connect("db.sqlite")

    # May raise Exception
    cursor = conn.cursor()
    cursor.execute(query)

    # Skipped if exception occurs!
    conn.close()
