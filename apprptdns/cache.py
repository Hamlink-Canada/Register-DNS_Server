"""Simple cache wrapper using cachetools.TTLCache.

This module exposes a single `cache` instance with two helpers:
- `setupCache()` — initialize the TTLCache using values from `config.ini`.
- `getCache()` — return the underlying cache mapping.

The DNS server and messagebus consumer use this to store node updates.
"""

from cachetools import TTLCache
from apprptdns.config import config


class cacheHandler:
    """Encapsulate the TTLCache so callers use a shared instance.

    Usage:
        cache.setupCache()
        c = cache.getCache()
    """

    def getCache(self):
        """Return the underlying TTLCache object."""
        return self.cache

    def setupCache(self):
        """Create the TTLCache using values from the loaded `config`.

        The `size` is the maximum number of entries and `ttl` is the
        time-to-live in seconds for each entry.
        """
        self.cache = TTLCache(int(config['cache']['size']), int(config['cache']['ttl']))


cache = cacheHandler()
