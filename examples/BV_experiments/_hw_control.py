import contextlib

import requests
from loguru import logger

HOST = "127.0.0.1"
PORT = 8000

api_base = f"http://{HOST}:{PORT}"
eosinY_endpoint = f"{api_base}/eosin"
activator_endpoint = f"{api_base}/activator"
quencher_endpoint = f"{api_base}/quencher"
solvent_endpoint = f"{api_base}/solvent"
SMIS_endpoint = f"{api_base}/smis"

bubble_sensor_measure_endpoint = f"{api_base}/bubble-sensor-measure"
bubble_sensor_power_endpoint = f"{api_base}/bubble-sensor-power"

MFC_endpoint = f"{api_base}/MFC"
r2_endpoint = f"{api_base}/r2"
# pumpM_endpoint = f"{api_base}/Knauer-pumpM"
collector_endpoint = f"{api_base}/Collector"

# analytic devices
# hplc_endpoint = f"{api_base}/hplc"

__all__ = [
    "eosinY_endpoint",
    "activator_endpoint",
    "quencher_endpoint",
    "solvent_endpoint",
    "SMIS_endpoint",
    "bubble_sensor_measure_endpoint",
    "bubble_sensor_power_endpoint",
    "MFC_endpoint",
    "r2_endpoint",
    "collector_endpoint",
    # "pumpM_endpoint",
    # "hplc_endpoint",
]


def check_for_errors(resp, *args, **kwargs):
    resp.raise_for_status()


def log_responses(resp, *args, **kwargs):
    logger.debug(f"Reply: {resp.text} on {resp.url}")


@contextlib.contextmanager  #decorator: add __enter__ and __exit__
def command_session():
    with requests.Session() as session:
        session.hooks["response"] = [log_responses, check_for_errors]
        yield session
