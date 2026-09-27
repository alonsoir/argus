# Subida TCP a caudal fijo. Uso: python3 d281_tcp_upload.py HOST PORT KB_POR_S SEGUNDOS
import socket, sys, time
host, port, kbps, secs = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
chunk = b"x" * 1024
s = socket.create_connection((host, port))
t0 = time.time(); sent = 0
while time.time() - t0 < secs:
    s.sendall(chunk); sent += 1
    d = t0 + sent / kbps - time.time()
    if d > 0:
        time.sleep(d)
s.close()
print(f"sent {sent} KB in {time.time()-t0:.1f}s")
