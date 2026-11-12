# DNS directory documentation

This project is the read side of the registration system. It consumes timestamped
registration updates from Kafka, keeps a bounded in-memory directory of current
IPv4 node endpoints, and answers DNS queries with A, TXT, and IAX SRV records.

```text
HTTP/IAX registrar --protobuf registration update--> Kafka --consume/replay--> DNS directory
                                                                              |
                                                               A / TXT / IAX SRV answers
```

Kafka replay rebuilds the local directory when the service starts. A message's
timestamp and registration lifetime determine when its entry expires; replaying an
old event does not renew it. Each replica reads the full registration topic so its
directory is complete. Kafka retention therefore needs to cover the replay window.

This service does not authenticate incoming registrations or write Kafka events.
Those responsibilities belong to the registrar services.

Start with the repository [README](../README.md) for a local container example and
configuration summary. See [directory behavior](directory.md) for record semantics
and expiry, and [glossary](glossary.md) for domain terms.
