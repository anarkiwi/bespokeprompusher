import json
import time

import requests
from tplinkrouterc6u import TPLinkDecoClient
from tplinkrouterc6u.common.exception import ClientError, ClientException

IP_DEFAULT = "http://192.168.254.1"
FIELDS = ["rssi", "rsrq", "snr", "rsrp", "uplink_rate", "downlink_rate"]

# Uptime/PCI are cloud-passthrough only, so uptimes are timed here, per Deco.
_STATE = {}


class _TPLinkDecoClient2(TPLinkDecoClient):
    def get_internet(self):
        return self.request(
            "admin/network?form=internet", json.dumps({"operation": "read"})
        )


class _Uptime:
    """Seconds since `up` last went false -> true, as observed by the caller.

    exact stays 0 while the anchor is merely the first observation, i.e. the
    value is a lower bound rather than a real session/boot age.
    """

    def __init__(self):
        self._since = None
        self.exact = False

    def update(self, up, now):
        if not up:
            self._since = None
            self.exact = True
            return 0.0
        if self._since is None:
            self._since = now
        return now - self._since


def poll(config, creds):
    ip = config.get("url", IP_DEFAULT)
    if ip not in _STATE:
        _STATE[ip] = (_Uptime(), _Uptime())
    session, reachable = _STATE[ip]
    now = time.monotonic()
    pw = creds.get("deco", "password")
    try:
        router = _TPLinkDecoClient2(ip, pw)
        router.authorize()
        internet_stats = router.get_internet()
        router.logout()
    except (requests.exceptions.ConnectionError, ClientError, ClientException):
        # Losing the Deco breaks observation of the cell session too.
        session.update(False, now)
        reachable.update(False, now)
        return []

    cpe = internet_stats["mobile_cpe"]
    results = []
    for k, v in cpe.items():
        if k in FIELDS:
            results.append((k, float(v)))
        elif k == "network_type":
            results.append(("lte_plus", int(v == "lte_plus")))
    connected = cpe.get("dial_status") == "connected"
    results.extend(
        (
            ("cell_session_uptime_seconds", session.update(connected, now)),
            ("cell_session_uptime_exact", int(session.exact)),
            ("system_uptime_seconds", reachable.update(True, now)),
            ("system_uptime_exact", int(reachable.exact)),
        )
    )
    return results
