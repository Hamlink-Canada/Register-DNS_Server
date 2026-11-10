import pytest
from dnslib import RCODE, DNSRecord
from rpt_protobuf.dns_update_pb2 import dns_update

from rpt_dns.directory import Directory
from rpt_dns.dns import respond


def update(timestamp=100, ttl=180, node=1234):
    entry = dns_update()
    entry.timestamp.seconds = timestamp
    entry.node.id = node
    entry.node.ipaddress = "192.0.2.1"
    entry.node.port = 4569
    entry.node.ttl = ttl
    entry.node.server = "registrar-1"
    return entry


def test_shared_nested_update_expiry_and_replay():
    now = [100.0]
    directory = Directory(clock=lambda: now[0])
    assert directory.ingest(update().SerializeToString())
    assert directory.get(1234)[1] == 60
    now[0] = 270
    assert directory.get(1234)[1] == 10
    now[0] = 280
    assert directory.get(1234) is None
    assert not directory.ingest(update().SerializeToString())


def test_out_of_order_and_duplicate_rejected():
    directory = Directory(clock=lambda: 100)
    assert directory.ingest(update().SerializeToString())
    assert not directory.ingest(update().SerializeToString())
    assert not directory.ingest(update(timestamp=99).SerializeToString())
    assert directory.get(1234)[0].timestamp.seconds == 100


@pytest.mark.parametrize("change", [{"ttl": 0}, {"ttl": -1}, {"timestamp": 1000}, {"node": 0}])
def test_invalid_updates(change):
    directory = Directory(clock=lambda: 100)
    assert not directory.ingest(update(**change).SerializeToString())


def test_malformed_and_missing_fields():
    directory = Directory(clock=lambda: 100)
    assert not directory.ingest(b"\xff")
    assert not directory.ingest(dns_update().SerializeToString())


@pytest.mark.parametrize(
    "kind,name",
    [
        ("A", "1234.nodes.example.org"),
        ("TXT", "1234.nodes.example.org"),
        ("SRV", "_iax._udp.1234.nodes.example.org"),
    ],
)
def test_dns_uses_nested_message_and_remaining_ttl(kind, name):
    directory = Directory(clock=lambda: 275)
    assert directory.ingest(update().SerializeToString())
    result = DNSRecord.parse(
        respond(DNSRecord.question(name, kind).pack(), directory, "nodes.example.org")
    )
    assert result.header.rcode == RCODE.NOERROR
    assert result.rr[0].ttl == 5
    if kind == "A":
        assert str(result.rr[0].rdata) == "192.0.2.1"
    if kind == "SRV":
        assert result.rr[0].rdata.port == 4569


def test_directory_capacity_and_domain_isolation():
    directory = Directory(capacity=1, clock=lambda: 100)
    directory.ingest(update(node=1).SerializeToString())
    directory.ingest(update(node=2).SerializeToString())
    assert directory.get(1) is None
    request = DNSRecord.question("2.attacker.example", "A")
    result = DNSRecord.parse(respond(request.pack(), directory, "nodes.example.org"))
    assert result.header.rcode == RCODE.SERVFAIL
