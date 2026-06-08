from unittest.mock import MagicMock, patch

import pytest

from bespokeprompusher.pollers._snmp import walk_int


def _result(returncode, out=b"", err=b""):
    r = MagicMock()
    r.returncode = returncode
    r.stdout = out
    r.stderr = err
    return r


def test_parses_integer_from_last_line():
    with patch("subprocess.run", return_value=_result(0, b"iso.1 = INTEGER: 42\n")):
        assert walk_int("h", "o", "c") == 42


def test_passes_version_and_community_to_snmpwalk():
    with patch("subprocess.run", return_value=_result(0, b"x = 1\n")) as mock_run:
        walk_int("host", "oid", "sekret", version="1")
    cmd = mock_run.call_args.args[0]
    assert "sekret" in cmd
    assert "-v1" in cmd


def test_raises_on_nonzero_returncode():
    with patch("subprocess.run", return_value=_result(1, err=b"timeout")):
        with pytest.raises(RuntimeError, match="snmpwalk failed"):
            walk_int("h", "o", "c")
