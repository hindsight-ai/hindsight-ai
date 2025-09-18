import uuid
import pytest

from core.utils import token_crypto
from core.api import deps as deps_mod


def test_generate_and_parse_token_format():
    tid, secret, full = token_crypto.generate_token()
    assert tid and secret and full
    assert full.startswith(token_crypto.TOKEN_PREFIX)
    parsed = token_crypto.parse_token(full)
    assert parsed is not None
    assert parsed.token_id == tid
    assert parsed.secret == secret


def test_hash_and_verify_argon2_or_pbkdf2():
    secret = "s3cr3t-Value"
    enc = token_crypto.hash_secret(secret)
    assert enc
    assert token_crypto.verify_secret(secret, enc) is True
    assert token_crypto.verify_secret("wrong", enc) is False


def test_verify_pbkdf2_path_even_if_argon2_present():
    secret = "another-secret"
    # Force-generate a PBKDF2 encoded hash using the helper
    enc = token_crypto._pbkdf2_hash(secret)
    assert enc.startswith("pbkdf2$")
    assert token_crypto.verify_secret(secret, enc) is True
    assert token_crypto.verify_secret("bad", enc) is False


def test_derive_display_parts_has_prefix_and_last4():
    tid = "abcd1234efgh5678"
    secret = "xyz-0123456789"
    full = token_crypto.build_token_string(tid, secret)
    prefix, last4 = token_crypto.derive_display_parts(full)
    # Prefix is first 8 of the token body (token_id begins the body)
    assert prefix == tid[:8]
    assert last4 == secret[-4:]


def _fake_current_user_with_pat(scopes, org_id=None):
    return {
        "id": uuid.uuid4(),
        "email": "user@example.com",
        "display_name": "User",
        "memberships": [],
        "memberships_by_org": {},
        "pat": {
            "id": uuid.uuid4(),
            "token_id": "tid",
            "scopes": scopes,
            "organization_id": org_id,
        },
    }


def test_ensure_pat_allows_read_scope_rules():
    # No PAT -> no-op
    deps_mod.ensure_pat_allows_read({})

    # read present -> ok
    cu = _fake_current_user_with_pat(["read"], None)
    deps_mod.ensure_pat_allows_read(cu)

    # write implies read -> ok
    cu = _fake_current_user_with_pat(["write"], None)
    deps_mod.ensure_pat_allows_read(cu)

    # neither read nor write -> 403
    cu = _fake_current_user_with_pat(["manage"], None)
    with pytest.raises(Exception):
        deps_mod.ensure_pat_allows_read(cu)


def test_ensure_pat_allows_read_org_mismatch():
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    cu = _fake_current_user_with_pat(["read"], org_a)
    # Matching org -> ok
    deps_mod.ensure_pat_allows_read(cu, target_org_id=org_a)
    # Mismatch -> 403
    with pytest.raises(Exception):
        deps_mod.ensure_pat_allows_read(cu, target_org_id=org_b)

