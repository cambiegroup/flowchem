import requests
from loguru import logger
from pydantic import AnyHttpUrl

from flowchem.client.component_client import FlowchemComponentClient
from flowchem.components.device_info import DeviceInfo


class FlowchemDeviceClient:
    def __init__(self, url: AnyHttpUrl):
        self.url = url

        # Log every request and always raise for status
        self._session = requests.Session()
        self._session.hooks["response"] = [
            FlowchemDeviceClient.log_responses,
            FlowchemDeviceClient.raise_for_status,
        ]

        # Connect, get device info and populate components
        try:
            self.device_info = DeviceInfo.model_validate_json(
                self._session.get(self.url).text
            )
        except ConnectionError as ce:
            raise RuntimeError(
                f"Cannot connect to device at {url}!"
                f"This is likely caused by the server listening only on local the interface,"
                f"start flowchem with the --host 0.0.0.0 option to check if that's the problem!"
            ) from ce
        self.components = [
            FlowchemComponentClient(cmp_url, parent=self)
            for cmp_url in self.device_info.components
        ]

    @staticmethod
    def raise_for_status(resp, *args, **kwargs):
        resp.raise_for_status()

    @staticmethod
    def log_responses(resp, *args, **kwargs):
        logger.debug(f"Reply: {resp.text} on {resp.url}")
