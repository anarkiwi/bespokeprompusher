from unittest.mock import MagicMock, patch

import pytest
import requests

from bespokeprompusher.pollers import updateip


def _creds(token="testtoken"):
    m = MagicMock()
    m.get.side_effect = lambda section, key: {("directnic", "token"): token}[
        (section, key)
    ]
    return m


def _http_ok(headers=None):
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.headers = headers or {}
    return r


def _wan_ip(ip):
    return patch("bespokeprompusher.pollers.updateip._echo_wan_ip", return_value=ip)


def test_returns_synced_when_dns_matches():
    with _wan_ip("1.2.3.4"), patch("socket.gethostbyname", return_value="1.2.3.4"):
        results = updateip.poll({"dns_record": "x.example"}, _creds())
    assert dict(results) == {"synced": 1}


def test_updates_when_dns_stale_and_reports_ok():
    with (
        _wan_ip("9.8.7.6"),
        patch("socket.gethostbyname", return_value="1.2.3.4"),
        patch("requests.get", return_value=_http_ok()) as mock_get,
    ):
        results = updateip.poll({"dns_record": "x.example"}, _creds(token="tok"))
    assert dict(results) == {"synced": 0, "update_ok": 1}
    url = mock_get.call_args.args[0]
    assert "tok" in url
    assert "9.8.7.6" in url


def test_reports_update_failure():
    bad = MagicMock()
    bad.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
    with (
        _wan_ip("9.8.7.6"),
        patch("socket.gethostbyname", return_value="1.2.3.4"),
        patch("requests.get", return_value=bad),
    ):
        results = updateip.poll({"dns_record": "x.example"}, _creds())
    assert dict(results) == {"synced": 0, "update_ok": 0}


def test_raises_on_dns_failure():
    with (
        _wan_ip("1.2.3.4"),
        patch("socket.gethostbyname", side_effect=OSError("no such host")),
    ):
        with pytest.raises(RuntimeError, match="resolve x.example"):
            updateip.poll({"dns_record": "x.example"}, _creds())


def test_raises_when_echo_unreachable():
    with patch(
        "requests.get", side_effect=requests.exceptions.ConnectTimeout("timeout")
    ):
        with pytest.raises(RuntimeError, match="failed to read WAN IP"):
            updateip.poll({"dns_record": "x.example"}, _creds())


# pylint: disable=protected-access
def test_echo_wan_ip_reads_header():
    with patch("requests.get", return_value=_http_ok(headers={"X-WAN-IP": "5.6.7.8"})):
        ip = updateip._echo_wan_ip("https://numbers.example/whatismyip")
    assert ip == "5.6.7.8"


def test_echo_wan_ip_raises_when_header_missing():
    with patch("requests.get", return_value=_http_ok(headers={})):
        with pytest.raises(RuntimeError, match="whatismyip echo failed"):
            updateip._echo_wan_ip("https://numbers.example/whatismyip")


def test_echo_wan_ip_raises_on_bad_ip_in_header():
    with patch(
        "requests.get", return_value=_http_ok(headers={"X-WAN-IP": "not-an-ip"})
    ):
        with pytest.raises(RuntimeError, match="whatismyip echo failed"):
            updateip._echo_wan_ip("https://numbers.example/whatismyip")


def test_uses_configured_whatismyip_url():
    with (
        patch(
            "bespokeprompusher.pollers.updateip._echo_wan_ip", return_value="1.2.3.4"
        ) as mock_wan,
        patch("socket.gethostbyname", return_value="1.2.3.4"),
    ):
        updateip.poll(
            {
                "dns_record": "x.example",
                "whatismyip_url": "https://custom.example/whatismyip",
            },
            _creds(),
        )
    mock_wan.assert_called_once_with("https://custom.example/whatismyip")
