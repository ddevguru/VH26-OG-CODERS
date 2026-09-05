"""UNCLOSED SOCKET LEAK — High Severity Resource Leak (LG-NET-001)
Network socket stream 's' created without close() or release call.
"""
import socket

def send_network_ping(host: str, port: int):
    # High Leak: 's' network socket handle is left unclosed
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall(b"PING")
    data = s.recv(1024)
    return data
