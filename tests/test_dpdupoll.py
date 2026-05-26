from unittest.mock import MagicMock, patch

from bespokeprompusher.pollers import dpdupoll


def _creds(community="testcomm"):
    m = MagicMock()
    m.get.return_value = community
    return m


def _snmp_ok(value):
    r = MagicMock()
    r.returncode = 0
    r.stdout = f"iso.1.2.3 = INTEGER: {value}\n".encode()
    return r


def test_returns_voltage_and_current():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_snmp_ok(2400), _snmp_ok(15)]
        results = dpdupoll.poll({}, _creds())
    d = dict(results)
    assert d["rPDUPhaseStatusVoltage"] == 2400
    assert d["rPDUPhaseStatusCurrent"] == 1.5  # 15 * 0.1


def test_uses_configured_host():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_snmp_ok(100), _snmp_ok(10)]
        dpdupoll.poll({"host": "myhost.local"}, _creds())
    for call in mock_run.call_args_list:
        assert "myhost.local" in call.args[0]


def test_uses_community_from_creds():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [_snmp_ok(100), _snmp_ok(10)]
        dpdupoll.poll({}, _creds("secret123"))
    for call in mock_run.call_args_list:
        assert "secret123" in call.args[0]


def test_raises_on_snmpwalk_failure():
    import pytest

    bad = MagicMock()
    bad.returncode = 1
    bad.stderr = b"timeout"
    with patch("subprocess.run", return_value=bad):
        with pytest.raises(RuntimeError, match="snmpwalk failed"):
            dpdupoll.poll({}, _creds())
