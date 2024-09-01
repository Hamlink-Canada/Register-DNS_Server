from dataclasses import dataclass
from cachetools import TTLCache

cache = TTLCache(10240, 60)

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
    if not number:
        return None
    node = int(number.group(1))
    if node not in cache:
        print(f"{node} not found in cache")
        return None

    result = cache[node]
    return result
