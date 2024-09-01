from dataclasses import dataclass

@dataclass
class Node:
    number: int
    ip: str
    port: int

    @property
    def asTXT(self):
        result = [
                    "NN=" + str(self.number),
                    "RT=",
                    "RB=0",
                    "IP=" + self.ip,
                    "PIP=",
                    "PT=" + str(self.port),
                    "RH=",
                ]
        return [w.encode() for w in result]

def getNode(number):
    if not number:
        return None
    node = number.group(1)
    return Node(node, "111.111.111.111", 5061)
