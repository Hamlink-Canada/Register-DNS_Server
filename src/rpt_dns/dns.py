"""DNS A/TXT/SRV replies from current registration entries."""

import re
from time import monotonic

from dnslib import QTYPE, RCODE, RR, SRV, TXT, A, DNSError, DNSRecord

try:
    from opentelemetry import metrics, trace
except ImportError:  # Telemetry is an optional extra.
    metrics = None
    trace = None

if metrics is not None:
    _meter = metrics.get_meter(__name__)
    _queries = _meter.create_counter("rpt.dns.queries", unit="{query}")
    _query_duration = _meter.create_histogram("rpt.dns.query.duration", unit="s")
else:
    _queries = _query_duration = None


def respond(data, directory, domain, client_address=None):
    span = trace.get_tracer(__name__).start_span("rpt_dns.query") if trace else None
    scope = trace.use_span(span, end_on_exit=True) if span is not None else None
    if scope is not None:
        scope.__enter__()
    if client_address and trace is not None and span is not None and span.is_recording():
        span.set_attribute("client.address", client_address[0])
    started = monotonic()
    outcome = "success"
    try:
        request = DNSRecord.parse(data)
        reply = request.reply()
        if len(request.questions) != 1:
            outcome = "formerr"
            reply.header.rcode = RCODE.FORMERR
            return reply.pack()
        question = request.q
        prefix = r"_iax\._udp\." if question.qtype == QTYPE.SRV else ""
        match = re.fullmatch(
            prefix + r"([1-9][0-9]{0,18})\." + re.escape(domain.rstrip(".")) + r"\.",
            str(question.qname),
            re.IGNORECASE,
        )
        found = directory.get(int(match[1])) if match else None
        if trace is not None and span is not None and span.is_recording():
            span.set_attribute("dns.question.name", str(question.qname))
            span.set_attribute("dns.question.type", QTYPE.get(question.qtype, str(question.qtype)))
            if match:
                span.set_attribute("repeater.node_id", match[1])
        if found is None:
            outcome = "not_found"
            reply.header.rcode = RCODE.SERVFAIL
            return reply.pack()
        entry, ttl = found
        node = entry.node
        if question.qtype == QTYPE.A:
            rdata = A(node.ipaddress)
        elif question.qtype == QTYPE.SRV:
            rdata = SRV(
                priority=0, weight=0, port=node.port, target=f"{node.id}.{domain.rstrip('.')}"
            )
        elif question.qtype == QTYPE.TXT:
            timestamp = entry.timestamp.ToDatetime().replace(microsecond=0).isoformat()
            rdata = TXT(
                [
                    f"NN={node.id}",
                    f"RT={timestamp}",
                    "RB=0",
                    f"IP={node.ipaddress}",
                    "PIP=",
                    f"PT={node.port}",
                    f"RH={node.server}",
                ]
            )
        else:
            outcome = "unsupported_type"
            reply.header.rcode = RCODE.SERVFAIL
            return reply.pack()
        reply.add_answer(RR(question.qname, question.qtype, rdata=rdata, ttl=ttl))
        return reply.pack()
    except (DNSError, ValueError, OverflowError):
        outcome = "malformed"
        if trace is not None and span is not None and span.is_recording():
            span.set_attribute("dns.failure.category", "malformed_query")
        return None
    finally:
        attributes = {"outcome": outcome}
        if _queries is not None:
            _queries.add(1, attributes)
            _query_duration.record(monotonic() - started, attributes)
        if scope is not None:
            scope.__exit__(None, None, None)
