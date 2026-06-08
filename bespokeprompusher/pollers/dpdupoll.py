from bespokeprompusher.pollers._snmp import walk_int

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
        result = walk_int(host, oid, community, version="1")
        if var in SCALE:
            result *= SCALE[var]
        results.append((var, result))
    return results
