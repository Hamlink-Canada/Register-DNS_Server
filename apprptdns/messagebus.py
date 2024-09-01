from kafka import KafkaConsumer
from apprptdns.dns_pb2 import update
from google.protobuf.json_format import MessageToDict
#from cachetools import TTLCache

class MessageBusServer():

    def __init__(self):
#        self.entries = TTLCache(512, 120)
        self.consumer = None

    def deserialize(self, message):
        try: 
            result = update()
            result.ParseFromString(message)
        except Exception as error:
            print(error)
            return None
        return result

    def serve_forever(self):
        self.consumer = KafkaConsumer(
            'test',
            bootstrap_servers='localhost:9092',
            max_poll_records = 100,
            value_deserializer=lambda m: self.deserialize(m),
            auto_offset_reset='earliest',
        )
        self.running = True
        while self.running:
            try:
                for message in self.consumer:
                    if message.value:
                        print(message.value)
            except Exception as error:
                print(error)
                continue

    def shutdown(self):
        self.running = False
        if self.consumer is not None:
            self.consumer.close()
