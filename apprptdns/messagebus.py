from datetime import datetime, timedelta
from confluent_kafka import Consumer, TopicPartition
from apprptdns.dns_pb2 import update
from apprptdns.cache import cache
from apprptdns.config import config
from google.protobuf.json_format import MessageToDict
import logging

class MessageBusServer():

    def __init__(self, cache):
        self.cache = cache.getCache()
        self.topic = "test"
        self.conf = {'bootstrap.servers': config['kafka']['bootstrap'],
            'group.id': 'DNSServer',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False,
        }
        self.consumer = Consumer(self.conf)
        self.partition_count = 0
        self.partition_check = datetime.now() - timedelta(hours=1)


    def deserialize(self, message):
        try: 
            result = update()
            result.ParseFromString(message)
        except Exception as error:
            logging.error("Error deserializing from queue: %s", error)
            return None
        return result

    def subscribe(self):
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
        self.running = True
        while self.running:
            try:
                self.subscribe()
                message = self.consumer.poll(timeout=1.0)
                if message is None: continue
                if message.value():
                    message = self.deserialize(message.value())
                    # TODO: TTL in the message is how often the client is suppose to refresh in seconds
                    #       But, they may not refresh within that time. So, we'll do it in minutes
                    if message.timestamp.ToDatetime() + timedelta(minutes=message.ttl) > datetime.now():
                        logging.debug("Node %s update with timestamp %s", message.node, message.timestamp.ToDatetime())
                        self.cache[message.node] = message
                    else:
                        logging.info("Node %s update outside of TTL: %s", message.node, message.timestamp.ToDatetime())
            except Exception as error:
                logging.error("Error parsing message from queue: %s", error)
                continue

    def shutdown(self):
        self.running = False
        if self.consumer is not None:
            self.consumer.close()
