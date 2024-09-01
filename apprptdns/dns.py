import re
from apprptdns.node import getNode, asTXT
from dnslib import (
            DNSError,
            DNSRecord, A,
            RR, QTYPE, RCODE,
            TXT, SRV,
            )

domain = "nodes.pttlink.org."
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
    # Parse the DNS request
    try: 
        request = DNSRecord.parse(data)
    except DNSError:
        print("Got Invalid Question")
        return error()

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
        rdata = A(node.ip)

    else:
        # We only reply to TXT, SRV and A requests
        print(f"Something else: {question.qtype}")
        return error(request)

    reply = request.reply()
    reply.add_answer(RR(question.get_qname(), question.qtype, rdata=rdata, ttl=60))
    return reply.pack()
