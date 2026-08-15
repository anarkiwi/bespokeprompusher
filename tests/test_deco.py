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


def _router(mobile_cpe, performance=None):
    r = MagicMock()
    r.get_internet.return_value = {"mobile_cpe": mobile_cpe}
    r.get_performance.return_value = {} if performance is None else performance
    return r


def _connected(performance=None, **extra):
    return _router({"dial_status": "connected", **extra}, performance)


def _set_cpe(router, mobile_cpe):
    router.get_internet.return_value = {"mobile_cpe": mobile_cpe}


def _poll_ctor(router, now=0.0, config=None):
    """Poll once, returning (metrics, the patched client constructor)."""
    with (
        patch(
            "bespokeprompusher.pollers.deco._TPLinkDecoClient2", return_value=router
        ) as ctor,
        patch("bespokeprompusher.pollers.deco.time.monotonic", return_value=now),
    ):
        return dict(deco.poll({} if config is None else config, _creds())), ctor


def _poll(router, now=0.0, config=None):
    return _poll_ctor(router, now, config)[0]


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
    router = _router({"dial_status": "disconnected"})
    assert _poll(router, now=10.0) == {
        "cell_session_uptime_seconds": 0.0,
        "cell_session_uptime_exact": 1,
        "system_uptime_seconds": 0.0,
        "system_uptime_exact": 0,
    }
    _set_cpe(router, {"dial_status": "connected"})
    redialed = _poll(router, now=20.0)
    assert redialed["cell_session_uptime_seconds"] == 0.0
    assert redialed["cell_session_uptime_exact"] == 1
    assert _poll(router, now=35.0)["cell_session_uptime_seconds"] == 15.0


def test_unreachable_deco_restarts_both_timers():
    router = _connected()
    _poll(router, now=0.0)
    assert _poll(router, now=30.0)["system_uptime_seconds"] == 30.0
    router.get_internet.side_effect = requests.exceptions.ConnectionError
    assert not _poll(router, now=60.0)
    router.get_internet.side_effect = None
    recovered = _poll(router, now=90.0)
    assert recovered["system_uptime_seconds"] == 0.0
    assert recovered["system_uptime_exact"] == 1
    assert recovered["cell_session_uptime_seconds"] == 0.0
    assert _poll(router, now=100.0)["system_uptime_seconds"] == 10.0


def test_exports_cpu_and_memory():
    d = _poll(_connected(performance={"cpu_usage": 0.21, "mem_usage": 0.5}))
    assert d["cpu_usage"] == 0.21
    assert d["mem_usage"] == 0.5


def test_unavailable_performance_keeps_the_other_metrics():
    d = _poll(_connected(rssi="80"))
    assert "mem_usage" not in d
    assert d["rssi"] == 80.0
    assert d["system_uptime_seconds"] == 0.0


def test_get_performance_swallows_a_client_error():
    # pylint: disable=protected-access
    client = deco._TPLinkDecoClient2.__new__(deco._TPLinkDecoClient2)
    with patch.object(deco._TPLinkDecoClient2, "_read", side_effect=ClientError):
        assert not client.get_performance()


def test_state_is_per_deco():
    other = {"url": "http://192.168.254.2"}
    _poll(_connected(), now=0.0)
    assert _poll(_connected(), now=50.0, config=other)["system_uptime_seconds"] == 0.0
    assert _poll(_connected(), now=50.0)["system_uptime_seconds"] == 50.0


def test_client_is_reused_across_polls():
    """One login serves every later poll; that is the point of holding it."""
    router = _connected()
    _poll(router, now=0.0)
    for now in (60.0, 120.0, 180.0):
        _, ctor = _poll_ctor(router, now=now)
        ctor.assert_not_called()
    assert router.authorize.call_count == 1


def test_session_is_never_logged_out():
    """Logging out throws away the session the next poll would have reused."""
    router = _connected()
    _poll(router, now=0.0)
    _poll(router, now=60.0)
    router.logout.assert_not_called()


def test_expired_session_logs_in_again_and_recovers():
    first = _connected(rssi="80")
    _poll(first, now=0.0)
    first.get_internet.side_effect = ClientError
    second = _connected(rssi="90")
    metrics, ctor = _poll_ctor(second, now=60.0)
    assert metrics["rssi"] == 90.0
    ctor.assert_called_once()
    assert second.authorize.call_count == 1


def test_expired_session_that_cannot_log_in_again_gives_up():
    router = _connected()
    _poll(router, now=0.0)
    router.get_internet.side_effect = ClientError
    assert not _poll(router, now=60.0)


def test_connection_error_does_not_log_in_again():
    """A Deco that is not answering gets no extra login attempt."""
    router = _connected()
    _poll(router, now=0.0)
    router.get_internet.side_effect = requests.exceptions.ConnectionError
    metrics, ctor = _poll_ctor(router, now=60.0)
    assert not metrics
    ctor.assert_not_called()


def test_read_timeout_resets_the_timers():
    """A wedging Deco stops mid-request, which is a timeout, not a refusal."""
    router = _connected()
    _poll(router, now=0.0)
    router.get_internet.side_effect = requests.exceptions.ReadTimeout
    assert not _poll(router, now=60.0)
    router.get_internet.side_effect = None
    assert _poll(router, now=90.0)["system_uptime_seconds"] == 0.0
