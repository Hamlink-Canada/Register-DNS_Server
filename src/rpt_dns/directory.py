"""Shared nested protobuf ingestion and event-time expiration."""

from collections import OrderedDict
from datetime import timezone
from ipaddress import IPv4Address
from threading import RLock
from time import time

from google.protobuf.message import DecodeError
from rpt_protobuf.dns_update_pb2 import dns_update


class Directory:
    def __init__(self, capacity=10000, max_lifetime=86400, clock_skew=30, *, clock=time):
        self.capacity, self.max_lifetime, self.clock_skew = capacity, max_lifetime, clock_skew
        self.clock = clock
        self.entries = OrderedDict()
        self.watermarks = {}
        self.lock = RLock()

    def ingest(self, data):
        entry = dns_update()
        try:
            entry.ParseFromString(data)
            if not entry.HasField("node") or not entry.HasField("timestamp"):
                return False
            timestamp = entry.timestamp.ToDatetime().replace(tzinfo=timezone.utc).timestamp()
            # Validate protobuf Timestamp range/nanoseconds before accepting it.
            entry.timestamp.ToJsonString()
            node = entry.node
            IPv4Address(node.ipaddress)
            now = self.clock()
            if not (
                node.id > 0
                and 1 <= node.port <= 65535
                and 0 < node.ttl <= self.max_lifetime
                and node.server
                and len(("RH=" + node.server).encode("utf-8")) <= 255
            ):
                return False
            if timestamp > now + self.clock_skew or timestamp + node.ttl <= now:
                return False
        except (DecodeError, ValueError, OverflowError):
            return False
        with self.lock:
            now = self.clock()
            previous = self.watermarks.get(node.id)
            if previous and previous[0] >= (
                entry.timestamp.seconds,
                entry.timestamp.nanos,
            ):
                return False
            if previous is None and len(self.watermarks) >= self.capacity:
                for key, value in tuple(self.watermarks.items()):
                    if value[1] <= now:
                        del self.watermarks[key]
                        self.entries.pop(key, None)
                if len(self.watermarks) >= self.capacity:
                    return False
            self.watermarks[node.id] = (
                (entry.timestamp.seconds, entry.timestamp.nanos),
                timestamp + self.max_lifetime + self.clock_skew,
            )
            self.entries[node.id] = entry
            self.entries.move_to_end(node.id)
        return True

    def get(self, node_id):
        with self.lock:
            entry = self.entries.get(node_id)
            if entry is None:
                return None
            expiry = entry.timestamp.seconds + entry.timestamp.nanos / 1e9 + entry.node.ttl
            remaining = int(expiry - self.clock())
            if remaining < 1:
                del self.entries[node_id]
                return None
            return entry, min(60, remaining)
