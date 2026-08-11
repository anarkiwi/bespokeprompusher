import logging

from bespokeprompusher.pollers._snmp import walk_int

log = logging.getLogger(__name__)

# Ubiquiti nanobridge backhaul stations, one SNMP host each.
STATIONS_DEFAULT = ("gnd-nb",)
# ath0 ifHCIn/OutOctets undercount bridged traffic ~170x here; use UBNT-AFLTU-MIB.
VARS = {
    "nbRxBytes": "iso.3.6.1.4.1.41112.1.10.1.5.3.0",
    "nbTxBytes": "iso.3.6.1.4.1.41112.1.10.1.5.1.0",
    "nbRxPps": "iso.3.6.1.4.1.41112.1.10.1.5.4.0",
    "nbTxPps": "iso.3.6.1.4.1.41112.1.10.1.5.2.0",
    "nbChain0Signal": "iso.3.6.1.4.1.41112.1.10.1.4.1.5",
    "nbChain1Signal": "iso.3.6.1.4.1.41112.1.10.1.4.1.6",
    "nbChain0LinkPotential": "iso.3.6.1.4.1.41112.1.10.1.4.1.9",
    "nbChain1LinkPotential": "iso.3.6.1.4.1.41112.1.10.1.4.1.10",
    "nbTxCapacityKbps": "iso.3.6.1.4.1.41112.1.10.1.4.1.3",
    "nbRxCapacityKbps": "iso.3.6.1.4.1.41112.1.10.1.4.1.4",
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
