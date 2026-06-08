from unittest.mock import patch

from bespokeprompusher.pollers import dpdupoll
from tests.snmp_helpers import creds, snmp_ok


def test_returns_voltage_and_current():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [snmp_ok(2400), snmp_ok(15)]
        results = dpdupoll.poll({}, creds())
    d = dict(results)
    assert d["rPDUPhaseStatusVoltage"] == 2400
    assert d["rPDUPhaseStatusCurrent"] == 1.5  # 15 * 0.1


def test_uses_configured_host():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [snmp_ok(100), snmp_ok(10)]
        dpdupoll.poll({"host": "myhost.local"}, creds())
    for call in mock_run.call_args_list:
        assert "myhost.local" in call.args[0]
