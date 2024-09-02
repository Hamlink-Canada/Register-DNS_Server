#!/usr/bin/env python3
from apprptdns.servers import ThreadedTCPServer, ThreadedUDPServer
from apprptdns.handlers import TCPRequestHandler, UDPRequestHandler
from apprptdns.messagebus import MessageBusServer
from apprptdns.config import config
from apprptdns.cache import cache
import threading
import time
import sys
import logging

logging.basicConfig(
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M",
    level=logging.INFO,
 )

if __name__ == '__main__':
    config.read('config.ini')
    cache.setupCache()
    port = int(config['dns']['port'])
    servers = []
    servers.append(ThreadedUDPServer(('', port), UDPRequestHandler))
    servers.append(ThreadedTCPServer(('', port), TCPRequestHandler))
    servers.append(MessageBusServer(cache))

    for s in servers:
        thread = threading.Thread(target=s.serve_forever)  # that thread will start one more thread for each request
        thread.daemon = True  # exit the server thread when the main thread terminates
        thread.start()
        if hasattr(s, "RequestHandlerClass"):
            logging.info("%s server loop running in thread: %s" % (s.RequestHandlerClass.__name__[:3], thread.name))

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
