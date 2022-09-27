"""Functions for the construction of XML requests for Spinsolve."""
from pathlib import WindowsPath

from lxml import etree


def create_message(sub_element_name, attributes=None):
    """Create a minimal XML tree with Message as root and sub_element as child tag."""
    if attributes is None:
        attributes = {}

    root = etree.Element("Message")
    etree.SubElement(root, sub_element_name, attributes)
    return root


def set_attribute(name, value="") -> etree.Element:
    """Creates a Set message.

    Used for name = {Solvent | Sample} + indirectly by UserData and DataFolder."""
    base = create_message("Set")
    attribute = etree.SubElement(base.find("./Set"), name)
    attribute.text = value
    return base


def get_request(name) -> etree.Element:
    """Creates a Get message.

    Used for name = {Solvent | Sample | UserData} + indirectly by UserData and DataFolder."""
    base = create_message("GetRequest")
    etree.SubElement(base.find("./GetRequest"), name)
    return base


def set_data_folder(location) -> etree.Element:
    """Create a Set DataFolder message."""
    # Get base request
    data_folder = set_attribute("DataFolder")

    # Add folder specific tag
    full_tree = etree.SubElement(data_folder.find(".//DataFolder"), "TimeStampTree")
    full_tree.text = (
        location.as_posix() if isinstance(location, WindowsPath) else location
    )

    return data_folder


def create_protocol_message(name: str, options: dict) -> etree.Element:
    """Create an XML request to run a protocol."""
    xml_root = create_message("Start", {"protocol": name})
    start_tag = xml_root.find("Start")

    # All options are sent as Start tag SubElements
    for key, value in options.items():
        etree.SubElement(start_tag, "Option", {"name": f"{key}", "value": f"{value}"})

    return xml_root
