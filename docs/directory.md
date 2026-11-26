# Directory behavior

The directory consumes every Kafka partition independently on each DNS instance,
replaying from the beginning on process restart. It does not join a consumer group
for load balancing: each replica must see the whole directory. Partitions added
later are discovered within 60 seconds. Expired and older updates are discarded.
Kafka remains the deployment's durable replay source; this service adds no database.

The only accepted registration message is `rpt_protobuf.dns_update_pb2.dns_update`,
with the existing shared nested node fields. Legacy messages have no decoder here.
An entry expires at timestamp + node.ttl seconds. DNS responses cap TTL at 60 seconds
and the entry's remaining validity. The bounded directory defaults to 10000 entries;
choose an adequate capacity for your network. Invalid addresses, IDs, ports,
timestamps, lifetimes, or missing metadata are rejected.

Configuration: `RPT_DOMAIN`, `RPT_PORT` (default 5054 TCP and UDP), `RPT_CACHE_SIZE`,
`RPT_MAX_LIFETIME` (86400 seconds), `RPT_CLOCK_SKEW` (30 seconds), `RPT_WORKERS` (32),
and nested Kafka settings. Only IPv4 registrations and A/TXT/SRV responses are
implemented. Domain names must match the configured suffix exactly. TCP frames are
read incrementally with timeouts. Worker admission is bounded; configure shared
network limits at ingress for public deployments.
