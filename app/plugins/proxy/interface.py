from abc import ABC, abstractmethod


class ProxyPlugin(ABC):
    """Base interface for Telegram proxy providers."""

    name = "unknown"

    @abstractmethod
    def get_proxy(self):
        """Return Telethon proxy configuration or None."""
        raise NotImplementedError
