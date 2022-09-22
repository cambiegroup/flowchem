import contextlib

import requests
from loguru import logger


def check_for_errors(resp, *args, **kwargs):
    resp.raise_for_status()


def log_responses(resp, *args, **kwargs):
    logger.debug(resp.text)


@contextlib.contextmanager
def command_session():
    with requests.Session() as session:
        session.hooks["response"] = [log_responses, check_for_errors]
        yield session
