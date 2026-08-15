import json
import time

import requests
from tplinkrouterc6u import TPLinkDecoClient
from tplinkrouterc6u.common.exception import ClientError, ClientException

IP_DEFAULT = "http://192.168.254.1"
FIELDS = ["rssi", "rsrq", "snr", "rsrp", "uplink_rate", "downlink_rate"]
# Deco 4G/5G firmware is reported to fill RAM with NAT sessions until it wedges.
PERF_FIELDS = ["cpu_usage", "mem_usage"]

# Uptime/PCI are cloud-passthrough only, so uptimes are timed here, per Deco.
_STATE = {}

_AUTH_ERRORS = (ClientError, ClientException)


class _TPLinkDecoClient2(TPLinkDecoClient):
    def _read(self, form):
        return self.request(
            f"admin/network?form={form}", json.dumps({"operation": "read"})
        )

    def get_internet(self):
        return self._read("internet")

    def get_performance(self):
        """cpu_usage/mem_usage, or {} rather than costing us the signal metrics."""
        try:
            return self._read("performance")
        except _AUTH_ERRORS:
            return {}


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


class _Deco:
    """Uptime timers plus one authorized client, reused across polls.

    Logging in costs three POSTs and an RSA decrypt on the Deco, whose
    management plane is what wedges first. tplinkrouterc6u caches the key and
    sequence per client, so a reused client re-fetches neither.
    """

    def __init__(self):
        self.session = _Uptime()
        self.reachable = _Uptime()
        self._client = None

    def _connect(self, url, password):
        if self._client is None:
            client = _TPLinkDecoClient2(url, password)
            client.authorize()
            self._client = client
        return self._client

    def drop(self):
        self._client = None

    def read(self, url, password):
        """Both forms, logging in again only if a held session has expired.

        A request error is never retried: the Deco is not answering, and a
        second login only adds load to a device that is already wedging.
        """
        held = self._client is not None
        try:
            client = self._connect(url, password)
            return client.get_internet(), client.get_performance()
        except _AUTH_ERRORS:
            self.drop()
            if not held:
                raise
        client = self._connect(url, password)
        return client.get_internet(), client.get_performance()


def poll(config, creds):
    url = config.get("url", IP_DEFAULT)
    state = _STATE.setdefault(url, _Deco())
    now = time.monotonic()
    try:
        internet_stats, performance = state.read(url, creds.get("deco", "password"))
    except (requests.exceptions.RequestException,) + _AUTH_ERRORS:
        # Losing the Deco breaks observation of the cell session too.
        state.drop()
        state.session.update(False, now)
        state.reachable.update(False, now)
        return []

    cpe = internet_stats["mobile_cpe"]
    results = []
    for k, v in cpe.items():
        if k in FIELDS:
            results.append((k, float(v)))
        elif k == "network_type":
            results.append(("lte_plus", int(v == "lte_plus")))
    results.extend((k, float(v)) for k, v in performance.items() if k in PERF_FIELDS)
    connected = cpe.get("dial_status") == "connected"
    results.extend(
        (
            ("cell_session_uptime_seconds", state.session.update(connected, now)),
            ("cell_session_uptime_exact", int(state.session.exact)),
            ("system_uptime_seconds", state.reachable.update(True, now)),
            ("system_uptime_exact", int(state.reachable.exact)),
        )
    )
    return results
