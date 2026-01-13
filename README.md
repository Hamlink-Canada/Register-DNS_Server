# APP RPT DNS Server

Python DNS service for APP RPT portals.

Overview
- Listens to a Kafka topic and keeps APP RPT node updates in an in-memory TTL cache.
- Answers DNS A, SRV and TXT queries for nodes from cache.

Quick Start

Prerequisites
- Python 3.8+
- `protoc` (Protocol Buffers compiler) for generating `apprptdns/dns_pb2.py`
- Kafka cluster accessible to the server

Install

1. Create and activate a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Generate protobuf bindings:

```bash
./build_proto.sh
```

Configuration
- Edit `config.ini` to point to your Kafka bootstrap servers and tune cache settings. Example:

```ini
[kafka]
bootstrap=localhost:9092
topic=test

[cache]
size=10240
ttl=60

[dns]
basedomain=nodes.pttlink.org
port=5054
```

Running the DNS server

From the `dnsserver/` directory run:

```bash
python3 dnsserver.py
```

This starts UDP, TCP DNS listeners on the configured port and a messagebus consumer that populates the cache.

Sending test updates

`senddns.py` is provided as a simple example that publishes a protobuf `update` message to Kafka. It uses the Kafka producer to send a serialized `update` message to the configured topic.

Notes and troubleshooting
- `requirements.txt` lists `confluent_kafka` (used by the consumer). The `senddns.py` example imports `KafkaProducer` from `kafka` (the `kafka-python` library). If you plan to use `senddns.py` as-is, install `kafka-python` or change `senddns.py` to use `confluent_kafka.Producer` for consistency.
- Run `./build_proto.sh` after editing `dns.proto` to regenerate `apprptdns/dns_pb2.py`.
- The cache uses `cachetools.TTLCache`; entries are kept according to `config.ini` settings.

Contributing / Notes
- This project is a work in progress. The `apprptdns` package contains the DNS logic (`dns.py`), cache handling, the Kafka consumer (`messagebus.py`), and request handlers (`handlers.py`).
- There are small implementation details to consider (see `apprptdns/servers.py` and `senddns.py`) which may need adjustments depending on your deployment or preferred Kafka client.

License

See the `LICENSE` file for license information.
