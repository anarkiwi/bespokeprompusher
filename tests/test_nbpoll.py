from unittest.mock import MagicMock, patch

from bespokeprompusher.pollers import nbpoll
from tests.snmp_helpers import creds, snmp_ok


def test_emits_all_vars_with_station_label():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [snmp_ok(v) for v in range(1, len(nbpoll.VARS) + 1)]
        d = dict(nbpoll.poll({}, creds()))
    for i, var in enumerate(nbpoll.VARS, start=1):
        assert d[f'{var}{{station="gnd-nb"}}'] == i


def test_uses_configured_stations():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = [snmp_ok(10)] * len(nbpoll.VARS)
        nbpoll.poll({"stations": ["only-nb"]}, creds())
    queried = [call.args[0][-2] for call in mock_run.call_args_list]
    assert queried == ["only-nb"] * len(nbpoll.VARS)


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
