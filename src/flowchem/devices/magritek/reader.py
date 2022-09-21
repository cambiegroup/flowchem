"""Connection reader + XML parser for Spinsolve replies."""
from __future__ import annotations  # Still used for deferred evaluation of hints, PEP 563

import queue
import time
import warnings

from lxml import etree

from .utils import get_my_docs_path


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
        self._replies: list[etree.Element] = []
        self._rcv_buffer = b""

    def wait_for_reply(self, reply_type="", timeout=1):
        """
        Awaits for a reply of type reply_type or up to timeout
        """
        reply = self.get_next_reply(reply_type)

        # If already available just return
        if reply is not None:
            return reply

        # This is ugly, but usually unnecessary as replies are received immediately.
        # Only relevant if controlling remote devices over connections with significant latency
        start_time = time.time()
        while reply is None and time.time() < (start_time + timeout):
            reply = self.get_next_reply(reply_type)
            time.sleep(0.1)

        if reply is None:
            raise RuntimeError("No reply received from device!")

        return reply

    def get_next_reply(self, reply_type=""):
        """
        Returns the next reply of given type in self._replies.
        """
        self.fetch_replies()

        valid_replies = [
            reply for reply in self._replies if reply[0].tag.endswith(reply_type)
        ]

        if len(valid_replies) > 0:
            first_valid_reply = valid_replies[0]
            self._replies.remove(first_valid_reply)
            return first_valid_reply

    def clear_replies(self, reply_type=""):
        """Remove old replies."""
        # Shortcut if none provided...
        if not reply_type:
            self._replies.clear()

        # Otherwise, check type
        for reply in self._replies:
            if reply[0].tag.endswith(reply_type):
                self._replies.remove(reply)

    def fetch_replies(self):
        """
        Fetch the unprocessed chunks from the queue and adds them to the reception buffer
        """
        while not self._queue.empty():
            # From queue only complete replies thanks to read until(b"</Message>")
            tree = self.parse_tree(self._queue.get())
            self._queue.task_done()

            if tree:
                self._replies.append(tree)

            if tree and self.schema:
                self.validate_tree(tree)

    def parse_tree(self, tree_string) -> etree.Element | None:
        """Parse an XML reply tree, add it to the replies and validate it (if the schema is available)."""

        try:
            return etree.fromstring(tree_string, self.parser)
        except etree.XMLSyntaxError:
            warnings.warn(f"Cannot parse response XML {tree_string}")
            return None

    def validate_tree(self, tree: etree.Element):
        """Validate the XML tree against the schema."""

        try:
            self.schema.validate(tree)
        except etree.XMLSyntaxError as syntax_error:
            warnings.warn(f"Invalid XML received! [Validation error: {syntax_error}]")
