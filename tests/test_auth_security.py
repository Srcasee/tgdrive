import os

os.environ["AUTH_SECRET"] = "test-secret"
os.environ["AUTH_TOKEN_TTL"] = "60"

from auth.security import create_token, hash_password, verify_password, verify_token, verify_totp


def test_password_hash_round_trip():
    encoded = hash_password("correct horse battery staple")
    assert encoded != "correct horse battery staple"
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("wrong password", encoded)


def test_token_round_trip():
    token = create_token("42", "admin")
    payload = verify_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "admin"


def test_tampered_token_is_rejected():
    token = create_token("42", "admin")
    body, _ = token.split(".", 1)
    tampered = body + "x.invalid"
    try:
        verify_token(tampered)
    except Exception:
        return
    raise AssertionError("tampered token was accepted")



def test_totp_rfc_vector_and_invalid_code():
    # RFC 6238 SHA-1 test secret, truncated to the six-digit form.
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert verify_totp(secret, "287082", now=59, window=0)
    assert not verify_totp(secret, "287083", now=59, window=0)
