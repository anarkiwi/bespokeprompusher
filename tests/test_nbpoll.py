from unittest.mock import MagicMock, patch

import pytest

from bespokeprompusher.pollers import nbpoll


def _creds(community="testcomm"):
    m = MagicMock()
    m.get.return_value = community
    return m


def _snmp_ok(value):
    r = MagicMock()
    r.returncode = 0
    r.stdout = f"iso.1.2.3 = Counter64: {value}\n".encode()
    return r


def test_returns_in_and_out_octets_per_station():
    with patch("subprocess.run") as mock_run:
        # order: (nbifInOct birdsong, nbifInOct gnd, nbifOutOct birdsong, nbifOutOct gnd)
        mock_run.side_effect = [_snmp_ok(1), _snmp_ok(2), _snmp_ok(3), _snmp_ok(4)]
        results = nbpoll.poll({}, _creds())
    d = dict(results)
    assert d['nbifInOct{station="birdsong-nb"}'] == 1
    assert d['nbifInOct{station="gnd-nb"}'] == 2
    assert d['nbifOutOct{station="birdsong-nb"}'] == 3
    assert d['nbifOutOct{station="gnd-nb"}'] == 4


def test_uses_configured_stations():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_snmp_ok(10), _snmp_ok(20)]
        nbpoll.poll({"stations": ["only-nb"]}, _creds())
    queried = [call.args[0][-2] for call in mock_run.call_args_list]
    assert queried == ["only-nb", "only-nb"]


def test_uses_community_from_creds():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_snmp_ok(1), _snmp_ok(1), _snmp_ok(1), _snmp_ok(1)]
        nbpoll.poll({}, _creds("secret123"))
    for call in mock_run.call_args_list:
        assert "secret123" in call.args[0]


def test_raises_on_snmpwalk_failure():
    bad = MagicMock()
    bad.returncode = 1
    bad.stderr = b"timeout"
    with patch("subprocess.run", return_value=bad):
        with pytest.raises(RuntimeError, match="snmpwalk failed"):
            nbpoll.poll({}, _creds())
