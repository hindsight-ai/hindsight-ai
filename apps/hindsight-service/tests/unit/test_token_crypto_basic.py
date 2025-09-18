import sys
import re
sys.path.insert(0, 'apps/hindsight-service')

from core.utils import token_crypto as tc


def test_generate_and_parse_and_verify():
    tid, sec, tok = tc.generate_token()
    assert tok.startswith(tc.TOKEN_PREFIX)
    parsed = tc.parse_token(tok)
    assert parsed is not None
    assert parsed.token_id == tid
    assert parsed.secret == sec
    h = tc.hash_secret(sec)
    assert isinstance(h, str) and len(h) > 10
    assert tc.verify_secret(sec, h) is True


def test_derive_display_parts():
    tid, sec, tok = tc.generate_token()
    pfx, last4 = tc.derive_display_parts(tok)
    assert isinstance(pfx, str) and len(pfx) > 0
    assert isinstance(last4, str) and len(last4) == 4

