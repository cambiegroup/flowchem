import requests  # type: ignore
from loguru import logger
from pydantic import AnyHttpUrl

from flowchem.client.component_client import FlowchemComponentClient
from flowchem.components.device_info import DeviceInfo


class FlowchemDeviceClient:
    def __init__(self, url: AnyHttpUrl) -> None:
        self.url = str(url)

        # Log every request and always raise for status
        self._session = requests.Session()
        self._session.hooks["response"] = [
            FlowchemDeviceClient.raise_for_status,
            FlowchemDeviceClient.log_responses,
        ]

        # Connect, get device info and populate components
        try:
            self.device_info = DeviceInfo.model_validate_json(
                self._session.get(self.url).text,
            )
        except ConnectionError as ce:
            msg = (
                f"Cannot connect to device at {url}!"
                f"This is likely caused by the server listening only on local the interface,"
                f"start flowchem with the --host 0.0.0.0 option to check if that's the problem!"
            )
            raise RuntimeError(msg) from ce
        self.components = {
            k: FlowchemComponentClient(v, parent=self)
            for k, v in self.device_info.components.items()
        }

    def __getitem__(self, item):
        """Get a device component by name or type."""
        if isinstance(item, type):
            return [
                component
                for component in self.components
                if isinstance(component, item)
            ]
        if isinstance(item, str):
            return self.components.get(item, None)
        return None

    # noinspection PyUnusedLocal
    @staticmethod
    def raise_for_status(resp, *args, **kwargs):  # noqa
        """Raise errors for status codes != 200 in session requests."""
        resp.raise_for_status()

    @staticmethod
    def log_responses(resp, *args, **kwargs):  # noqa
        """Log all the requests sent."""
        logger.debug(f"Reply: '{resp.text}' on {resp.url}")
