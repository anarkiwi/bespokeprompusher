from unittest.mock import MagicMock, patch

import pytest
import requests

from bespokeprompusher.pollers import updateip


def _creds(deco_pw="decopw", token="testtoken"):
    m = MagicMock()
    m.get.side_effect = lambda section, key: {
        ("deco", "password"): deco_pw,
        ("directnic", "token"): token,
    }[(section, key)]
    return m


def _http_ok():
    r = MagicMock()
    r.raise_for_status.return_value = None
    return r


def _wan_ip(ip):
    """Patch _deco_wan_ip to return ip."""
    return patch("bespokeprompusher.pollers.updateip._deco_wan_ip", return_value=ip)


def test_returns_synced_when_dns_matches():
    with _wan_ip("1.2.3.4"), patch("socket.gethostbyname", return_value="1.2.3.4"):
        results = updateip.poll({"dns_record": "x.example"}, _creds())
    assert dict(results) == {"synced": 1}


def test_updates_when_dns_stale_and_reports_ok():
    with (
        _wan_ip("9.8.7.6"),
        patch("socket.gethostbyname", return_value="1.2.3.4"),
        patch("requests.get", return_value=_http_ok()) as mock_post,
    ):
        results = updateip.poll({"dns_record": "x.example"}, _creds(token="tok"))
    assert dict(results) == {"synced": 0, "update_ok": 1}
    url = mock_post.call_args.args[0]
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


def test_raises_on_bad_ip_response():
    with _wan_ip("not-an-ip"):
        with pytest.raises(RuntimeError, match="WAN IP"):
            updateip.poll({"dns_record": "x.example"}, _creds())


def test_raises_on_dns_failure():
    with (
        _wan_ip("1.2.3.4"),
        patch("socket.gethostbyname", side_effect=OSError("no such host")),
    ):
        with pytest.raises(RuntimeError, match="resolve x.example"):
            updateip.poll({"dns_record": "x.example"}, _creds())


def test_uses_configured_deco_host():
    with (
        patch(
            "bespokeprompusher.pollers.updateip._deco_wan_ip", return_value="1.2.3.4"
        ) as mock_wan,
        patch("socket.gethostbyname", return_value="1.2.3.4"),
    ):
        updateip.poll(
            {"dns_record": "x.example", "deco_host": "http://10.0.0.1"},
            _creds(deco_pw="custompw"),
        )
    mock_wan.assert_called_once_with("http://10.0.0.1", "custompw")
