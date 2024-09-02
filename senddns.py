#!/usr/bin/env python3
from datetime import datetime
from apprptdns.dns_pb2 import update
from apprptdns.config import config
from kafka import KafkaProducer

config.read('config.ini')

Entry = update()
Entry.timestamp.FromDatetime(datetime.now())
Entry.node = 1234
Entry.ipaddress = "123.123.123.123"
Entry.port = 5060
Entry.ttl = 60
Entry.server = "Manual"

print(Entry)

producer = KafkaProducer(bootstrap_servers=config['kafka']['bootstrap'])
producer.send(config['kafka']['topic'], key=str(Entry.node).encode(), value=Entry.SerializeToString())
producer.flush()

