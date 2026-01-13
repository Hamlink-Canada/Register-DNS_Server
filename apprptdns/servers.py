#!/usr/bin/env python3
"""Thin wrappers providing threaded TCP/UDP servers.

Note: The original `ThreadedTCPServer.__init__` called
`socketserver.UDPServer.__init__` which looks like an implementation bug.
The classes below inherit the intended base class constructors.
"""

import socketserver


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Threading TCP server combining mixin and TCPServer."""


class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    """Threading UDP server combining mixin and UDPServer."""

