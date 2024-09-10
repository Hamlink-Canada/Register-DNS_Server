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


    def deserialize(self, message):
        try: 
            result = update()
            result.ParseFromString(message)
        except Exception as error:
            logging.error("Error deserializing from queue: %s", error)
            return None
        return result

    def subscribe(self):
        # TODO: Figure out how to run this periodically so we ensure we're listening to all partititions if the count changes
        topics = self.consumer.list_topics(topic=self.topic)
        partitions = topics.topics[self.topic].partitions
        self.consumer.assign([TopicPartition(self.topic, p) for p in list(partitions)])

    def serve_forever(self):
        self.subscribe()

        self.running = True
        while self.running:
            try:
                message = self.consumer.poll(timeout=1.0)
                if message is None: continue
                if message.value():
                    message = self.deserialize(message.value())
                    # TODO: Check if now < timestamp + TTL, don't load if it's old
                    self.cache[message.node] = message
            except Exception as error:
                logging.error("Error parsing message from queue: %s", error)
                continue

    def shutdown(self):
        self.running = False
        if self.consumer is not None:
            self.consumer.close()
