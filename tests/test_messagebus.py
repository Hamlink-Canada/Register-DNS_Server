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
        KAFKA=SimpleNamespace(BOOTSTRAP="localhost:9092", GROUP="test", TOPIC="registrations")
    )
    bus = MessageBus(settings, None)
    bus.partitions = {0}
    bus.serve()
    assert [(p.partition, p.offset) for p in bus.consumer.assigned] == [
        (0, expected),
        (1, OFFSET_BEGINNING),
    ]
    assert bus.consumer.closed
