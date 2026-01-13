"""Helpers to format node entries and lookup nodes in the cache.

This module converts the protobuf `update` message into DNS TXT fields
and provides a helper to retrieve a node by numeric ID from the shared cache.
"""

from dataclasses import dataclass
from cachetools import TTLCache
from apprptdns.config import config
from apprptdns.cache import cache
import logging


def asTXT(node):
    """Return a list of bytes suitable for a DNS TXT record.

    The function formats several key/value pairs expected by APP RPT
    consumers and returns them encoded as bytes as required by `dnslib.TXT`.
    """
    result = [
        "NN=" + str(node.node),
        "RT=" + node.timestamp.ToDatetime().replace(microsecond=0).isoformat(),
        "RB=0",
        "IP=" + node.ipaddress,
        "PIP=",
        "PT=" + str(node.port),
        "RH=" + node.server,
    ]
    return [w.encode() for w in result]


def getNode(number):
    """Lookup a node by regex match object containing the numeric id.

    Returns the protobuf `update` message stored in the cache or `None` if
    not present. The argument `number` is expected to be a `re.Match`
    with the first group containing the node id.
    """
    localCache = cache.getCache()
    if not number:
        return None
    node = int(number.group(1))
    if node not in localCache:
        logging.debug(f"{node} not found in cache")
        return None

    # TODO: Check TTL to see if it's still valid. The cache is a TTLCache so
    # entries should expire automatically, but additional validation could be
    # applied here if needed.

    result = localCache[node]
    return result
