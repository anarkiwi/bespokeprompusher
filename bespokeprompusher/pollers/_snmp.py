import subprocess


def walk_int(host, oid, community, version="2c"):
    """snmpwalk a single OID; return the integer value on the last output line."""
    run = subprocess.run(
        ["snmpwalk", f"-v{version}", "-c", community, host, oid],
        capture_output=True,
        check=False,
        timeout=30,
    )
    if run.returncode != 0:
        raise RuntimeError(
            f"snmpwalk failed for {oid} on {host}: {run.stderr.decode().strip()}"
        )
    return int(run.stdout.decode().splitlines()[-1].split()[-1])
