""" Functions related to instrument reply parsing """

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
    FINISHING = (
        4  # Upon <State status="Ready", scan acquisition over, not saving/processing
    )
    COMPLETED = 5  # Upon <Completed>, means also processing/saving data is over
    ERROR = 6  # If an error occurs
    UNKNOWN = 7


# def extract_error(xml_message: etree._Element) -> str:
#     """
#     Search for an error tag in the XML tree provided.
#     If an error is found returns its error message, empty string if no errors are present.
#     """
#     error = xml_message.find(".//Error")
#     return error.get("error") if error is not None else ""


def parse_status_notification(xml_message: etree.Element):
    """
    Parse a status notification reply.
    """
    status = xml_message.find(".//StatusNotification")

    # No status notification found
    if status is None:
        warnings.warn(
            "Parse status notification called on a message with no StatusNotification tags!"
        )
        return None

    # StatusNotification child can be <State> (w/ submsg). <Progress>, <Completed> or <Error>
    child = status[0]

    if child.tag == "State":
        return parse_state(child)

    if child.tag == "Progress":
        return StatusNotification.RUNNING, None

    if child.tag == "Completed":
        return StatusNotification.COMPLETED, None

    if child.tag == "Error":
        return StatusNotification.ERROR, None

    warnings.warn("Could not detect StatusNotification state!")
    return StatusNotification.UNKNOWN, None


def parse_state(xml_message: etree.Element):
    """Parse state message"""
    status_type = StatusNotification.UNKNOWN

    # Parse status
    status = xml_message.get("status")
    if status == "Running":
        status_type = StatusNotification.STARTED
    elif status == "Ready":
        status_type = StatusNotification.FINISHING
    elif status == "Stopping":
        status_type = StatusNotification.STOPPING
    else:
        warnings.warn(f"Unidentified notification status: {status}")

    # Full path is only available on experiment, so often this string is empty
    remote_folder = xml_message.get("dataFolder")

    if remote_folder:
        return status_type, remote_folder
    else:
        return status_type, None
