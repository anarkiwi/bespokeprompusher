import socket

import requests
from tplinkrouterc6u import TPLinkDecoClient
from tplinkrouterc6u.common.exception import ClientError, ClientException

DECO_DEFAULT = "http://192.168.254.1"
DIRECTNIC_URL = "https://directnic.com/dns/gateway/{token}/?data={ip}"


def _deco_wan_ip(host, password):
    router = TPLinkDecoClient(host, password)
    router.authorize()
    try:
        ip = router.get_ipv4_status().wan_ipv4_ipaddress
    finally:
        router.logout()
    if ip is None:
        raise RuntimeError("Deco returned no WAN IPv4 address")
    return str(ip)


def poll(config, creds):
    deco_host = config.get("deco_host", DECO_DEFAULT)
    dns_record = config["dns_record"]
    deco_password = creds.get("deco", "password")
    token = creds.get("directnic", "token")

    try:
        current_ip = _deco_wan_ip(deco_host, deco_password)
        socket.inet_aton(current_ip)
    except (
        requests.exceptions.RequestException,
        ClientError,
        ClientException,
        OSError,
    ) as e:
        raise RuntimeError(f"updateip: failed to read WAN IP from Deco: {e}") from e

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
