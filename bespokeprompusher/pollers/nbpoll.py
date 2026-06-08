import logging

from bespokeprompusher.pollers._snmp import walk_int

log = logging.getLogger(__name__)

# Ubiquiti nanobridge backhaul stations. Each is its own SNMP host; the OIDs
# are the 64-bit interface octet counters for the radio interface (ifIndex 4).
STATIONS_DEFAULT = ("birdsong-nb", "gnd-nb")
VARS = {
    "nbifInOct": "iso.3.6.1.2.1.31.1.1.1.6.4",
    "nbifOutOct": "iso.3.6.1.2.1.31.1.1.1.10.4",
}


def poll(config, creds):
    community = creds.get("snmp", "nb_community")
    stations = config.get("stations", STATIONS_DEFAULT)
    results = []
    for station in stations:
        try:
            station_metrics = [
                (f'{var}{{station="{station}"}}', walk_int(station, oid, community))
                for var, oid in VARS.items()
            ]
        except Exception as e:  # a single down station must not drop the rest
            log.warning("nbpoll: skipping %s: %s", station, e)
            continue
        results.extend(station_metrics)
    return results
