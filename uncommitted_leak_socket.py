"""UNCOMMITTED TEST FILE 3 — Unclosed Socket Handle Resource Leak
For live terminal testing: python -m leakguard scan uncommitted_leak_socket.py --voice
"""
import socket

def send_heartbeat_ping(host: str, port: int):
    # Unclosed network socket 'sock'
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((host, port))
        sock.sendall(b"PING")
        response = sock.recv(1024)
        return response == b"PONG"
