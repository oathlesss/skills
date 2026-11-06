import socket, struct, json, sys
host, port = sys.argv[1], int(sys.argv[2])

def vint(n):
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out

def read_varint(sock):
    n = shift = 0
    while True:
        b = sock.recv(1)[0]
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            return n
        shift += 7

def read_bytes(sock, n):
    out = b""
    while len(out) < n:
        out += sock.recv(n - len(out))
    return out

def frame(packet):
    return vint(len(packet)) + packet

s = socket.create_connection((host, port), timeout=5)
hs = b"\x00" + vint(777) + vint(len(host)) + host.encode() + struct.pack(">H", port) + b"\x01"
s.sendall(frame(hs))
s.sendall(frame(b"\x00"))

# response: [len varint][pid 0x00][strlen varint][json]  (strlen is a VARINT, not one byte)
length = read_varint(s)
packet = read_bytes(s, length)
body = packet[1:]  # skip packet id 0x00
slen = read_from = shift = 0
while True:
    b = body[read_from]
    read_from += 1
    slen |= (b & 0x7F) << shift
    if not (b & 0x80):
        break
    shift += 7
resp = json.loads(body[read_from:read_from + slen])
print("version:", resp["version"]["name"], "protocol:", resp["version"]["protocol"])
d = resp.get("description")
motd = d.get("text") if isinstance(d, dict) else d
print("motd:", motd)
print("players:", resp["players"]["online"], "/", resp["players"]["max"])
