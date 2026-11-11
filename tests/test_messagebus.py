from types import SimpleNamespace

import pytest
from confluent_kafka import OFFSET_BEGINNING, TopicPartition

from rpt_dns.messagebus import MessageBus


@pytest.mark.parametrize("offset,expected", [(5, 5), (-1001, OFFSET_BEGINNING)])
def test_partition_expansion_preserves_positions_and_replays_uninitialized(
    monkeypatch, offset, expected
):
    class Consumer:
        closed = False
        assigned = []

        def __init__(self, config):
            self.config = config
            assert config["auto.offset.reset"] == "earliest"

        def list_topics(self, topic, timeout):
            return SimpleNamespace(
                topics={topic: SimpleNamespace(error=None, partitions={0: None, 1: None})}
            )

        def assignment(self):
            return [TopicPartition("registrations", 0)]

        def position(self, assignment):
            return [TopicPartition("registrations", 0, offset)]

        def assign(self, partitions):
            self.assigned = partitions

        def poll(self, timeout):
            bus.stopped.set()
            return None

        def close(self):
            self.closed = True

    monkeypatch.setattr("rpt_dns.messagebus.Consumer", Consumer)
    settings = SimpleNamespace(
        KAFKA=SimpleNamespace(
            BOOTSTRAP="localhost:9092",
            GROUP="test",
            TOPIC="registrations",
            SECURITY_PROTOCOL="",
        )
    )
    bus = MessageBus(settings, None)
    bus.partitions = {0}
    bus.serve()
    assert [(p.partition, p.offset) for p in bus.consumer.assigned] == [
        (0, expected),
        (1, OFFSET_BEGINNING),
    ]
    assert bus.consumer.closed


def test_message_bus_uses_tls_scram_consumer_settings(monkeypatch):
    created = {}

    class Consumer:
        def __init__(self, config):
            created.update(config)

    monkeypatch.setattr("rpt_dns.messagebus.Consumer", Consumer)
    settings = SimpleNamespace(
        KAFKA=SimpleNamespace(
            BOOTSTRAP="kafka:9093",
            TOPIC="rpt.registrations",
            GROUP="rpt-dns",
            SECURITY_PROTOCOL="SASL_SSL",
            SASL_MECHANISM="SCRAM-SHA-512",
            SASL_USERNAME="registration-dns-consumer",
            SASL_PASSWORD="test-password",
            SSL_CA_LOCATION="/var/run/kafka/ca.crt",
        )
    )

    MessageBus(settings, None)

    assert created["bootstrap.servers"] == "kafka:9093"
    assert created["security.protocol"] == "SASL_SSL"
    assert created["sasl.mechanism"] == "SCRAM-SHA-512"
    assert created["sasl.username"] == "registration-dns-consumer"
    assert created["sasl.password"] == "test-password"
    assert created["ssl.ca.location"] == "/var/run/kafka/ca.crt"
