#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Python KISS Module Class Definitions."""

import socket
from lib.helper import debug
from lib.decorators import dumpArgs

from pykiss.kiss import Kiss
from kiss import BUFSIZE

# --------------------------------------------------------------------------------------------------------------------
class TcpKiss(Kiss):
    """Kiss over TCP Class"""

    def __init__(self, host=None, port=0,
                 timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        """TcpKiss Constructor.

        When called without arguments, create an unconnected instance.
        With a hostname argument, it connects the instance; port number and timeout are optional.
        """
        super().__init__()
        self.host = host
        self.port = port
        self.sock = None
        self._write_handler = None
        if host is not None:
            self.open(host, port, timeout)

    def _read_handler(self, bufsize=None):
        """Read handler.
        :param bufsize: The maximum amount of data to be received at once.
        :returns: The data read from the socket
        """
        bufsize = bufsize or BUFSIZE
        read_data = self.sock.recv(bufsize)
        # print(read_data.hex())
        return read_data

    def close(self):
        """Close the connection."""
        sock = self.sock
        self.sock = None
        if sock:
            sock.close()

    def open(self, host, port, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
        """
        Initializes the KISS device and commits configuration.
        """

        self.host = host
        self.port = port
        self.sock = socket.create_connection((self.host, self.port), timeout)
        self._write_handler = self.sock.send


# --------------------------------------------------------------------------------------------------------------------
# Simple callback function. Just print the data...
def p(frames):
    for frame in frames:
        # print(frame)  # prints whatever is passed in.
        print(f"In p(): {frame=}")


# --------------------------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    """The main of this module will perform some tests"""


    import lib.helper
    lib.helper.clear_debug_window()

    with TcpKiss("192.168.0.31", 7342) as tcp:
        tcp.write_command(b"TNC:")  # Ask for the FLDigi version number
        tcp.read(callback=p)
        tcp.write_command(b"MODEML:")   # Ask for list of supported modems (modes)
        tcp.read(callback=p)
        tcp.write_command(b"MODEM: MODEMBW: KISSCRCM:")   # Ask for current modem information
        tcp.read(callback=p)
        tcp.write_command(b"RSIDBCAST:ON TRXSBCAST:ON TXBEBCAST:ON")    # Set parameters
        tcp.read(callback=p)
        tcp.write_command(b"KISSRAW:ON")
        tcp.read(callback=p)
        while True:
            tcp.read(callback=p)
