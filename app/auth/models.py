from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """Authenticated web principal used by API authorization dependencies."""

    subject: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"
