from typing import TYPE_CHECKING

from loguru import logger
from pydantic import AnyHttpUrl

if TYPE_CHECKING:
    from flowchem.client.device_client import FlowchemDeviceClient
from flowchem.components.component_info import ComponentInfo


class FlowchemComponentClient:
    def __init__(self, url: AnyHttpUrl, parent: "FlowchemDeviceClient"):
        self.url = url
        # Get ComponentInfo from
        logger.warning(f"CREATE COMPONENT FOR URL {url}")
        self._parent = parent
        self._session = self._parent._session
        self.component_info = ComponentInfo.model_validate_json(self.get(url).text)

    def get(self, url, **kwargs):
        """Sends a GET request. Returns :class:`Response` object."""
        return self._session.get(url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        """Sends a POST request. Returns :class:`Response` object."""
        return self._session.post(url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        """Sends a PUT request. Returns :class:`Response` object."""
        return self._session.put(url, data=data, **kwargs)
