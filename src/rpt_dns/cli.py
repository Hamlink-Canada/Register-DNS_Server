"""Serve DNS over TCP and UDP and stop cleanly on SIGTERM."""

import logging
import signal
import socketserver
import time
from struct import pack, unpack
from threading import BoundedSemaphore, Thread

from .config import load_settings
from .directory import Directory
from .dns import respond
from .messagebus import MessageBus


def read_exact(sock, size):
    data = bytearray()
    while len(data) < size:
        chunk = sock.recv(size - len(data))
        if not chunk:
            raise ValueError("truncated DNS frame")
        data.extend(chunk)
    return bytes(data)


class UDPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, sock = self.request
        response = respond(data, self.server.directory, self.server.domain)
        if response:
            sock.sendto(response, self.client_address)


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(2)
        try:
            size = unpack("!H", read_exact(self.request, 2))[0]
            response = respond(
                read_exact(self.request, size), self.server.directory, self.server.domain
            )
            if response:
                self.request.sendall(pack("!H", len(response)) + response)
        except (OSError, ValueError):
            pass


class BoundedServer(socketserver.ThreadingMixIn):
    daemon_threads = True
    allow_reuse_address = True

    def process_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


class UDPServer(BoundedServer, socketserver.UDPServer):
    pass


class TCPServer(BoundedServer, socketserver.TCPServer):
    pass


def main():
    settings = load_settings()
    logging.basicConfig(level=logging.INFO)
    directory = Directory(settings.CACHE_SIZE, settings.MAX_LIFETIME, settings.CLOCK_SKEW)
    bus = MessageBus(settings, directory)
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    servers, threads = [], []
    try:
        for cls, handler in ((UDPServer, UDPHandler), (TCPServer, TCPHandler)):
            server = cls((settings.HOST, int(settings.PORT)), handler)
            server.directory, server.domain = directory, settings.DOMAIN
            server.slots = BoundedSemaphore(int(settings.WORKERS))
            servers.append(server)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            threads.append(thread)
        thread = Thread(target=bus.serve, daemon=True)
        thread.start()
        threads.append(thread)
        while not stopped:
            time.sleep(0.2)
    finally:
        bus.stopped.set()
        for server in servers:
            server.shutdown()
            server.server_close()
        for thread in threads:
            thread.join(timeout=3)
