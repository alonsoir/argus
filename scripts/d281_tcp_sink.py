# Receptor TCP que descarta lo recibido. Uso: python3 d281_tcp_sink.py 192.168.100.1 9000
import socket, sys
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((sys.argv[1], int(sys.argv[2])))
s.listen(4)
while True:
    c, a = s.accept()
    n = 0
    while True:
        d = c.recv(65536)
        if not d:
            break
        n += len(d)
    c.close()
    print(f"{a} -> {n} bytes", flush=True)
