"""100% Safe Python Service — All resources properly managed using context managers."""
import sqlite3
import socket
from contextlib import closing


def read_config_file(config_path: str) -> str:
    """SAFE: File opened with 'with' block — guaranteed closed on all paths."""
    with open(config_path, "r", encoding="utf-8") as f:
        return f.read()


def query_active_users(db_path: str):
    """SAFE: SQLite connection and cursor managed with 'with' & 'closing'."""
    with sqlite3.connect(db_path) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute("SELECT id, username FROM users WHERE is_active = 1")
            return cursor.fetchall()


def send_telemetry_event(host: str, port: int, payload: bytes):
    """SAFE: Network socket managed with 'with' block."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))
        client_socket.sendall(payload)
