import contextlib

import requests
from loguru import logger

HOST = "127.0.0.1"
PORT = 8000
api_base = f"http://{HOST}:{PORT}"
socl2_endpoint = f"{api_base}/socl2"
hexyldecanoic_endpoint = f"{api_base}/hexyldecanoic"
r4_channel = 0
r4_endpoint = f"{api_base}/r4-heater/{r4_channel}"
flowir_endpoint = f"{api_base}/flowir"

__all__ = ["socl2_endpoint", "hexyldecanoic_endpoint", "r4_endpoint", "command_session", "flowir_endpoint"]


def check_for_errors(resp, *args, **kwargs):
    resp.raise_for_status()


def log_responses(resp, *args, **kwargs):
    logger.debug(f"Reply: {resp.text} on {resp.url}")


@contextlib.contextmanager
def command_session():
    with requests.Session() as session:
        session.hooks["response"] = [log_responses, check_for_errors]
        yield session
