"""Each DNS instance replays all partitions, rejecting expired or stale events."""

import logging
from threading import Event

from confluent_kafka import OFFSET_BEGINNING, Consumer, KafkaException, TopicPartition

from rpt_dns.kafka_config import client_config


class MessageBus:
    def __init__(self, settings, directory):
        self.settings, self.directory = settings, directory
        self.stopped = Event()
        config = client_config(settings)
        config.update(
            {
                "group.id": settings.KAFKA.GROUP,
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
            }
        )
        self.consumer = Consumer(config)
        self.partitions = set()

    def serve(self):
        from time import monotonic

        next_check = 0
        try:
            while not self.stopped.is_set():
                try:
                    if monotonic() >= next_check:
                        topic = self.consumer.list_topics(self.settings.KAFKA.TOPIC, timeout=2)
                        metadata = topic.topics[self.settings.KAFKA.TOPIC]
                        if metadata.error:
                            raise KafkaException(metadata.error)
                        partitions = set(metadata.partitions)
                        if partitions != self.partitions:
                            positions = {
                                p.partition: p.offset if p.offset >= 0 else OFFSET_BEGINNING
                                for p in self.consumer.position(self.consumer.assignment())
                            }
                            self.consumer.assign(
                                [
                                    TopicPartition(
                                        self.settings.KAFKA.TOPIC,
                                        p,
                                        positions.get(p, OFFSET_BEGINNING),
                                    )
                                    for p in sorted(partitions)
                                ]
                            )
                            self.partitions = partitions
                        next_check = monotonic() + 60
                    message = self.consumer.poll(0.2)
                    if message is not None and not message.error() and message.value():
                        self.directory.ingest(message.value())
                except (KafkaException, KeyError):
                    logging.warning("Kafka directory consumer unavailable")
                    self.stopped.wait(1)
        finally:
            self.consumer.close()
