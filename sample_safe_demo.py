"""Sample Safe Python File with Properly Managed Resources for LeakGuard Demo."""
import sqlite3
import socket
from contextlib import closing


def process_user_data_safely(file_path: str) -> str:
    """SAFE #1: File opened with context manager 'with'"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = f.read()
    print(f"Successfully read {len(data)} bytes")
    return data


def fetch_database_records_safely(db_path: str):
    """SAFE #2: SQLite connection & cursor managed with 'with' and 'closing'"""
    with sqlite3.connect(db_path) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT * FROM users")
            rows = cursor.fetchall()
            return rows


def send_network_log_safely(host: str, port: int, message: str):
    """SAFE #3: Network socket properly managed using 'with'"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(message.encode("utf-8"))
