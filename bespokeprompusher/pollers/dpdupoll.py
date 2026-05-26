import subprocess

DPDU_DEFAULT = "dpdu.finf"
VARS = {
    "rPDUPhaseStatusVoltage": "iso.3.6.1.4.1.674.10903.200.2.200.120.2.1.5.1",
    "rPDUPhaseStatusCurrent": "iso.3.6.1.4.1.674.10903.200.2.200.120.2.1.4.1",
}
SCALE = {"rPDUPhaseStatusCurrent": 0.1}


def poll(config, creds):
    host = config.get("host", DPDU_DEFAULT)
    community = creds.get("snmp", "dpdu_community")
    results = []
    for var, oid in VARS.items():
        run = subprocess.run(
            ["snmpwalk", "-v1", "-c", community, host, oid],
            capture_output=True,
            timeout=30,
        )
        if run.returncode != 0:
            raise RuntimeError(
                f"snmpwalk failed for {var}: {run.stderr.decode().strip()}"
            )
        line = run.stdout.decode().splitlines()[-1]
        result = int(line.split()[-1])
        if var in SCALE:
            result *= SCALE[var]
        results.append((var, result))
    return results
