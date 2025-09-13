"""
Token generation, parsing, and hashing utilities for Personal Access Tokens.

Responsibilities:
- Generate token strings of the form: hs_pat_<token_id>_<secret>
- Hash secrets using Argon2id (preferred) with PBKDF2-HMAC-SHA256 fallback
- Verify secrets with constant-time comparison
- Provide helpers to derive display prefix and last four for UI
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple

ARGON2_AVAILABLE = False
try:  # pragma: no cover - availability varies in environments
    from argon2 import PasswordHasher
    from argon2.low_level import Type

    _argon2 = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8, hash_len=32, type=Type.ID)
    ARGON2_AVAILABLE = True
except Exception:  # pragma: no cover
    _argon2 = None


TOKEN_PREFIX = "hs_pat_"


@dataclass(frozen=True)
class ParsedToken:
    token_id: str
    secret: str


def generate_token_id() -> str:
    """Return a short, url-safe token id (hex) suitable for DB lookup and logs."""
    # Use 12-16 hex chars from UUID to avoid '_' conflicts in parsing
    return uuid.uuid4().hex[:16]


def generate_secret(length: int = 32) -> str:
    """Return a high-entropy url-safe secret string (approx length)."""
    # token_urlsafe yields ~1.3 chars per byte; empirically length ~ 43 for 32 bytes
    return secrets.token_urlsafe(length)


def build_token_string(token_id: str, secret: str) -> str:
    return f"{TOKEN_PREFIX}{token_id}_{secret}"


def parse_token(token: str) -> Optional[ParsedToken]:
    """Parse a token string into token_id and secret.

    Returns None if format is invalid.
    """
    if not token or not token.startswith(TOKEN_PREFIX):
        return None
    body = token[len(TOKEN_PREFIX) :]
    # token_id contains no underscores (hex), secret may contain '_' so split once
    idx = body.find("_")
    if idx <= 0:
        return None
    token_id = body[:idx]
    secret = body[idx + 1 :]
    if not token_id or not secret:
        return None
    return ParsedToken(token_id=token_id, secret=secret)


def _pbkdf2_hash(secret: str, *, iterations: int = 200_000, salt_bytes: int = 16) -> str:
    salt = secrets.token_bytes(salt_bytes)
    dk = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
    return "pbkdf2$sha256$%d$%s$%s" % (
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(dk).decode("ascii"),
    )


def _pbkdf2_verify(secret: str, encoded: str) -> bool:
    try:
        scheme, algo, iter_str, b64_salt, b64_dk = encoded.split("$")
        if scheme != "pbkdf2" or algo != "sha256":
            return False
        iterations = int(iter_str)
        salt = base64.urlsafe_b64decode(b64_salt)
        dk_expected = base64.urlsafe_b64decode(b64_dk)
        dk = hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk, dk_expected)
    except Exception:
        return False


def hash_secret(secret: str) -> str:
    """Hash a secret using Argon2id when available, otherwise PBKDF2-HMAC-SHA256."""
    if ARGON2_AVAILABLE:
        return _argon2.hash(secret)  # type: ignore[arg-type]
    return _pbkdf2_hash(secret)


def verify_secret(secret: str, encoded_hash: str) -> bool:
    if not secret or not encoded_hash:
        return False
    try:
        if encoded_hash.startswith("$argon2id$") and ARGON2_AVAILABLE:
            return _argon2.verify(encoded_hash, secret)  # type: ignore[arg-type]
        if encoded_hash.startswith("pbkdf2$"):
            return _pbkdf2_verify(secret, encoded_hash)
        # Unknown scheme
        return False
    except Exception:
        return False


def derive_display_parts(full_token: str) -> Tuple[str, str]:
    """Return (prefix, last_four) for UI display.

    Prefix: first 8 chars of token body (after hs_pat_)
    Last four: last 4 chars of the secret part
    """
    if not full_token.startswith(TOKEN_PREFIX):
        return "", ""
    body = full_token[len(TOKEN_PREFIX) :]
    prefix = body[:8]
    parsed = parse_token(full_token)
    last_four = (parsed.secret[-4:] if parsed else "")
    return prefix, last_four


def generate_token() -> Tuple[str, str, str]:
    """Generate a new token and return (token_id, secret, full_token)."""
    tid = generate_token_id()
    sec = generate_secret()
    token = build_token_string(tid, sec)
    return tid, sec, token
