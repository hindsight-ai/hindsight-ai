"""
Debugging script for inspecting users, organizations, and memberships.

Connects to the configured database, lists entities, and exercises
`get_user_memberships` output for quick diagnostics.
"""
import os
import sys
from sqlalchemy.orm import Session
from core.db.database import get_db
from core.db.models import OrganizationMembership, Organization, User
from core.api.auth import get_user_memberships

# Set up test db env like tests do
os.environ["DATABASE_URL"] = "postgresql://testuser:testpass@localhost:5432/testdb"

# Get a db session
db_gen = get_db()
db = next(db_gen)

print("=== All Users ===")
users = db.query(User).all()
for user in users:
    print(f"User: {user.email} (id: {user.id})")

print("\n=== All Organizations ===")
orgs = db.query(Organization).all()
for org in orgs:
    print(f"Org: {org.name} (id: {org.id}, created_by: {org.created_by})")

print("\n=== All Memberships ===")
memberships = db.query(OrganizationMembership).all()
for m in memberships:
    print(f"Membership: user_id={m.user_id}, org_id={m.organization_id}, role={m.role}")

print("\n=== Testing get_user_memberships ===")
if users:
    user = users[0]
    memberships = get_user_memberships(db, user.id)
    print(f"get_user_memberships for {user.email}: {memberships}")

db.close()
