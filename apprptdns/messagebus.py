"""Kafka messagebus consumer that populates the in-memory cache.

This module uses `confluent_kafka.Consumer` to read protobuf `update`
messages from the configured topic and stores valid entries in the
shared TTL cache.
"""

from datetime import datetime, timedelta
from confluent_kafka import Consumer, TopicPartition
from apprptdns.dns_pb2 import update
from apprptdns.cache import cache
from apprptdns.config import config
from google.protobuf.json_format import MessageToDict
import logging


class MessageBusServer():
    """Consume node update messages and write them into the cache.

    Notes:
    - Uses `config['kafka']['bootstrap']` for bootstrap servers.
    - Assigns partitions manually when the partition count changes to
      ensure the consumer can read all available partitions.
    """

    def __init__(self, cache):
        # store direct reference to the underlying mapping for fast writes
        self.cache = cache.getCache()
        self.topic = "test"
        self.conf = {
            'bootstrap.servers': config['kafka']['bootstrap'],
            'group.id': 'DNSServer',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        }
        self.consumer = Consumer(self.conf)
        # track partition count to detect changes
        self.partition_count = 0
        self.partition_check = datetime.now() - timedelta(hours=1)

    def deserialize(self, message):
        """Parse a protobuf `update` message from bytes.

        Returns the parsed message or None on error.
        """
        try:
            result = update()
            result.ParseFromString(message)
        except Exception as error:
            logging.error("Error deserializing from queue: %s", error)
            return None
        return result

    def subscribe(self):
        """Periodically check topic metadata and assign partitions if changed."""
        if self.partition_check < datetime.now() - timedelta(minutes=1):
            logging.debug("Checking partition count")
            self.partition_check = datetime.now()
            topics = self.consumer.list_topics(topic=self.topic)
            partitions = topics.topics[self.topic].partitions
            if len(partitions) > self.partition_count:
                logging.debug("Partition count changed from %s to %s.", self.partition_count, len(partitions))
                self.partition_count = len(partitions)
                self.consumer.assign([TopicPartition(self.topic, p) for p in list(partitions)])

    def serve_forever(self):
        """Main loop: poll for messages and insert valid updates into cache."""
        self.running = True
        while self.running:
            try:
                self.subscribe()
                message = self.consumer.poll(timeout=1.0)
                if message is None:
                    continue
                if message.value():
                    message = self.deserialize(message.value())
                    # TTL in the message is provided in seconds by clients.
                    # Here we accept updates where timestamp + ttl (minutes)
                    # is still in the future.
                    if message.timestamp.ToDatetime() + timedelta(minutes=message.ttl) > datetime.now():
                        logging.debug("Node %s update with timestamp %s", message.node, message.timestamp.ToDatetime())
                        self.cache[message.node] = message
                    else:
                        logging.info("Node %s update outside of TTL: %s", message.node, message.timestamp.ToDatetime())
            except Exception as error:
                logging.error("Error parsing message from queue: %s", error)
                continue

    def shutdown(self):
        """Stop the loop and close the consumer."""
        self.running = False
        if self.consumer is not None:
            self.consumer.close()
