from typing import Protocol


class Plugin(Protocol):
    """Generic structural contract implemented by external tgdrive plugins."""

    name: str
    version: str
    capabilities: frozenset[str]
