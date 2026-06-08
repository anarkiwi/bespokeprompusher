from unittest.mock import MagicMock, patch

from bespokeprompusher.pollers import nbpoll
from tests.snmp_helpers import creds, snmp_ok


def test_emits_in_and_out_octets_with_station_label():
    with patch("subprocess.run") as mock_run:
        # station-first order: birdsong(in, out), gnd(in, out)
        mock_run.side_effect = [snmp_ok(1), snmp_ok(2), snmp_ok(3), snmp_ok(4)]
        d = dict(nbpoll.poll({}, creds()))
    assert d['nbifInOct{station="birdsong-nb"}'] == 1
    assert d['nbifOutOct{station="birdsong-nb"}'] == 2
    assert d['nbifInOct{station="gnd-nb"}'] == 3
    assert d['nbifOutOct{station="gnd-nb"}'] == 4


def test_uses_configured_stations():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [snmp_ok(10), snmp_ok(20)]
        nbpoll.poll({"stations": ["only-nb"]}, creds())
    queried = [call.args[0][-2] for call in mock_run.call_args_list]
    assert queried == ["only-nb", "only-nb"]


def test_skips_unreachable_station_but_keeps_others():
    def fake_run(cmd, **_kwargs):
        if cmd[-2] == "down-nb":
            bad = MagicMock()
            bad.returncode = 1
            bad.stderr = b"Timeout: No Response"
            return bad
        return snmp_ok(7)

    with patch("subprocess.run", side_effect=fake_run):
        d = dict(nbpoll.poll({"stations": ["down-nb", "up-nb"]}, creds()))
    assert all("down-nb" not in name for name in d)
    assert d['nbifInOct{station="up-nb"}'] == 7
    assert d['nbifOutOct{station="up-nb"}'] == 7
