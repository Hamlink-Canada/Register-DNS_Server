from cachetools import TTLCache
from apprptdns.config import config

class cacheHandler:
    def getCache(self):
        return self.cache

    def setupCache(self):
        self.cache = TTLCache(int(config['cache']['size']), int(config['cache']['ttl']))

cache = cacheHandler()
