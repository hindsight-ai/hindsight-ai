from core.utils.token_crypto import (
    TOKEN_PREFIX,
    parse_token,
    build_token_string,
    hash_secret,
    verify_secret,
    derive_display_parts,
    generate_token,
)


def test_parse_token_and_build_roundtrip():
    tid = "abc123def4567890"
    secret = "s3cr3t_part_with_underscores"
    token = build_token_string(tid, secret)
    parsed = parse_token(token)
    assert parsed and parsed.token_id == tid and parsed.secret == secret

    assert parse_token("") is None
    assert parse_token("notvalid") is None
    assert parse_token(TOKEN_PREFIX + "nounderscore") is None


def test_hash_and_verify_secret_pbkdf2():
    secret = "topsecret"
    h = hash_secret(secret)
    # Should verify True for correct secret, False for wrong
    assert verify_secret(secret, h) is True
    assert verify_secret("wrong", h) is False


def test_display_parts_and_generate_token():
    tid, sec, token = generate_token()
    prefix, last4 = derive_display_parts(token)
    assert len(prefix) == 8
    assert len(last4) == 4
    # Non-prefixed returns blanks
    assert derive_display_parts("bogus")==("", "")
