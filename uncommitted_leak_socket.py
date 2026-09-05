"""UNCOMMITTED TEST FILE 3 — Unclosed Network Socket Stream Leak
For live terminal testing: python -m leakguard scan uncommitted_leak_socket.py --voice
"""
import socket

def send_telemetry_packet(server_host: str, port: int, payload: bytes):
    # Unclosed socket handle 'sock'
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((server_host, port))
    sock.sendall(payload)
    response = sock.recv(512)
    return response
