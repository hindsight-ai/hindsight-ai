"""
Script to update existing organization members' permissions based on their roles.
This ensures that editor/admin/owner roles have can_write=true and all roles have can_read=true.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.database import get_db
from core.db.models import OrganizationMembership
from core.utils.role_permissions import get_role_permissions

def update_member_permissions():
    """Update permissions for all existing organization members based on their roles."""
    db = next(get_db())

    try:
        # Get all organization memberships
        memberships = db.query(OrganizationMembership).all()

        updated_count = 0
        for membership in memberships:
            old_can_read = membership.can_read
            old_can_write = membership.can_write

            # Get the correct permissions for this role using the dynamic system
            try:
                role_permissions = get_role_permissions(membership.role)
                new_can_read = role_permissions["can_read"]
                new_can_write = role_permissions["can_write"]
            except ValueError as e:
                print(f"Warning: {e}. Skipping member {membership.user_id}")
                continue

            # Only update if permissions changed
            if old_can_read != new_can_read or old_can_write != new_can_write:
                membership.can_read = new_can_read
                membership.can_write = new_can_write
                updated_count += 1
                print(f"Updated member {membership.user_id} in org {membership.organization_id}: "
                      f"role={membership.role}, can_read={new_can_read}, can_write={new_can_write}")

        if updated_count > 0:
            db.commit()
            print(f"\nSuccessfully updated permissions for {updated_count} members")
        else:
            db.commit()  # Commit even if no updates were needed
            print("\nNo members needed permission updates")

    except Exception as e:
        db.rollback()
        print(f"Error updating member permissions: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_member_permissions()
