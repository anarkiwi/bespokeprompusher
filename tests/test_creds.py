import os
import tempfile

import pytest

from bespokeprompusher.creds import Creds


def _write_ini(content):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False) as f:
        f.write(content)
        return f.name


def test_reads_value():
    path = _write_ini("[snmp]\ndpdu_community = mycommunity\n")
    try:
        c = Creds(path)
        assert c.get("snmp", "dpdu_community") == "mycommunity"
    finally:
        os.unlink(path)


def test_raises_on_missing_file():
    with pytest.raises(SystemExit):
        Creds("/nonexistent/path/finfsecrets")


def test_interpolation_disabled():
    path = _write_ini("[section]\npassword = p%40ss\n")
    try:
        c = Creds(path)
        assert c.get("section", "password") == "p%40ss"
    finally:
        os.unlink(path)
