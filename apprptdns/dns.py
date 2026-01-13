"""DNS response builder that maps APP RPT node updates to DNS records.

Supported question types:
- TXT: returns node metadata as TXT key/value strings
- A: returns node IP address
- SRV: returns an SRV record pointing to `<node>.<basedomain>`

This module validates that queries are for the configured base domain and
uses the shared in-memory cache (stored as protobuf `update` messages)
to populate DNS answers.
"""

import re
import logging
from apprptdns.node import getNode, asTXT
from apprptdns.config import config
from dnslib import DNSError, DNSRecord, A, RR, QTYPE, RCODE, TXT, SRV


# Regular expressions used to extract the numeric node id from the queried
# name. Example TXT/A: "1234.nodes.pttlink.org." -> group(1) == "1234"
# Example SRV: "_iax._udp.1234.nodes.pttlink.org." -> group(1) == "1234"
srvRegex = re.compile(r"^_iax\._udp\.([0-9]*)\.")
ATXTRegex = re.compile(r"^([0-9]*)\.")


def error(request=None):
    """Return a packed SERVFAIL response.

    If `request` is provided we build a reply matching the incoming
    question; otherwise return an empty DNSRecord with the SERVFAIL code.
    """
    if request is None:
        reply = DNSRecord()
    else:
        reply = request.reply()
    reply.header.rcode = getattr(RCODE, 'SERVFAIL')
    return reply.pack()


def dns_response(data):
    """Parse incoming DNS packet `data` and return a packed reply.

    Returns `None` when the query cannot be parsed (invalid packet), and
    otherwise returns a packed DNS reply. Unsupported or missing node
    entries result in a SERVFAIL reply.
    """
    domain = config['dns']['basedomain']
    if not domain.endswith('.'):
        domain = domain + '.'

    # Parse the DNS request into a DNSRecord object
    try:
        request = DNSRecord.parse(data)
    except DNSError:
        logging.debug("Got invalid DNS question packet")
        return None

    # Single question label
    question = request.get_q()

    # Only answer queries for our configured base domain; otherwise return SERVFAIL
    if not question.get_qname().matchSuffix(domain):
        return error(request)

    # Remove the base domain from the qname string so regexes match the prefix
    qname = str(question.get_qname().stripSuffix(domain))

    # Map question types to cache lookups and rdata construction
    if question.qtype == QTYPE.TXT:
        # Expect a numeric prefix, e.g. "1234." -> TXT with node metadata
        node = getNode(ATXTRegex.search(qname))
        if not node:
            return error(request)
        rdata = TXT(asTXT(node))

    elif question.qtype == QTYPE.SRV:
        # SRV records use the `_iax._udp.<node>` naming convention
        node = getNode(srvRegex.search(qname))
        if not node:
            return error(request)
        # SRV points to <node>.<domain> with the node's port
        rdata = SRV(priority=0, weight=0, port=node.port, target=f"{node.node}.{domain}")

    elif question.qtype == QTYPE.A:
        # A queries use the same numeric prefix as TXT
        node = getNode(ATXTRegex.search(qname))
        if not node:
            return error(request)
        rdata = A(node.ipaddress)

    else:
        # We only reply to TXT, SRV and A requests
        logging.debug("Unsupported question type: %s", question.qtype)
        return error(request)

    # Build the reply and attach a single answer with a conservative TTL
    reply = request.reply()
    reply.add_answer(RR(question.get_qname(), question.qtype, rdata=rdata, ttl=60))
    return reply.pack()
