"""Backward-compatible proxy manager facade.

New code should use ProxyRuntime directly. Keeping this facade avoids a
breaking import for deployments that already referenced ProxyManager.
"""

from .runtime import ProxyRuntime


class ProxyManager(ProxyRuntime):
    pass
