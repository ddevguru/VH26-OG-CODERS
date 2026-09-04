import sqlite3

def fetch_data(query):
    with sqlite3.connect("db.sqlite") as conn:

        # May raise Exception
        with conn.cursor() as cursor:
            cursor.execute(query)

            # Skipped if exception occurs!
