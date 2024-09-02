import re
import logging
from apprptdns.node import getNode, asTXT
from apprptdns.config import config
from dnslib import (
            DNSError,
            DNSRecord, A,
            RR, QTYPE, RCODE,
            TXT, SRV,
            )


srvRegex = re.compile(r"^_iax\._udp\.([0-9]*)\.")
ATXTRegex = re.compile(r"^([0-9]*)\.")

def error(request = None):
    if request is None:
        reply = DNSRecord()
    else:
        reply = request.reply()
    reply.header.rcode = getattr(RCODE,'SERVFAIL')
    return reply.pack()

def dns_response(data):
    domain = config['dns']['basedomain']
    if not domain.endswith("."):
        domain = domain + "."

    # Parse the DNS request
    try: 
        request = DNSRecord.parse(data)
    except DNSError:
        logging.debug("Got Invalid Question")
        return None

    # Get the requested resource as a DNSLabel
    question = request.get_q()

    # Make sure we have a question for our domain, otherwise, just don't reply
    if not question.get_qname().matchSuffix(domain):
        return error(request)

    # Get the question as a string, without the domain
    qname = str(question.get_qname().stripSuffix(domain))

    if question.qtype == QTYPE.TXT:
        node = getNode(ATXTRegex.search(qname))
        if not node:
            return error(request)
        rdata = TXT(asTXT(node))

    elif question.qtype == QTYPE.SRV:
        node = getNode(srvRegex.search(qname))
        if not node:
            return error(request)
        rdata = SRV(priority = 0, weight = 0, port = node.port, target = f"{node.node}.{domain}")

    elif question.qtype == QTYPE.A:
        node = getNode(ATXTRegex.search(qname))
        if not node:
            return error(request)
        rdata = A(node.ipaddress)

    else:
        # We only reply to TXT, SRV and A requests
        logging.debug("Something else: %s", question.qtype)
        return error(request)

    reply = request.reply()
    reply.add_answer(RR(question.get_qname(), question.qtype, rdata=rdata, ttl=60))
    return reply.pack()
