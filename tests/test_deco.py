from unittest.mock import MagicMock, patch

import requests
from tplinkrouterc6u.common.exception import ClientError

from bespokeprompusher.pollers import deco


def _creds(password="testpw"):
    m = MagicMock()
    m.get.return_value = password
    return m


def _router(mobile_cpe):
    r = MagicMock()
    r.get_internet.return_value = {"mobile_cpe": mobile_cpe}
    return r


def test_extracts_numeric_fields():
    router = _router(
        {
            "rssi": "75",
            "rsrq": "9",
            "snr": "12",
            "rsrp": "90",
            "uplink_rate": "10",
            "downlink_rate": "50",
        }
    )
    with patch(
        "bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router
    ):
        results = deco.poll({}, _creds())
    d = dict(results)
    assert d["rssi"] == 75.0
    assert d["downlink_rate"] == 50.0


def test_network_type_lte_plus():
    router = _router({"network_type": "lte_plus"})
    with patch(
        "bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router
    ):
        results = deco.poll({}, _creds())
    assert dict(results)["lte_plus"] == 1


def test_network_type_not_lte_plus():
    router = _router({"network_type": "lte"})
    with patch(
        "bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router
    ):
        results = deco.poll({}, _creds())
    assert dict(results)["lte_plus"] == 0


def test_unknown_fields_ignored():
    router = _router({"rssi": "80", "unknown_field": "ignored"})
    with patch(
        "bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router
    ):
        results = deco.poll({}, _creds())
    assert "unknown_field" not in dict(results)


def test_returns_empty_on_connection_error():
    router = MagicMock()
    router.authorize.side_effect = requests.exceptions.ConnectionError
    with patch(
        "bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router
    ):
        assert not deco.poll({}, _creds())


def test_returns_empty_on_client_error():
    router = MagicMock()
    router.authorize.side_effect = ClientError
    with patch(
        "bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router
    ):
        assert not deco.poll({}, _creds())
