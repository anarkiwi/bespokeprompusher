from unittest.mock import MagicMock, patch

import pytest
import requests
from tplinkrouterc6u.common.exception import ClientError

from bespokeprompusher.pollers import deco


@pytest.fixture(autouse=True)
def _reset_state():
    deco._STATE.clear()  # pylint: disable=protected-access
    yield
    deco._STATE.clear()  # pylint: disable=protected-access


def _creds(password="testpw"):
    m = MagicMock()
    m.get.return_value = password
    return m


def _router(mobile_cpe):
    r = MagicMock()
    r.get_internet.return_value = {"mobile_cpe": mobile_cpe}
    return r


def _poll(router, now=0.0, config=None):
    with (
        patch("bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router),
        patch("bespokeprompusher.pollers.deco.time.monotonic", return_value=now),
    ):
        return dict(deco.poll({} if config is None else config, _creds()))


def _connected(**extra):
    return _router({"dial_status": "connected", **extra})


def _unreachable(exc=requests.exceptions.ConnectionError):
    r = MagicMock()
    r.authorize.side_effect = exc
    return r


def test_extracts_numeric_fields():
    router = _connected(
        rssi="75",
        rsrq="9",
        snr="12",
        rsrp="90",
        uplink_rate="10",
        downlink_rate="50",
    )
    d = _poll(router)
    assert d["rssi"] == 75.0
    assert d["downlink_rate"] == 50.0


def test_network_type_lte_plus():
    assert _poll(_connected(network_type="lte_plus"))["lte_plus"] == 1


def test_network_type_not_lte_plus():
    assert _poll(_connected(network_type="lte"))["lte_plus"] == 0


def test_unknown_fields_ignored():
    assert "unknown_field" not in _poll(_connected(rssi="80", unknown_field="ignored"))


def test_returns_empty_on_connection_error():
    assert not _poll(_unreachable())


def test_returns_empty_on_client_error():
    assert not _poll(_unreachable(ClientError))


def test_uptimes_anchor_on_first_poll_and_grow():
    router = _connected()
    first = _poll(router, now=100.0)
    assert first["cell_session_uptime_seconds"] == 0.0
    assert first["system_uptime_seconds"] == 0.0
    later = _poll(router, now=160.0)
    assert later["cell_session_uptime_seconds"] == 60.0
    assert later["system_uptime_seconds"] == 60.0


def test_first_poll_uptimes_are_lower_bounds():
    d = _poll(_connected(), now=10.0)
    assert d["cell_session_uptime_exact"] == 0
    assert d["system_uptime_exact"] == 0


def test_session_uptime_resets_and_becomes_exact_on_redial():
    assert _poll(_router({"dial_status": "disconnected"}), now=10.0) == {
        "cell_session_uptime_seconds": 0.0,
        "cell_session_uptime_exact": 1,
        "system_uptime_seconds": 0.0,
        "system_uptime_exact": 0,
    }
    redialed = _poll(_connected(), now=20.0)
    assert redialed["cell_session_uptime_seconds"] == 0.0
    assert redialed["cell_session_uptime_exact"] == 1
    assert _poll(_connected(), now=35.0)["cell_session_uptime_seconds"] == 15.0


def test_unreachable_deco_restarts_both_timers():
    _poll(_connected(), now=0.0)
    assert _poll(_connected(), now=30.0)["system_uptime_seconds"] == 30.0
    assert not _poll(_unreachable(), now=60.0)
    recovered = _poll(_connected(), now=90.0)
    assert recovered["system_uptime_seconds"] == 0.0
    assert recovered["system_uptime_exact"] == 1
    assert recovered["cell_session_uptime_seconds"] == 0.0
    assert _poll(_connected(), now=100.0)["system_uptime_seconds"] == 10.0


def test_state_is_per_deco():
    other = {"url": "http://192.168.254.2"}
    _poll(_connected(), now=0.0)
    assert _poll(_connected(), now=50.0, config=other)["system_uptime_seconds"] == 0.0
    assert _poll(_connected(), now=50.0)["system_uptime_seconds"] == 50.0
