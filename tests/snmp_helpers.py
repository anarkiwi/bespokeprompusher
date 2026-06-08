from unittest.mock import MagicMock


def creds(community="testcomm"):
    m = MagicMock()
    m.get.return_value = community
    return m


def snmp_ok(value):
    r = MagicMock()
    r.returncode = 0
    r.stdout = f"iso.1.2.3 = INTEGER: {value}\n".encode()
    return r
