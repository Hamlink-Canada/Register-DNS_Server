from dataclasses import dataclass
from cachetools import TTLCache
from apprptdns.config import config
from apprptdns.cache import cache

def asTXT(node):
    result = [
                "NN=" + str(node.node),
                "RT=",
                "RB=0",
                "IP=" + node.ipaddress,
                "PIP=",
                "PT=" + str(node.port),
                "RH=",
            ]
    return [w.encode() for w in result]

def getNode(number):
    localCache = cache.getCache()
    if not number:
        return None
    node = int(number.group(1))
    if node not in localCache:
        print(f"{node} not found in cache")
        return None

    result = localCache[node]
    return result
