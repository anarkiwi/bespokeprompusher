from unittest.mock import MagicMock, patch

import pytest

from bespokeprompusher.pollers import nut

SAMPLE = (
    b"BEGIN LIST VAR ups\n"
    b'VAR ups battery.charge "100"\n'
    b'VAR ups battery.voltage "27.4"\n'
    b'VAR ups device.mfr "CyberPower Systems"\n'
    b'VAR ups driver.flag.allow_killpower "0"\n'
    b'VAR ups input.voltage "230.0"\n'
    b"END LIST VAR ups\n"
)


def _socket_returning(payload):
    sock = MagicMock()
    sock.__enter__.return_value = sock
    sock.__exit__.return_value = False
    chunks = [payload, b""]
    sock.recv.side_effect = chunks
    return sock


def test_parses_numeric_vars_and_skips_strings():
    sock = _socket_returning(SAMPLE)
    with patch("socket.create_connection", return_value=sock):
        results = nut.poll({}, MagicMock())
    d = dict(results)
    assert d["battery_charge"] == 100
    assert d["battery_voltage"] == 27.4
    assert d["driver_flag_allow_killpower"] == 0
    assert d["input_voltage"] == 230
    assert "device_mfr" not in d


def test_sends_list_var_request_with_configured_ups():
    sock = _socket_returning(
        b'BEGIN LIST VAR myups\nVAR myups battery.charge "42"\nEND LIST VAR myups\n'
    )
    with patch("socket.create_connection", return_value=sock) as conn:
        nut.poll({"host": "h.example", "port": 9999, "ups": "myups"}, MagicMock())
    conn.assert_called_once_with(("h.example", 9999), timeout=10)
    sock.sendall.assert_any_call(b"LIST VAR myups\n")


def test_logout_failure_is_tolerated():
    sock = _socket_returning(SAMPLE)
    sock.sendall.side_effect = [None, OSError("closed")]
    with patch("socket.create_connection", return_value=sock):
        results = nut.poll({}, MagicMock())
    assert results


def test_raises_on_unexpected_response():
    sock = _socket_returning(b"ERR ACCESS-DENIED\n")
    with patch("socket.create_connection", return_value=sock):
        with pytest.raises(RuntimeError, match="unexpected NUT response"):
            nut.poll({}, MagicMock())
