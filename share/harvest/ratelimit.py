import time
import logging


logger = logging.getLogger(__name__)


class RateLimittedProxy:

    def __init__(self, proxy_to, calls, per_second):
        self._proxy_to = proxy_to
        self._allowance = calls
        self._calls = calls
        self._last_call = 0
        self._per_second = per_second
        self._cache = {}

    def _check_limit(self):
        if self._allowance > 1:
            return
        wait = self._per_second - (time.time() - self._last_call)
        if wait > 0:
            logger.debug('Rate limitting %s. Sleeping for %s', self._proxy_to, wait)
            time.sleep(wait)
        self._allowance = self._calls
        logger.debug('Access granted for %s', self._proxy_to)

    def _called(self):
        self._allowance -= 1
        self._last_call = time.time()

    def __call__(self, *args, **kwargs):
        self._check_limit()
        ret = self._proxy_to(*args, **kwargs)
        self._called()
        return ret

    def __getattr__(self, name):
        return self._cache.setdefault(name, self.__class__(getattr(self._proxy_to, name), self._calls, self._per_second))
