from kafka import KafkaConsumer
from apprptdns.dns_pb2 import update
from apprptdns.cache import cache
from apprptdns.config import config
from google.protobuf.json_format import MessageToDict
import logging

class MessageBusServer():

    def __init__(self, cache):
        self.consumer = None
        self.cache = cache.getCache()

    def deserialize(self, message):
        try: 
            result = update()
            result.ParseFromString(message)
        except Exception as error:
            logging.error("Error deserializing from queue: %s", error)
            return None
        return result

    def serve_forever(self):
        self.consumer = KafkaConsumer(
            'test',
            bootstrap_servers=config['kafka']['bootstrap'],
            max_poll_records = 100,
            value_deserializer=lambda m: self.deserialize(m),
            auto_offset_reset='earliest',
        )
        self.running = True
        while self.running:
            try:
                for message in self.consumer:
                    if message.value:
                        # TODO: Check if now < timestamp + TTL, don't load if it's old
                        self.cache[message.value.node] = message.value
            except Exception as error:
                logging.error("Error parsing message from queue: %s", error)
                continue

    def shutdown(self):
        self.running = False
        if self.consumer is not None:
            self.consumer.close()
