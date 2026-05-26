from unittest.mock import MagicMock, patch

import pytest

from bespokeprompusher import main


def test_push_posts_to_correct_url():
    with patch("requests.post") as mock_post:
        mock_post.return_value.raise_for_status = MagicMock()
        main.push("http://gw:9091", "ups", "mdr-pi", [("metric", 1.0)])
    mock_post.assert_called_once()
    assert "ups" in mock_post.call_args.args[0]
    assert "mdr-pi" in mock_post.call_args.args[0]


def test_push_logs_on_error():
    with patch("requests.post", side_effect=Exception("boom")):
        main.push("http://gw:9091", "job", "inst", [("x", 1.0)])


def test_make_poller_calls_poll_and_pushes():
    task = {
        "name": "t",
        "poller": "fronius",
        "job": "j",
        "instance": "i",
        "config": {},
    }
    mock_mod = MagicMock()
    mock_mod.poll.return_value = [("m", 1.0)]
    with (
        patch("importlib.import_module", return_value=mock_mod),
        patch("bespokeprompusher.main.push") as mock_push,
    ):
        fn = main.make_poller(task, "http://gw:9091", MagicMock())
        fn()
    mock_push.assert_called_once_with("http://gw:9091", "j", "i", [("m", 1.0)])


def test_make_poller_skips_push_on_empty():
    task = {
        "name": "t",
        "poller": "fronius",
        "job": "j",
        "instance": "i",
        "config": {},
    }
    mock_mod = MagicMock()
    mock_mod.poll.return_value = []
    with (
        patch("importlib.import_module", return_value=mock_mod),
        patch("bespokeprompusher.main.push") as mock_push,
    ):
        fn = main.make_poller(task, "http://gw:9091", MagicMock())
        fn()
    mock_push.assert_not_called()


def test_loop_catches_exceptions_and_continues():
    calls = []

    def fn():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("fail")

    with patch("time.sleep", side_effect=[None, StopIteration]):
        with pytest.raises(StopIteration):
            main.loop(fn, "test", 10)

    assert len(calls) == 2


def test_main_starts_threads():
    cfg = {
        "pushgateway": "http://gw:9091",
        "secrets_file": "/s/finfsecrets",
        "tasks": [
            {
                "name": "t1",
                "poller": "fronius",
                "job": "j",
                "instance": "i",
                "interval_seconds": 60,
            }
        ],
    }
    with (
        patch("builtins.open", MagicMock()),
        patch("yaml.safe_load", return_value=cfg),
        patch("bespokeprompusher.main.Creds"),
        patch("bespokeprompusher.main.make_poller", return_value=MagicMock()),
        patch("threading.Thread") as mock_thread,
        patch("time.sleep", side_effect=StopIteration),
    ):
        with pytest.raises(StopIteration):
            main.main()
    mock_thread.assert_called_once()
    mock_thread.return_value.start.assert_called_once()
