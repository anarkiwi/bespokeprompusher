from unittest.mock import patch

from bespokeprompusher.pollers import nbpoll
from tests.snmp_helpers import creds, snmp_ok


def test_emits_in_and_out_octets_with_station_label():
    with patch("subprocess.run") as mock_run:
        # order: nbifInOct(birdsong, gnd), nbifOutOct(birdsong, gnd)
        mock_run.side_effect = [snmp_ok(1), snmp_ok(2), snmp_ok(3), snmp_ok(4)]
        d = dict(nbpoll.poll({}, creds()))
    assert d['nbifInOct{station="birdsong-nb"}'] == 1
    assert d['nbifInOct{station="gnd-nb"}'] == 2
    assert d['nbifOutOct{station="birdsong-nb"}'] == 3
    assert d['nbifOutOct{station="gnd-nb"}'] == 4


def test_uses_configured_stations():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [snmp_ok(10), snmp_ok(20)]
        nbpoll.poll({"stations": ["only-nb"]}, creds())
    queried = [call.args[0][-2] for call in mock_run.call_args_list]
    assert queried == ["only-nb", "only-nb"]
