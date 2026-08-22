from ..interface import ProxyPlugin


class NoneProxy(ProxyPlugin):
    name = "none"

    def get_proxy(self):
        return None
