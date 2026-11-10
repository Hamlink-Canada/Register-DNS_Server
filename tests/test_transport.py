import socket
from struct import pack, unpack
from threading import BoundedSemaphore, Thread

from dnslib import DNSRecord
from rpt_protobuf.dns_update_pb2 import dns_update

from rpt_dns.cli import TCPHandler, TCPServer, UDPHandler, UDPServer, read_exact
from rpt_dns.directory import Directory


def test_dns_tcp_and_udp():
    import time

    directory = Directory()
    entry = dns_update()
    entry.timestamp.seconds = int(time.time())
    entry.node.id, entry.node.ipaddress = 1234, "192.0.2.1"
    entry.node.port, entry.node.ttl, entry.node.server = 4569, 180, "test"
    assert directory.ingest(entry.SerializeToString())
    query = DNSRecord.question("1234.nodes.example.org", "A").pack()
    for cls, handler, kind in [
        (TCPServer, TCPHandler, socket.SOCK_STREAM),
        (UDPServer, UDPHandler, socket.SOCK_DGRAM),
    ]:
        with cls(("127.0.0.1", 0), handler) as server:
            server.directory, server.domain = directory, "nodes.example.org"
            server.slots = BoundedSemaphore(2)
            thread = Thread(target=server.serve_forever)
            thread.start()
            try:
                with socket.socket(socket.AF_INET, kind) as sock:
                    sock.settimeout(2)
                    sock.connect(server.server_address)
                    if kind == socket.SOCK_STREAM:
                        frame = pack("!H", len(query)) + query
                        # TCP is a byte stream; framing cannot depend on one recv call.
                        sock.sendall(frame[:1])
                        sock.sendall(frame[1:])
                        size = unpack("!H", read_exact(sock, 2))[0]
                        reply = read_exact(sock, size)
                    else:
                        sock.send(query)
                        reply = sock.recv(4096)
                    assert str(DNSRecord.parse(reply).rr[0].rdata) == "192.0.2.1"
            finally:
                server.shutdown()
                thread.join(timeout=2)
