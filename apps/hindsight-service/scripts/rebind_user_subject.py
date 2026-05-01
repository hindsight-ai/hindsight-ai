"""
Operator script to clear or rebind a User row's external_subject.

Use cases:
  - The deployment's oauth2-proxy `--user-id-claim` was changed (e.g.
    preferred_username -> sub) and existing users now hit
    IdentityMismatchError on every sign-in.
  - A real account-recovery situation where a user's Google sub
    legitimately changed (rare; provider migration).
  - Cleanup after a failed F2 partial deployment.

Usage:
    python -m scripts.rebind_user_subject --email user@example.com --clear
    python -m scripts.rebind_user_subject --email user@example.com \\
        --new-subject 1234567890

Always lists the affected row and prompts before committing unless
--yes is passed.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _engine():
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    return create_engine(url, future=True)


def _confirm(prompt: str, *, yes: bool) -> bool:
    if yes:
        return True
    answer = input(f"{prompt} [y/N] ").strip().lower()
    return answer in ("y", "yes")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", required=True, help="User email (case-insensitive)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--clear", action="store_true", help="Set external_subject and auth_provider to NULL")
    group.add_argument("--new-subject", help="Set external_subject to this value")
    parser.add_argument("--auth-provider", default=None, help="Optional: set auth_provider alongside --new-subject")
    parser.add_argument("--yes", action="store_true", help="Don't prompt")
    args = parser.parse_args()

    engine = _engine()
    Session = sessionmaker(bind=engine, future=True)
    from core.db import models

    with Session() as session:
        user = (
            session.query(models.User)
            .filter(models.User.email == args.email.strip().lower())
            .first()
        )
        if not user:
            print(f"No user found with email {args.email!r}", file=sys.stderr)
            return 1
        print(
            f"Current state: id={user.id} email={user.email} "
            f"external_subject={user.external_subject!r} "
            f"auth_provider={user.auth_provider!r}"
        )
        if args.clear:
            if not _confirm("Clear external_subject and auth_provider?", yes=args.yes):
                print("Aborted.")
                return 1
            user.external_subject = None
            user.auth_provider = None
        else:
            new_sub: Optional[str] = args.new_subject
            if not _confirm(f"Set external_subject={new_sub!r}?", yes=args.yes):
                print("Aborted.")
                return 1
            user.external_subject = new_sub
            if args.auth_provider is not None:
                user.auth_provider = args.auth_provider

        session.commit()
        session.refresh(user)
        print(
            f"New state: id={user.id} email={user.email} "
            f"external_subject={user.external_subject!r} "
            f"auth_provider={user.auth_provider!r}"
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
