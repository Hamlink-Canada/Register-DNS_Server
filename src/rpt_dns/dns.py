"""DNS A/TXT/SRV replies from current registration entries."""

import re

from dnslib import QTYPE, RCODE, RR, SRV, TXT, A, DNSError, DNSRecord


def respond(data, directory, domain):
    try:
        request = DNSRecord.parse(data)
        reply = request.reply()
        if len(request.questions) != 1:
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
        if found is None:
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
            reply.header.rcode = RCODE.SERVFAIL
            return reply.pack()
        reply.add_answer(RR(question.qname, question.qtype, rdata=rdata, ttl=ttl))
        return reply.pack()
    except (DNSError, ValueError, OverflowError):
        return None
