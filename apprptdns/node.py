from dataclasses import dataclass
from cachetools import TTLCache
from apprptdns.config import config
from apprptdns.cache import cache
import logging

def asTXT(node):
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
    localCache = cache.getCache()
    if not number:
        return None
    node = int(number.group(1))
    if node not in localCache:
        logging.debug(f"{node} not found in cache")
        return None

    # TODO: Check TTL to see if it's still valid. 

    result = localCache[node]
    return result
