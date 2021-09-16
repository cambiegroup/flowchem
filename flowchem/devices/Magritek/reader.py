""" Connection reader + XML parser for Spinsolve replies """

import time
import warnings
import queue
from typing import List

from lxml import etree

from flowchem.devices.Magritek.utils import get_my_docs_path


class Reader:
    """
    This class is responsible for collecting and parsing replies from the spectrometer.
    It does not contain functionality to handle I/O.
    """

    def __init__(self, reply_queue: queue.Queue, xml_schema=None):
        self._queue = reply_queue

        if xml_schema is None:
            # This is the default location upon Spinsolve installation. However, remote control can be from remote ;)
            my_docs = get_my_docs_path()
            try:
                self.schema = etree.XMLSchema(
                    file=str(my_docs / "Magritek" / "Spinsolve" / "RemoteControl.xsd")
                )
            except etree.XMLSchemaParseError:  # i.e. not found
                self.schema = None
        else:
            self.schema = xml_schema

        self.parser = etree.XMLParser()
        self._replies: List[etree.Element] = []
        self._rcv_buffer = b""

    def wait_for_reply(self, reply_type="", remove=True, timeout=1):
        """
        Awaits for a reply of type reply_type or up to timeout
        """
        reply = self.get_last_reply(reply_type, remove)

        # If already available just return
        if reply is not None:
            return reply

        # This is ugly, but usually unnecessary as replies are received immediately.
        # Only relevant if controlling remote devices over connections with significant latency
        start_time = time.time()
        while reply is None and time.time() < (start_time + timeout):
            reply = self.get_last_reply(reply_type)
            time.sleep(0.5)

        if reply is None:
            raise RuntimeError("No reply received from device!")

        return reply

    def get_last_reply(self, reply_type="", remove=True):
        """
        Returns the last reply of given type
        """
        self.fetch_replies()

        for reply in reversed(self._replies):
            # First tag in message is response type
            if reply[0].tag.endswith(reply_type):
                if remove:
                    self._replies.remove(
                        reply
                    )  # yes, I am also surprised that this is possible ;)
                return reply

    def clear_replies(self, reply_type=""):
        """ Remove old replies. """
        # Shortcut if none provided
        if not reply_type:
            self._replies.clear()

        # Otherwise check type
        for reply in self._replies:
            if reply[0].tag.endswith(reply_type):
                self._replies.remove(reply)

    def fetch_replies(self):
        """
        Fetch the unprocessed chunks from the queue and adds them to the receive buffer
        """
        while not self._queue.empty():
            self._rcv_buffer += self._queue.get()
            self._queue.task_done()

        self.parse_buffer()

    def parse_buffer(self) -> bool:
        """
        Split then buffer into individual XML trees and parse them.
        """

        # Split buffer at each declaration to separate different trees
        declaration = b'<?xml version="1.0" encoding="utf-8"?>'
        trees = self._rcv_buffer.split(declaration)

        # Parse trees. (Buffer always starts with declaration, so split gives a tree[0] = b"" element that we skip
        for tree in trees[1:]:
            self.parse_tree(tree)

        # Clear buffer
        self._rcv_buffer = b""

    def parse_tree(self, tree_string):
        """
        Parse an XML reply tree, add it to the replies and validate it (if the schema is available).
        """

        # Parse
        try:
            root = etree.fromstring(tree_string, self.parser)
        except etree.XMLSyntaxError:
            warnings.warn(f"Cannot parse response XML {tree_string}")
            return None

        # Add tree to replies
        self._replies.append(root)

        # Validate
        if self.schema:
            try:
                self.schema.validate(root)
            except etree.XMLSyntaxError as e:
                warnings.warn(f"Invalid XML received! [Validation error: {e}]")
