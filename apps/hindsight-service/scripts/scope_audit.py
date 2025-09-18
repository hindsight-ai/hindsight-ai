#!/usr/bin/env python3
"""
Scope Audit Script

Scans key tables for scoping anomalies and prints a concise report:
- visibility_scope NULL or invalid values
- Missing owner/org based on scope semantics
- Potentially extraneous owner/org on public/personal rows

Reads database URL from (in order):
- DATABASE_URL
- TEST_DATABASE_URL
- Constructed from POSTGRES_* env vars (postgresql://user:pass@host:port/db)

Usage:
  python scripts/scope_audit.py [--json]

Exit code is 0; this is an audit tool only.
"""
from __future__ import annotations
import os
import json
from dataclasses import dataclass
from typing import Any, Dict
from sqlalchemy import create_engine, text


def _env_db_url() -> str:
    url = os.getenv('DATABASE_URL') or os.getenv('TEST_DATABASE_URL')
    if url:
        return url
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    db = os.getenv('POSTGRES_DB', 'postgres')
    if password:
        return f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return f"postgresql://{user}@{host}:{port}/{db}"


def _q(conn, sql: str) -> int:
    r = conn.execute(text(sql))
    row = r.fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def audit_table(conn, table: str) -> Dict[str, Any]:
    valid_scopes = "('personal','organization','public')"
    res: Dict[str, Any] = {}
    res['total'] = _q(conn, f"SELECT COUNT(*) FROM {table}")
    res['null_scope'] = _q(conn, f"SELECT COUNT(*) FROM {table} WHERE visibility_scope IS NULL")
    res['invalid_scope'] = _q(conn, f"SELECT COUNT(*) FROM {table} WHERE visibility_scope IS NOT NULL AND visibility_scope NOT IN {valid_scopes}")

    # Scope-specific checks; tables share column names
    # Personal
    res['personal_missing_owner'] = _q(conn, f"SELECT COUNT(*) FROM {table} WHERE visibility_scope='personal' AND owner_user_id IS NULL")
    res['personal_has_org'] = _q(conn, f"SELECT COUNT(*) FROM {table} WHERE visibility_scope='personal' AND organization_id IS NOT NULL")
    # Organization
    res['org_missing_org'] = _q(conn, f"SELECT COUNT(*) FROM {table} WHERE visibility_scope='organization' AND organization_id IS NULL")
    res['org_has_owner'] = _q(conn, f"SELECT COUNT(*) FROM {table} WHERE visibility_scope='organization' AND owner_user_id IS NOT NULL")
    # Public
    res['public_has_owner_or_org'] = _q(conn, f"SELECT COUNT(*) FROM {table} WHERE visibility_scope='public' AND (owner_user_id IS NOT NULL OR organization_id IS NOT NULL)")
    return res


@dataclass
class AuditReport:
    memory_blocks: Dict[str, Any]
    keywords: Dict[str, Any]
    agents: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({
            'memory_blocks': self.memory_blocks,
            'keywords': self.keywords,
            'agents': self.agents,
        }, indent=2)

    def pretty(self) -> str:
        def block(name, d):
            lines = [f"{name}:", f"  total: {d['total']}"]
            for k in ('null_scope','invalid_scope','personal_missing_owner','personal_has_org','org_missing_org','org_has_owner','public_has_owner_or_org'):
                lines.append(f"  {k}: {d[k]}")
            return "\n".join(lines)
        return "\n".join([
            block('memory_blocks', self.memory_blocks),
            block('keywords', self.keywords),
            block('agents', self.agents),
        ])


def main():
    as_json = '--json' in os.sys.argv
    url = _env_db_url()
    engine = create_engine(url, future=True)
    with engine.connect() as conn:
        report = AuditReport(
            memory_blocks=audit_table(conn, 'memory_blocks'),
            keywords=audit_table(conn, 'keywords'),
            agents=audit_table(conn, 'agents'),
        )
    print(report.to_json() if as_json else report.pretty())


if __name__ == '__main__':
    main()

