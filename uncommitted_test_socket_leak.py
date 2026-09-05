"""TEST FILE 3 — Unclosed Network Socket Handle Leak
Test CLI scan: python -m leakguard scan uncommitted_test_socket_leak.py --voice
Test CLI fix:  python -m leakguard fix uncommitted_test_socket_leak.py
"""
import socket

def send_telemetry_payload(remote_host: str, remote_port: int, payload: bytes):
    # Unclosed socket connection 'client_sock'
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_sock:
        client_sock.connect((remote_host, remote_port))
        client_sock.sendall(payload)
        ack = client_sock.recv(512)
        return ack == b"OK"
