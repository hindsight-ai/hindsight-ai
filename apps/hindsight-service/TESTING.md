# Testing Guide

## Permission Context Fixtures
New pytest fixtures provide quick user/org setups:
- `user_factory(email, is_superadmin=False)` -> User
- `organization_factory(name)` -> Organization
- `membership_factory(org, user, role='owner', can_read=True, can_write=True)` -> OrganizationMembership
- `superadmin_context` -> superadmin user
- `org_owner_context` -> (user, org) with owner role
- `editor_context` -> (user, org) editor role
- `viewer_context` -> (user, org) viewer role

Use these to avoid manual mocks of `_require_current_user`. Build real DB state then issue requests with appropriate headers matching created user email.

Example:
```
 def test_create_agent_in_org(client, user_factory, organization_factory, membership_factory):
     user = user_factory("alice@example.com")
     org = organization_factory("Org A")
     membership_factory(org, user, role='editor', can_write=True)
     headers = {"x-auth-request-email": user.email, "x-auth-request-user": user.display_name}
     resp = client.post("/agents/", json={"agent_name": "foo", "visibility_scope": "organization", "organization_id": str(org.id)}, headers=headers)
     assert resp.status_code == 201
```

## Coverage Gate Relaxation
Set `HINDSIGHT_RELAX_COVERAGE=true` locally to signal tooling that fail-under may be skipped for focused iterations. (Current implementation is a placeholder; integrate with a future pytest plugin or conditional addopts block.)

## Focused Test Runs
Run single tests with:
```
uv run pytest path/to/test_file.py::test_name -q
```

## Notes
- Fixtures in both `tests/integration/conftest.py` and `tests/fixtures/conftest.py` for compatibility; prefer the integration one going forward.
- Avoid patching `_require_current_user`; rely on real model records for clearer permission validation.
