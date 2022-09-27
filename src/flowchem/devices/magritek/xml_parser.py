"""Functions related to instrument response parsing."""
import warnings
from enum import Enum

from lxml import etree


class StatusNotification(Enum):
    """
    Represent the type of the status notification
    """

    STARTED = 1  # <State status="Ready"> received, starting protocol
    RUNNING = 2  # All good, <Progress> received, protocol is running
    STOPPING = 3  # Abort called, waiting for current scan end
    FINISHING = 4  # Upon <State status="Ready": acquisition over, processing ongoing
    COMPLETED = 5  # Upon <Completed>: with this also processing/saving data is over
    ERROR = 6  # If an error occurs
    UNKNOWN = 7


def parse_status_notification(xml_message: etree.Element):
    """Parse a status notification reply."""
    status = xml_message.find(".//StatusNotification")
    assert status is not None, "a StatusNotification tree is needed for parsing"

    # StatusNotification child can be <State> (w/ submsg), <Progress>, <Completed> or <Error>
    child = status[0]

    match child.tag:
        case "State":
            return parse_state(child)
        case "Progress":
            return StatusNotification.RUNNING, None
        case "Completed":
            return StatusNotification.COMPLETED, None
        case "Error":
            return StatusNotification.ERROR, None
        case _:
            warnings.warn("Could not detect StatusNotification state!")
            return StatusNotification.UNKNOWN, None


def parse_state(xml_message: etree.Element):
    """Parse state message"""
    match status := xml_message.get("status"):
        case "Running":
            status_type = StatusNotification.STARTED
        case "Ready":
            status_type = StatusNotification.FINISHING
        case "Stopping":
            status_type = StatusNotification.STOPPING
        case _:
            status_type = StatusNotification.UNKNOWN
            warnings.warn(f"Unidentified notification status: {status}")

    # dataFolder only present at experiment end, generally None
    return status_type, xml_message.get("dataFolder")
