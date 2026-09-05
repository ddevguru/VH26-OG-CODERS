"""Sample 100% Safe Python File for LeakGuard Demo."""
import sqlite3
import socket


def process_file_safely(file_path: str) -> str:
    """SAFE #1: File opened with context manager 'with'"""
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def connect_db_safely(db_path: str):
    """SAFE #2: SQLite connection managed with 'with'"""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        return cursor.fetchall()


def send_socket_safely(host: str, port: int, data: bytes):
    """SAFE #3: Socket managed with 'with'"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(data)
