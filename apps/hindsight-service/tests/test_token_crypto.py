import importlib

from core.utils import token_crypto


def test_generate_and_parse_roundtrip():
    tid, secret, full = token_crypto.generate_token()
    assert tid and secret and full
    parsed = token_crypto.parse_token(full)
    assert parsed is not None
    assert parsed.token_id == tid
    assert parsed.secret == secret
    prefix, last4 = token_crypto.derive_display_parts(full)
    # prefix/last4 should be strings (may be empty in degenerate cases)
    assert isinstance(prefix, str)
    assert isinstance(last4, str)


def test_hash_and_verify_pbkdf2_fallback():
    # Force PBKDF2 fallback regardless of argon2 availability to exercise that code path
    old_argon = getattr(token_crypto, "ARGON2_AVAILABLE", False)
    try:
        # Toggle the runtime flag so hash_secret uses the PBKDF2 fallback path
        token_crypto.ARGON2_AVAILABLE = False
        secret = "s3cr3t-test-value"
        enc = token_crypto.hash_secret(secret)
        assert enc.startswith("pbkdf2$")
        assert token_crypto.verify_secret(secret, enc)
        assert not token_crypto.verify_secret("wrong-secret", enc)
    finally:
        # Restore original flag
        token_crypto.ARGON2_AVAILABLE = old_argon
