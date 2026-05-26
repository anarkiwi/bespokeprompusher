import requests

URL_DEFAULT = "http://fronius.finf/solar_api/v1/GetInverterRealtimeData.cgi"
PARAMS_DEFAULT = {
    "Scope": "Device",
    "DataCollection": "CommonInverterData",
    "DeviceId": "1",
}
FIELDS = ("PAC", "IAC", "UAC", "FAC", "IDC", "UDC")


def poll(config, _creds):
    url = config.get("url", URL_DEFAULT)
    params = config.get("params", PARAMS_DEFAULT)
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return []

    data = resp.json().get("Body", {}).get("Data")
    if not data:
        return []

    results = []
    for field in FIELDS:
        entry = data.get(field)
        if entry is not None:
            results.append((field, entry["Value"]))

    error_code = (data.get("DeviceStatus") or {}).get("ErrorCode") or 0
    results.append(("ErrorCode", error_code))
    return results
