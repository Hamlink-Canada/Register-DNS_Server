#!/usr/bin/env python3
from apprptdns.servers import ThreadedTCPServer, ThreadedUDPServer
from apprptdns.handlers import TCPRequestHandler, UDPRequestHandler
from apprptdns.messagebus import MessageBusServer
import threading
import time
import sys

port = 5053

if __name__ == '__main__':
    servers = []
    servers.append(ThreadedUDPServer(('', port), UDPRequestHandler))
    servers.append(ThreadedTCPServer(('', port), TCPRequestHandler))
    servers.append(MessageBusServer())

    for s in servers:
        thread = threading.Thread(target=s.serve_forever)  # that thread will start one more thread for each request
        thread.daemon = True  # exit the server thread when the main thread terminates
        thread.start()
        if hasattr(s, "RequestHandlerClass"):
            print("%s server loop running in thread: %s" % (s.RequestHandlerClass.__name__[:3], thread.name))

    try:
        while 1:
            time.sleep(1)
            sys.stderr.flush()
            sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        for s in servers:
            s.shutdown()
