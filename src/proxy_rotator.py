from itertools import cycle


class ProxyRotator:
    """
    Round-robin proxy selection for authorized monitoring.
    """

    def __init__(self, proxies):
        self.proxies = list(proxies)
        self._proxy_cycle = (
            cycle(self.proxies)
            if self.proxies
            else None
        )

    def next_proxy(self):
        if self._proxy_cycle is None:
            return None

        return next(self._proxy_cycle)

    def has_proxies(self):
        return bool(self.proxies)