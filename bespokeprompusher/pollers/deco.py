import json

import requests
from tplinkrouterc6u import TPLinkDecoClient
from tplinkrouterc6u.common.exception import ClientError, ClientException

IP_DEFAULT = "http://192.168.254.1"
FIELDS = ["rssi", "rsrq", "snr", "rsrp", "uplink_rate", "downlink_rate"]


class _TPLinkDecoClient2(TPLinkDecoClient):
    def get_internet(self):
        return self.request(
            "admin/network?form=internet", json.dumps({"operation": "read"})
        )


def poll(config, creds):
    ip = config.get("url", IP_DEFAULT)
    pw = creds.get("deco", "password")
    try:
        router = _TPLinkDecoClient2(ip, pw)
        router.authorize()
        internet_stats = router.get_internet()
        router.logout()
    except (requests.exceptions.ConnectionError, ClientError, ClientException):
        return []

    results = []
    for k, v in internet_stats["mobile_cpe"].items():
        if k in FIELDS:
            results.append((k, float(v)))
        elif k == "network_type":
            results.append(("lte_plus", int(v == "lte_plus")))
    return results
