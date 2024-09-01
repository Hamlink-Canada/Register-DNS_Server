#!/usr/bin/env python3
import socketserver

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, *args, **kwargs):
        socketserver.UDPServer.__init__(self, *args, **kwargs)

class ThreadedUDPServer(socketserver.ThreadingMixIn, socketserver.UDPServer):
    def __init__(self, *args, **kwargs):
        socketserver.UDPServer.__init__(self, *args, **kwargs)

