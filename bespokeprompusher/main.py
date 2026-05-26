import importlib
import logging
import os
import threading
import time

import requests
import yaml

from bespokeprompusher.creds import Creds

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
log = logging.getLogger(__name__)


def push(pushgateway, job, instance, metrics):
    url = f"{pushgateway}/metrics/job/{job}/instance/{instance}"
    body = "".join(f"{name} {value}\n" for name, value in metrics)
    try:
        resp = requests.post(url, data=body.encode(), timeout=30)
        resp.raise_for_status()
    except Exception as e:
        log.error("push failed for %s/%s: %s", job, instance, e)


def make_poller(task_cfg, pushgateway, creds):
    mod = importlib.import_module(
        f"bespokeprompusher.pollers.{task_cfg['poller']}"
    )
    job = task_cfg["job"]
    instance = task_cfg["instance"]
    extra = task_cfg.get("config", {})
    name = task_cfg["name"]

    def run():
        metrics = mod.poll(extra, creds)
        if metrics:
            push(pushgateway, job, instance, metrics)
            log.info("pushed %d metrics for %s/%s", len(metrics), job, instance)
        else:
            log.debug("no metrics from %s", name)

    return run


def loop(fn, name, interval_seconds):
    while True:
        try:
            fn()
        except Exception as e:
            log.error("task %s error: %s", name, e)
        time.sleep(interval_seconds)


def main():
    config_path = os.environ.get("CONFIG_FILE", "/config/bespokeprompusher.yaml")
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    secrets_path = cfg.get(
        "secrets_file",
        os.environ.get("SECRETS_FILE", "/secrets/finfsecrets"),
    )
    creds = Creds(secrets_path)
    pushgateway = cfg["pushgateway"]

    for task in cfg["tasks"]:
        fn = make_poller(task, pushgateway, creds)
        name = task["name"]
        interval = task["interval_seconds"]
        log.info("starting task %s every %ds", name, interval)
        t = threading.Thread(target=loop, args=(fn, name, interval), daemon=True)
        t.start()

    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
