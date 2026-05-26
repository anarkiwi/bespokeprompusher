from unittest.mock import MagicMock, patch

import requests

from bespokeprompusher.pollers import fronius


def _resp(data):
    r = MagicMock()
    r.json.return_value = {"Body": {"Data": data}}
    return r


def test_extracts_all_fields():
    data = {
        "PAC": {"Value": 1200.5},
        "IAC": {"Value": 5.2},
        "UAC": {"Value": 230.1},
        "FAC": {"Value": 50.0},
        "IDC": {"Value": 4.8},
        "UDC": {"Value": 350.0},
        "DeviceStatus": {"ErrorCode": 0},
    }
    with patch("requests.get", return_value=_resp(data)):
        results = fronius.poll({}, None)
    d = dict(results)
    assert d["PAC"] == 1200.5
    assert d["UDC"] == 350.0
    assert d["ErrorCode"] == 0


def test_skips_missing_fields():
    data = {"PAC": {"Value": 500.0}, "DeviceStatus": {"ErrorCode": 0}}
    with patch("requests.get", return_value=_resp(data)):
        results = fronius.poll({}, None)
    names = [n for n, _ in results]
    assert "PAC" in names
    assert "IAC" not in names


def test_error_code_defaults_to_zero_when_absent():
    data = {"PAC": {"Value": 100.0}}
    with patch("requests.get", return_value=_resp(data)):
        results = fronius.poll({}, None)
    assert dict(results)["ErrorCode"] == 0


def test_returns_empty_on_connection_error():
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
        assert not fronius.poll({}, None)


def test_returns_empty_on_null_data():
    r = MagicMock()
    r.json.return_value = {"Body": {"Data": None}}
    with patch("requests.get", return_value=r):
        assert not fronius.poll({}, None)


def test_uses_configured_url():
    with patch(
        "requests.get",
        return_value=_resp({"DeviceStatus": {"ErrorCode": 0}}),
    ) as mock_get:
        fronius.poll({"url": "http://myinverter.local/api"}, None)
    mock_get.assert_called_once()
    assert mock_get.call_args.args[0] == "http://myinverter.local/api"
