""" Functions related to instrument reply parsing """

import warnings

from lxml import etree
from enum import Enum


class StatusNotification(Enum):
    """
    Represent the type of the status notification
    """
    STARTED = 1  # <State status="Ready"> received, starting protocol
    RUNNING = 2  # All good, <Progress> received, protocol is running
    STOPPING = 3  # Abort called, waiting for current scan end
    FINISHING = 4  # Upon <State status="Ready", scan acquisition over, not saving/processing
    COMPLETED = 5  # Upon <Completed>, means also processing/saving data is over
    ERROR = 6  # If an error occurs
    UNKNOWN = 7


def extract_error(xml_message: etree._Element) -> str:
    """
    Search for an error tag in the XML tree provided.
    If an error is found returns its error message, empty string if no errors are present.
    """
    error = xml_message.find(".//Error")
    return error.get("error") if error is not None else ""


def parse_status_notification(xml_message: etree._Element):
    """
    Parse a status notification reply.
    """
    status = xml_message.find(".//StatusNotification")
    remote_folder = None
    status_type = StatusNotification.UNKNOWN

    # No status notification found
    if status is None:
        warnings.warn("Parse status notification called on a message with no StatusNotification tags!")
        return None

    # First (only) child of StatusNotification can be <State> <Progress> or <Completed>
    child = status[0]

    if child.tag == "State":
        status = child.get("status")

        # Set status
        if status == "Running":
            status_type = StatusNotification.STARTED
        elif status == "Ready":
            status_type = StatusNotification.FINISHING
        elif status == "Stopping":
            status_type = StatusNotification.STOPPING
        else:
            warnings.warn(f"Unidentified notification status: {status}")

        # Full path only shown on experiment end, thus Ready and Stopping
        if status in ("Ready", "Stopping"):
            remote_folder = child.get("dataFolder")

    elif child.tag == "Progress":
        status_type = StatusNotification.RUNNING

    elif child.tag == "Completed":
        status_type = StatusNotification.COMPLETED

    elif child.tag == "Error":
        status_type = StatusNotification.ERROR

    if status_type is StatusNotification.UNKNOWN:
        warnings.warn("Could not detect StatusNotification state!")

    return status_type, remote_folder
