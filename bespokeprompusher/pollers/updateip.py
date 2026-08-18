import socket

import requests

DIRECTNIC_URL = "https://directnic.com/dns/gateway/{token}/?data={ip}"
# Client-IP echo on our own numbers VPS, not the Deco's local API.
WHATISMYIP_URL = "https://www.vandervecken.com/whatismyip"


def _echo_wan_ip(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        ip = resp.headers["X-WAN-IP"]
        socket.inet_aton(ip)
        return ip
    except (requests.exceptions.RequestException, KeyError, OSError) as e:
        raise RuntimeError(f"whatismyip echo failed: {e}") from e


def poll(config, creds):
    dns_record = config["dns_record"]
    token = creds.get("directnic", "token")
    url = config.get("whatismyip_url", WHATISMYIP_URL)

    try:
        current_ip = _echo_wan_ip(url)
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
