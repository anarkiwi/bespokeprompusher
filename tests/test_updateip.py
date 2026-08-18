import subprocess
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


def _http_ok():
    r = MagicMock()
    r.raise_for_status.return_value = None
    return r


def _ssh_result(returncode=0, out=b"", err=b""):
    return MagicMock(returncode=returncode, stdout=out, stderr=err)


def _wan_ip(ip):
    return patch("bespokeprompusher.pollers.updateip._ssh_wan_ip", return_value=ip)


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


def test_raises_when_ssh_unreachable():
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=15)
    ):
        with pytest.raises(RuntimeError, match="failed to read WAN IP"):
            updateip.poll({"dns_record": "x.example"}, _creds())


# pylint: disable=protected-access
def test_ssh_wan_ip_parses_ssh_client_output():
    with patch("subprocess.run", return_value=_ssh_result(out=b"5.6.7.8 51413 2222\n")):
        ip = updateip._ssh_wan_ip("numbers.example", "/key", "/known_hosts")
    assert ip == "5.6.7.8"


def test_ssh_wan_ip_raises_on_nonzero_returncode():
    with patch(
        "subprocess.run", return_value=_ssh_result(returncode=255, err=b"denied")
    ):
        with pytest.raises(RuntimeError, match="ssh whatismyip failed"):
            updateip._ssh_wan_ip("numbers.example", "/key", "/known_hosts")


def test_ssh_wan_ip_raises_on_empty_output():
    with patch("subprocess.run", return_value=_ssh_result(out=b"")):
        with pytest.raises(RuntimeError, match="no output"):
            updateip._ssh_wan_ip("numbers.example", "/key", "/known_hosts")


def test_ssh_wan_ip_raises_on_bad_ip():
    with patch("subprocess.run", return_value=_ssh_result(out=b"not-an-ip 1 2\n")):
        with pytest.raises(RuntimeError, match="invalid IP"):
            updateip._ssh_wan_ip("numbers.example", "/key", "/known_hosts")


def test_uses_configured_ssh_params():
    with (
        patch(
            "bespokeprompusher.pollers.updateip._ssh_wan_ip", return_value="1.2.3.4"
        ) as mock_wan,
        patch("socket.gethostbyname", return_value="1.2.3.4"),
    ):
        updateip.poll(
            {
                "dns_record": "x.example",
                "ssh_host": "custom.example",
                "ssh_key": "/custom/key",
                "ssh_known_hosts": "/custom/known_hosts",
            },
            _creds(),
        )
    mock_wan.assert_called_once_with(
        "custom.example", "/custom/key", "/custom/known_hosts"
    )
