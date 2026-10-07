from .models import Principal


class AuthenticationRequired(Exception):
    pass


class AuthorizationDenied(Exception):
    pass


def require_admin(principal: Principal) -> Principal:
    """Domain-level admin guard; transport adapters should map failures to HTTP 401/403."""
    if principal is None:
        raise AuthenticationRequired()
    if not principal.is_admin:
        raise AuthorizationDenied()
    return principal
