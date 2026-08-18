import socket
import subprocess

import requests

DIRECTNIC_URL = "https://directnic.com/dns/gateway/{token}/?data={ip}"
SSH_HOST = "numbers.vandervecken.com"
SSH_KEY = "/secrets/whatismyip_id_ed25519"
SSH_KNOWN_HOSTS = "/secrets/whatismyip_known_hosts"


def _ssh_wan_ip(host, key_path, known_hosts):
    try:
        run = subprocess.run(
            [
                "ssh",
                "-p",
                "2222",
                "-i",
                key_path,
                "-o",
                "BatchMode=yes",
                "-o",
                "StrictHostKeyChecking=yes",
                "-o",
                f"UserKnownHostsFile={known_hosts}",
                f"whatismyip@{host}",
            ],
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError) as e:
        raise RuntimeError(f"ssh whatismyip failed: {e}") from e
    if run.returncode != 0:
        raise RuntimeError(f"ssh whatismyip failed: {run.stderr.decode().strip()}")
    fields = run.stdout.decode().split()
    if not fields:
        raise RuntimeError("ssh whatismyip returned no output")
    ip = fields[0]
    try:
        socket.inet_aton(ip)
    except OSError as e:
        raise RuntimeError(f"ssh whatismyip returned invalid IP {ip!r}: {e}") from e
    return ip


def poll(config, creds):
    dns_record = config["dns_record"]
    token = creds.get("directnic", "token")
    host = config.get("ssh_host", SSH_HOST)
    key_path = config.get("ssh_key", SSH_KEY)
    known_hosts = config.get("ssh_known_hosts", SSH_KNOWN_HOSTS)

    try:
        current_ip = _ssh_wan_ip(host, key_path, known_hosts)
    except RuntimeError as e:
        raise RuntimeError(f"updateip: failed to read WAN IP: {e}") from e

    try:
        dns_ip = socket.gethostbyname(dns_record)
    except OSError as e:
        raise RuntimeError(f"updateip: failed to resolve {dns_record}: {e}") from e

    if dns_ip == current_ip:
        return [("synced", 1)]

    try:
        resp = requests.get(
            DIRECTNIC_URL.format(token=token, ip=current_ip), timeout=30
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return [("synced", 0), ("update_ok", 0)]

    return [("synced", 0), ("update_ok", 1)]
