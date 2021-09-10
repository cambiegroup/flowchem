""" Functions related to the construction of instrument request """

import warnings
from pathlib import WindowsPath

from lxml import etree


def create_message(sub_element_name, attributes=None):
    """
    Create a minimal XML tree with Message as root and sub_element as child tag
    """
    if attributes is None:
        attributes = {}

    root = etree.Element("Message")
    etree.SubElement(root, sub_element_name, attributes)
    return root


def set_attribute(name, value="") -> etree._Element:
    """
    Creates a Set message.
    Used for name = {Solvent | Sample} + indirectly by UserData and DataFolder
    """
    base = create_message("Set")
    attribute = etree.SubElement(base.find("./Set"), name)
    attribute.text = value
    return base


def get_request(name) -> etree._Element:
    """
    Creates a Get message.
    Used for name = {Solvent | Sample | UserData} + indirectly by UserData and DataFolder
    """
    base = create_message("GetRequest")
    attribute = etree.SubElement(base.find("./GetRequest"), name)
    return base


def set_data_folder(location, folder_type="TimeStampTree") -> etree._Element:
    """
    Create a Set DataFolder message
    """
    # Validate folder_type
    if folder_type not in ("TimeStampTree", "TimeStamp", "UserFolder"):
        warnings.warn("Invalid data folder type! Assuming TimeStampTree.")
        folder_type = "TimeStampTree"

    # Get base request
    data_folder = set_attribute("DataFolder")

    # Add folder specific tag
    full_tree = etree.SubElement(data_folder.find(".//DataFolder"), folder_type)
    full_tree.text = location.as_posix() if isinstance(location, WindowsPath) else location

    return data_folder


def set_user_data(data: dict) -> etree._Element:
    """
    Given a dict with custom data, it creates a Set/UserData message.
    Those data are saved in acq.par
    """
    user_data = set_attribute("UserData")
    for key, value in data.items():
        etree.SubElement(user_data.find(".//UserData"), "Data", dict(key=key, value=value))
    return user_data


def create_protocol_message(protocol_name: str, protocol_options: dict) -> etree._Element:
    """
    Create an XML request to run a protocol
    """
    xml_root = create_message("Start", {"protocol": protocol_name})

    start_tag = xml_root.find("Start")

    for key, value in protocol_options.items():
        # All options are SubElements of the Start tag!
        etree.SubElement(start_tag, "Option", {"name": f"{key}", "value": f"{value}"})

    return xml_root
