from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass
class Plugin:
    """Generic tgdrive plugin contract.

    Plugins advertise capabilities; the core depends only on this contract and
    never imports a concrete plugin implementation.
    """

    name: str
    version: str = "0.0.0"
    capabilities: FrozenSet[str] = field(default_factory=frozenset)
