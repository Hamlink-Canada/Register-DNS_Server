"""Request handlers for TCP and UDP DNS queries.

These classes adapt the standard library `socketserver` handlers to the
project's `dns_response` function which returns a packed DNS reply.
"""

import socketserver
import datetime
import struct
import sys
import traceback
import logging
from apprptdns.dns import dns_response


class BaseRequestHandler(socketserver.BaseRequestHandler):
    """Base handler that delegates parsing and responding to `dns_response()`.

    Subclasses must implement `get_data()` and `send_data()` to handle the
    transport specifics (TCP/UDP).
    """

    def get_data(self):
        raise NotImplementedError

    def send_data(self, data):
        raise NotImplementedError

    def handle(self):
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        logging.debug("\n\n%s request %s (%s %s):" % (self.__class__.__name__[:3], now, self.client_address[0],
                                               self.client_address[1]))
        try:
            data = self.get_data()
            response = dns_response(data)
            if response:
                # `send_data` is transport-specific in subclasses
                self.send_data(response)
        except Exception:
            logging.error("Error handling request")
            traceback.print_exc(file=sys.stderr)


class TCPRequestHandler(BaseRequestHandler):
    """Handle DNS over TCP.

    TCP DNS frames include a two-byte length prefix; validate the size
    and strip the prefix before passing the packet to `dns_response()`.
    """

    def get_data(self):
        data = self.request.recv(8192).strip()
        # first two bytes are the length in network byte order
        sz = struct.unpack('>H', data[:2])[0]
        if sz < len(data) - 2:
            raise Exception("Wrong size of TCP packet")
        elif sz > len(data) - 2:
            raise Exception("Too big TCP packet")
        return data[2:]

    def send_data(self, data):
        sz = struct.pack('>H', len(data))
        return self.request.sendall(sz + data)


class UDPRequestHandler(BaseRequestHandler):
    """Handle DNS over UDP."""

    def get_data(self):
        # `self.request` for UDP is a (data, socket) tuple
        return self.request[0].strip()

    def send_data(self, data):
        return self.request[1].sendto(data, self.client_address)