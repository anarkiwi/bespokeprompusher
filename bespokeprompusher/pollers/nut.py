import socket

HOST_DEFAULT = "localhost"
PORT_DEFAULT = 3493
UPS_DEFAULT = "ups"
TIMEOUT_DEFAULT = 10


def _recv_until(sock, terminator):
    buf = b""
    while terminator not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf.decode("utf-8", errors="replace")


def _parse_vars(text, ups):
    prefix = f"VAR {ups} "
    end_line = f"END LIST VAR {ups}"
    results = []
    for line in text.splitlines():
        if line == end_line:
            break
        if not line.startswith(prefix):
            continue
        rest = line[len(prefix) :]
        name, _, raw = rest.partition(" ")
        value = raw.strip().strip('"')
        try:
            num = float(value)
        except ValueError:
            continue
        if num.is_integer():
            num = int(num)
        results.append((name.replace(".", "_"), num))
    return results


def poll(config, _creds):
    host = config.get("host", HOST_DEFAULT)
    port = int(config.get("port", PORT_DEFAULT))
    ups = config.get("ups", UPS_DEFAULT)
    timeout = config.get("timeout", TIMEOUT_DEFAULT)

    end_marker = f"END LIST VAR {ups}".encode()

    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(f"LIST VAR {ups}\n".encode())
        text = _recv_until(sock, end_marker)
        try:
            sock.sendall(b"LOGOUT\n")
        except OSError:
            pass

    if f"BEGIN LIST VAR {ups}" not in text:
        raise RuntimeError(f"unexpected NUT response: {text[:200]!r}")

    return _parse_vars(text, ups)
