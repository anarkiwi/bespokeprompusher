from unittest.mock import MagicMock, patch

import pytest

from bespokeprompusher.pollers import aquapoll


def _valid_response(level=50, rssi=90, temp=22, batt=1, tank_id=1):
    return bytes([0x02, tank_id, 0x00, level, rssi, temp, batt, 0x00, 0x0D])


def _make_serial(responses):
    instance = MagicMock()
    instance.__enter__ = MagicMock(return_value=instance)
    instance.__exit__ = MagicMock(return_value=False)
    instance.read.side_effect = responses
    return instance


def test_parses_valid_response():
    s = _make_serial([_valid_response(level=75, temp=23)])
    with patch("serial.Serial", return_value=s):
        results = aquapoll.poll({}, None)
    d = dict(results)
    assert d["level"] == 75
    assert d["temperature_c"] == 23
    assert d["rssi"] == 90
    assert d["battery_status"] == 1


def test_returns_all_four_metrics():
    s = _make_serial([_valid_response()])
    with patch("serial.Serial", return_value=s):
        results = aquapoll.poll({}, None)
    names = [n for n, _ in results]
    assert names == ["level", "rssi", "temperature_c", "battery_status"]


def test_retries_on_short_read():
    s = _make_serial(
        [
            b"\x00" * 5,  # too short
            b"\x00" * 9,  # wrong terminator
            _valid_response(level=60),
        ]
    )
    with patch("serial.Serial", return_value=s), patch("time.sleep"):
        results = aquapoll.poll({}, None)
    assert dict(results)["level"] == 60


def test_raises_after_three_failures():
    s = _make_serial([b"\x00" * 9] * 3)  # always wrong terminator
    with patch("serial.Serial", return_value=s), patch("time.sleep"):
        with pytest.raises(RuntimeError, match="no valid response"):
            aquapoll.poll({}, None)


def test_uses_configured_port():
    s = _make_serial([_valid_response()])
    with patch("serial.Serial", return_value=s) as mock_cls:
        aquapoll.poll({"port": "/dev/ttyUSB0"}, None)
    assert mock_cls.call_args.args[0] == "/dev/ttyUSB0"


def test_raises_on_wrong_tank_id():
    bad = _valid_response(tank_id=2)
    s = _make_serial([bad])
    with patch("serial.Serial", return_value=s), patch("time.sleep"):
        with pytest.raises((ValueError, RuntimeError)):
            aquapoll.poll({"tank_id": 1}, None)
