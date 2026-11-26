import pytest
from dnslib import RCODE, DNSRecord

from rpt_dns.cli import read_exact
from rpt_dns.config import load_settings
from rpt_dns.dns import respond


@pytest.fixture(autouse=True)
def isolated_config(monkeypatch, tmp_path):
    monkeypatch.setenv("RPT_CONFIG_DIR", str(tmp_path))


@pytest.mark.parametrize(
    "overrides",
    [
        {"port": 65536},
        {"cache_size": 0},
        {"workers": True},
        {"domain": ""},
        {"kafka": {"security_protocol": "SSL"}},
        {"kafka": {"security_protocol": "SASL_SSL"}},
    ],
)
def test_dns_config_rejects_invalid_values(overrides):
    with pytest.raises(ValueError):
        load_settings(**overrides)


def test_dns_config_accepts_complete_scram_tls_settings():
    settings = load_settings(
        kafka={
            "security_protocol": "SASL_SSL",
            "sasl_mechanism": "SCRAM-SHA-512",
            "sasl_username": "dns-reader",
            "sasl_password": "example-password",
            "ssl_ca_location": "/var/run/ca.pem",
        }
    )
    assert settings.KAFKA.SECURITY_PROTOCOL == "SASL_SSL"


def test_dns_respond_rejects_multiple_questions_and_unknown_names():
    request = DNSRecord.question("1.nodes.example.org", "A")
    request.add_question(DNSRecord.question("2.nodes.example.org", "A").q)
    response = DNSRecord.parse(respond(request.pack(), object(), "nodes.example.org"))
    assert response.header.rcode == RCODE.FORMERR

    unknown = DNSRecord.question("0.nodes.example.org", "A")
    response = DNSRecord.parse(respond(unknown.pack(), object(), "nodes.example.org"))
    assert response.header.rcode == RCODE.SERVFAIL


def test_dns_respond_returns_none_for_malformed_packet():
    assert respond(b"not-a-dns-packet", object(), "nodes.example.org") is None


def test_read_exact_handles_fragmented_reads_and_eof():
    class Fragmented:
        def __init__(self, chunks):
            self.chunks = iter(chunks)

        def recv(self, size):
            return next(self.chunks, b"")[:size]

    assert read_exact(Fragmented([b"a", b"bc"]), 3) == b"abc"
    with pytest.raises(ValueError, match="truncated"):
        read_exact(Fragmented([b"a", b""]), 2)
