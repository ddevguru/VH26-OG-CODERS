import socket

def connect_server(flag):
    s = socket.socket()

    if flag:
        s.close()
    else:
        # Leaked on else branch!
        print("Processing without closing socket")
