"""Sample Python File with Resource Leaks for LeakGuard PR Review Demo."""
import sqlite3
import socket


def process_user_data(file_path: str):
    """LEAK #1: Unclosed File Handle"""
    f = open(file_path, "r")
    data = f.read()
    print(f"Read {len(data)} bytes")
    # Missing f.close() -> LeakGuard detects DEFINITE_LEAK


def fetch_database_records(db_path: str):
    """LEAK #2: Unclosed SQLite Database Connection"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    return rows
    # Missing conn.close() -> LeakGuard detects DEFINITE_LEAK


def send_network_log(host: str, port: int, message: str):
    """LEAK #3: Unclosed Network Socket"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(message.encode("utf-8"))
    # Missing s.close() -> LeakGuard detects DEFINITE_LEAK
