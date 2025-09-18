# Architecture Overview

## Project Layout

```
.
.github
.github/workflows
.pytest_cache
.pytest_cache/v
.pytest_cache/v/cache
apps
apps/hindsight-dashboard
apps/hindsight-dashboard/coverage
apps/hindsight-dashboard/coverage/api
apps/hindsight-dashboard/coverage/components
apps/hindsight-dashboard/coverage/lcov-report
apps/hindsight-dashboard/coverage/lcov-report/api
apps/hindsight-dashboard/coverage/lcov-report/services
apps/hindsight-dashboard/coverage/services
apps/hindsight-dashboard/dist
apps/hindsight-dashboard/dist/assets
apps/hindsight-dashboard/public
apps/hindsight-dashboard/src
apps/hindsight-dashboard/src/api
apps/hindsight-dashboard/src/api/__tests__
apps/hindsight-dashboard/src/assets
apps/hindsight-dashboard/src/components
apps/hindsight-dashboard/src/components/__tests__
apps/hindsight-dashboard/src/context
apps/hindsight-dashboard/src/context/__tests__
apps/hindsight-dashboard/src/hooks
apps/hindsight-dashboard/src/services
apps/hindsight-dashboard/src/services/__tests__
apps/hindsight-dashboard/src/types
apps/hindsight-service
  - app.py
  - cleanup_keywords.py
  - debug_memberships.py
  - main.py
  - test_email_notifications.py
  - test_external_email.py
  - test_live_email.py
  - test_notification_flow.py
  - test_role_permissions.py
  - test_transactional_email.py
  - update_member_permissions.py
apps/hindsight-service/.pytest_cache
apps/hindsight-service/.pytest_cache/v
apps/hindsight-service/.pytest_cache/v/cache
apps/hindsight-service/.venv-e2e
apps/hindsight-service/.venv-e2e/bin
apps/hindsight-service/.venv-e2e/include
apps/hindsight-service/.venv-e2e/include/python3.13
apps/hindsight-service/.venv-e2e/lib
apps/hindsight-service/.venv-e2e/lib/python3.13
apps/hindsight-service/.venv-e2e/lib/python3.13/site-packages
apps/hindsight-service/core
  - async_bulk_operations.py
  - audit.py
apps/hindsight-service/core/api
  - agents.py
  - audits.py
  - auth.py
  - bulk_operations.py
  - consolidation.py
  - deps.py
  - keywords.py
  - main.py
  - memory_blocks.py
  - memory_optimization.py
  - notifications.py
  - orgs.py
  - permissions.py
  - support.py
  - users.py
apps/hindsight-service/core/core
  - __init__.py
  - consolidation_worker.py
apps/hindsight-service/core/db
  - crud.py
  - database.py
  - scope_utils.py
  - sqlite_compiler_shims.py
apps/hindsight-service/core/db/models
  - __init__.py
  - agents.py
  - audit.py
  - base.py
  - bulk_ops.py
  - keywords.py
  - memory.py
  - notifications.py
  - organizations.py
  - users.py
apps/hindsight-service/core/db/repositories
  - __init__.py
  - agents.py
  - audits.py
  - bulk_ops.py
  - keywords.py
  - memory_blocks.py
  - organizations.py
apps/hindsight-service/core/db/schemas
  - __init__.py
  - agents.py
  - audits.py
  - bulk_ops.py
  - keywords.py
  - memory.py
  - notifications.py
  - organizations.py
  - users.py
apps/hindsight-service/core/pruning
  - __init__.py
  - compression_service.py
  - pruning_service.py
apps/hindsight-service/core/search
  - __init__.py
apps/hindsight-service/core/services
  - __init__.py
  - email_service.py
  - notification_service.py
  - search_service.py
  - transactional_email_service.py
apps/hindsight-service/core/templates
apps/hindsight-service/core/templates/email
apps/hindsight-service/core/utils
  - keywords.py
  - role_permissions.py
  - scopes.py
  - urls.py
apps/hindsight-service/core/workers
  - __init__.py
  - async_bulk_operations.py
  - consolidation_worker.py
apps/hindsight-service/docs
apps/hindsight-service/docs/consolidation_feature
apps/hindsight-service/hindsight_service.egg-info
apps/hindsight-service/logs
apps/hindsight-service/migrations
  - env.py
apps/hindsight-service/migrations/versions
  - 14cd01c502f8_rename_memory_id_to_id_in_memory_blocks_.py
  - 225790e00d26_align_metadata_column_and_indexes_in_.py
  - 251ad5240261_fix_search_vector_column_type.py
  - 2a9c8674c949_add_pg_trgm_extension_for_fuzzy_search.py
  - 39b55ecbd958_add_notification_system_tables.py
  - 3f0b9c7a1c00_add_users_orgs_and_scoped_governance.py
  - 456789012345_add_archived_at_timestamp_to_memoryblock.py
  - 57a3b3cd5572_add_retrieval_count_to_memoryblock.py
  - 5bfbd21a9d4d_add_audit_logs_table.py
  - 85f1accd00c7_add_bulk_operations_table.py
  - 975d4a80651a_add_consolidation_suggestions_table.py
  - a17d8c8efa28_base_revision_for_initial_schema.py
  - bdec54c35ae4_add_archived_column_to_memoryblock.py
  - c90352561e56_align_metadata_column_in_memory_blocks_.py
  - d65131155346_add_full_text_search_support_for_memory_.py
  - f59d6b564160_add_organization_invitations_table.py
apps/hindsight-service/tests
  - __init__.py
  - conftest.py
apps/hindsight-service/tests/e2e
  - __init__.py
  - test_migrations_downgrade_chain.py
  - test_migrations_stepwise.py
  - test_permissions_agents_keywords.py
  - test_permissions_basic.py
  - test_permissions_extended.py
  - utils_pg.py
apps/hindsight-service/tests/fixtures
  - __init__.py
  - conftest.py
apps/hindsight-service/tests/integration
  - __init__.py
  - conftest.py
  - test_archived_memory_blocks_regression.py
  - test_archived_visibility_debug.py
  - test_archived_with_data.py
  - test_async_bulk_coverage.py
  - test_bulk_operations_coverage.py
  - test_coverage_boost.py
  - test_crud_coverage.py
  - test_final_80_percent_push.py
  - test_final_coverage_push.py
  - test_main_endpoints.py
  - test_main_scope_change_coverage.py
  - test_memory_blocks_frontend_regression.py
  - test_memory_optimization_coverage.py
  - test_scope_utils_coverage.py
apps/hindsight-service/tests/integration/agents
  - __init__.py
  - test_agents_additional.py
  - test_agents_api.py
  - test_agents_crud.py
apps/hindsight-service/tests/integration/bulk_operations
  - __init__.py
  - test_bulk_operations.py
  - test_bulk_operations_api.py
  - test_bulk_operations_audit.py
  - test_bulk_operations_crud.py
  - test_bulk_operations_filters.py
  - test_bulk_operations_worker.py
apps/hindsight-service/tests/integration/keywords
  - __init__.py
  - test_keyword_audit.py
  - test_keyword_extraction.py
  - test_keywords_additional.py
  - test_keywords_api.py
  - test_keywords_crud.py
apps/hindsight-service/tests/integration/memory_blocks
  - __init__.py
  - test_compression_api.py
  - test_compression_service.py
  - test_consolidation_suggestions.py
  - test_consolidation_worker.py
  - test_memory_blocks_additional.py
  - test_memory_blocks_advanced.py
  - test_memory_blocks_api.py
  - test_memory_blocks_crud.py
  - test_memory_optimization.py
  - test_memory_optimization_api.py
  - test_memory_optimization_suggestions.py
  - test_pruning_service_db.py
apps/hindsight-service/tests/integration/notifications
  - test_notifications_api.py
apps/hindsight-service/tests/integration/organizations
  - __init__.py
  - test_dynamic_role_permissions.py
  - test_invitations_audit.py
  - test_invitations_crud.py
  - test_invitations_negative.py
  - test_member_addition_regression.py
  - test_member_notifications.py
  - test_member_notifications_fixed.py
  - test_memberships_crud.py
  - test_org_membership_roles.py
  - test_organizations_additional.py
  - test_organizations_api.py
apps/hindsight-service/tests/integration/permissions
  - __init__.py
  - test_audit_logs.py
  - test_audit_logs_filters.py
  - test_audits_api.py
  - test_auth_additional.py
  - test_permissions.py
  - test_scope_changes_audit.py
  - test_scope_filters.py
apps/hindsight-service/tests/integration/search
  - __init__.py
  - test_search_api.py
  - test_search_hybrid.py
apps/hindsight-service/tests/unit
  - test_agent_crud.py
  - test_async_bulk_operations.py
  - test_audit_logging.py
  - test_audits_api_smoke.py
  - test_auth_deps.py
  - test_bulk_operations_planning.py
  - test_bulk_ops_api_smoke.py
  - test_database_coverage.py
  - test_email_service.py
  - test_keyword_association_api_smoke.py
  - test_keyword_crud.py
  - test_main_middleware.py
  - test_memory_block_crud.py
  - test_memory_blocks_actions_smoke.py
  - test_memory_optimization_api_smoke.py
  - test_notification_service.py
  - test_notification_service_extra.py
  - test_notification_service_smoke_extra.py
  - test_notifications_api_smoke.py
  - test_org_invitations_api_smoke.py
  - test_organization_access_control.py
  - test_permissions.py
  - test_permissions_helpers.py
  - test_pruning_service_mock.py
  - test_repositories_smoke.py
  - test_role_permissions.py
  - test_role_permissions_script.py
  - test_scope_utils.py
  - test_search_service.py
  - test_support_endpoints.py
  - test_transactional_email_service_extra.py
config
docs
docs/adr
hindsight_db_backups
hindsight_db_backups/data
infra
infra/helper_scripts
infra/migrations
infra/postgres
infra/scripts
mcp-servers
mcp-servers/hindsight-mcp
mcp-servers/hindsight-mcp/src
mcp-servers/hindsight-mcp/src/client
scripts
  - generate_architecture_docs.py
templates
```

## Python Modules and Docstrings

- `apps/hindsight-service/app.py`: App assembly entry point.
- `apps/hindsight-service/cleanup_keywords.py`: Maintenance script to normalize and de-duplicate keywords.
- `apps/hindsight-service/core/api/agents.py`: Agents API endpoints.
- `apps/hindsight-service/core/api/audits.py`: Audit log API endpoints.
- `apps/hindsight-service/core/api/auth.py`: Authentication helpers and identity resolution.
- `apps/hindsight-service/core/api/bulk_operations.py`: Bulk operations API endpoints.
- `apps/hindsight-service/core/api/consolidation.py`: Consolidation endpoints.
- `apps/hindsight-service/core/api/deps.py`: API dependency helpers.
- `apps/hindsight-service/core/api/keywords.py`: Keywords API endpoints.
- `apps/hindsight-service/core/api/main.py`: FastAPI application assembly and high-level routes.
- `apps/hindsight-service/core/api/memory_blocks.py`: Memory blocks API endpoints.
- `apps/hindsight-service/core/api/memory_optimization.py`: Memory optimization endpoints.
- `apps/hindsight-service/core/api/notifications.py`: Notification API Endpoints
- `apps/hindsight-service/core/api/orgs.py`: Organizations API endpoints.
- `apps/hindsight-service/core/api/permissions.py`: Simplified permission system for resource access control.
- `apps/hindsight-service/core/api/support.py`: Support and build information endpoints.
- `apps/hindsight-service/core/api/users.py`: Users API endpoints.
- `apps/hindsight-service/core/async_bulk_operations.py`: Improved async bulk operations system.
- `apps/hindsight-service/core/audit.py`: Audit logging helpers and enums.
- `apps/hindsight-service/core/core/__init__.py`: Back-compat shims and selected workers.
- `apps/hindsight-service/core/core/consolidation_worker.py`: Shim for backward compatibility with tests and legacy imports.
- `apps/hindsight-service/core/db/crud.py`: CRUD operations for ORM models.
- `apps/hindsight-service/core/db/database.py`: Database engine and session management.
- `apps/hindsight-service/core/db/models/__init__.py`: Domain-split SQLAlchemy models with a compatibility aggregator.
- `apps/hindsight-service/core/db/models/agents.py`: (no module docstring)
- `apps/hindsight-service/core/db/models/audit.py`: (no module docstring)
- `apps/hindsight-service/core/db/models/base.py`: Shared SQLAlchemy base and helpers.
- `apps/hindsight-service/core/db/models/bulk_ops.py`: (no module docstring)
- `apps/hindsight-service/core/db/models/keywords.py`: (no module docstring)
- `apps/hindsight-service/core/db/models/memory.py`: (no module docstring)
- `apps/hindsight-service/core/db/models/notifications.py`: (no module docstring)
- `apps/hindsight-service/core/db/models/organizations.py`: (no module docstring)
- `apps/hindsight-service/core/db/models/users.py`: (no module docstring)
- `apps/hindsight-service/core/db/repositories/__init__.py`: Per-domain repository modules for database access.
- `apps/hindsight-service/core/db/repositories/agents.py`: Agent repository functions.
- `apps/hindsight-service/core/db/repositories/audits.py`: Audit log repository functions.
- `apps/hindsight-service/core/db/repositories/bulk_ops.py`: Bulk operations repository functions.
- `apps/hindsight-service/core/db/repositories/keywords.py`: Keyword repository functions.
- `apps/hindsight-service/core/db/repositories/memory_blocks.py`: Memory block repository functions.
- `apps/hindsight-service/core/db/repositories/organizations.py`: Organization repository functions.
- `apps/hindsight-service/core/db/schemas/__init__.py`: Domain-split Pydantic schemas with a compatibility aggregator.
- `apps/hindsight-service/core/db/schemas/agents.py`: (no module docstring)
- `apps/hindsight-service/core/db/schemas/audits.py`: (no module docstring)
- `apps/hindsight-service/core/db/schemas/bulk_ops.py`: (no module docstring)
- `apps/hindsight-service/core/db/schemas/keywords.py`: (no module docstring)
- `apps/hindsight-service/core/db/schemas/memory.py`: (no module docstring)
- `apps/hindsight-service/core/db/schemas/notifications.py`: (no module docstring)
- `apps/hindsight-service/core/db/schemas/organizations.py`: (no module docstring)
- `apps/hindsight-service/core/db/schemas/users.py`: (no module docstring)
- `apps/hindsight-service/core/db/scope_utils.py`: Scope filtering utilities for data governance.
- `apps/hindsight-service/core/db/sqlite_compiler_shims.py`: SQLite compilation shims for PostgreSQL-specific SQLAlchemy types.
- `apps/hindsight-service/core/pruning/__init__.py`: Pruning services package.
- `apps/hindsight-service/core/pruning/compression_service.py`: Memory Compression Service for Hindsight AI
- `apps/hindsight-service/core/pruning/pruning_service.py`: Memory Pruning Service for Hindsight AI
- `apps/hindsight-service/core/search/__init__.py`: Search module compatibility shim.
- `apps/hindsight-service/core/services/__init__.py`: Business logic services package.
- `apps/hindsight-service/core/services/email_service.py`: Email Service
- `apps/hindsight-service/core/services/notification_service.py`: Notification Service
- `apps/hindsight-service/core/services/search_service.py`: Advanced search service for memory blocks.
- `apps/hindsight-service/core/services/transactional_email_service.py`: Transactional Email Service
- `apps/hindsight-service/core/utils/keywords.py`: Lightweight keyword extraction utilities used by repositories.
- `apps/hindsight-service/core/utils/role_permissions.py`: Role-based permission utilities for organization members.
- `apps/hindsight-service/core/utils/scopes.py`: Visibility scope constants and helpers.
- `apps/hindsight-service/core/utils/urls.py`: URL utilities for building absolute links in emails and notifications.
- `apps/hindsight-service/core/workers/__init__.py`: Workers package for background/long-running tasks.
- `apps/hindsight-service/core/workers/async_bulk_operations.py`: Workers namespace shim for async bulk operations.
- `apps/hindsight-service/core/workers/consolidation_worker.py`: Consolidation Worker for Hindsight AI
- `apps/hindsight-service/debug_memberships.py`: Debugging script for inspecting users, organizations, and memberships.
- `apps/hindsight-service/main.py`: CLI entry for the service package when executed directly.
- `apps/hindsight-service/migrations/env.py`: (no module docstring)
- `apps/hindsight-service/migrations/versions/14cd01c502f8_rename_memory_id_to_id_in_memory_blocks_.py`: Rename memory_id to id in memory_blocks table
- `apps/hindsight-service/migrations/versions/225790e00d26_align_metadata_column_and_indexes_in_.py`: Align metadata column and indexes in memory_blocks table
- `apps/hindsight-service/migrations/versions/251ad5240261_fix_search_vector_column_type.py`: fix_search_vector_column_type
- `apps/hindsight-service/migrations/versions/2a9c8674c949_add_pg_trgm_extension_for_fuzzy_search.py`: Add pg_trgm extension for fuzzy search
- `apps/hindsight-service/migrations/versions/39b55ecbd958_add_notification_system_tables.py`: add notification system tables
- `apps/hindsight-service/migrations/versions/3f0b9c7a1c00_add_users_orgs_and_scoped_governance.py`: Add users/orgs tables and scoped governance columns + indexes
- `apps/hindsight-service/migrations/versions/456789012345_add_archived_at_timestamp_to_memoryblock.py`: Add archived_at timestamp to MemoryBlock
- `apps/hindsight-service/migrations/versions/57a3b3cd5572_add_retrieval_count_to_memoryblock.py`: Add retrieval_count to MemoryBlock
- `apps/hindsight-service/migrations/versions/5bfbd21a9d4d_add_audit_logs_table.py`: add audit logs table
- `apps/hindsight-service/migrations/versions/85f1accd00c7_add_bulk_operations_table.py`: add bulk operations table
- `apps/hindsight-service/migrations/versions/975d4a80651a_add_consolidation_suggestions_table.py`: Add consolidation_suggestions table
- `apps/hindsight-service/migrations/versions/a17d8c8efa28_base_revision_for_initial_schema.py`: Base revision for initial schema
- `apps/hindsight-service/migrations/versions/bdec54c35ae4_add_archived_column_to_memoryblock.py`: Add archived column to MemoryBlock
- `apps/hindsight-service/migrations/versions/c90352561e56_align_metadata_column_in_memory_blocks_.py`: Initial schema creation
- `apps/hindsight-service/migrations/versions/d65131155346_add_full_text_search_support_for_memory_.py`: Add full-text search support for memory blocks
- `apps/hindsight-service/migrations/versions/f59d6b564160_add_organization_invitations_table.py`: add organization invitations table
- `apps/hindsight-service/test_email_notifications.py`: Email Notification Test Script
- `apps/hindsight-service/test_external_email.py`: Email Test with Different Recipient
- `apps/hindsight-service/test_live_email.py`: Live Email Test Script
- `apps/hindsight-service/test_notification_flow.py`: End-to-End Notification System Test
- `apps/hindsight-service/test_role_permissions.py`: Test script for the dynamic role-based permission system.
- `apps/hindsight-service/test_transactional_email.py`: Transactional Email Service Test Script
- `apps/hindsight-service/tests/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/conftest.py`: (no module docstring)
- `apps/hindsight-service/tests/e2e/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/e2e/test_migrations_downgrade_chain.py`: (no module docstring)
- `apps/hindsight-service/tests/e2e/test_migrations_stepwise.py`: (no module docstring)
- `apps/hindsight-service/tests/e2e/test_permissions_agents_keywords.py`: (no module docstring)
- `apps/hindsight-service/tests/e2e/test_permissions_basic.py`: (no module docstring)
- `apps/hindsight-service/tests/e2e/test_permissions_extended.py`: (no module docstring)
- `apps/hindsight-service/tests/e2e/utils_pg.py`: (no module docstring)
- `apps/hindsight-service/tests/fixtures/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/fixtures/conftest.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/agents/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/agents/test_agents_additional.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/agents/test_agents_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/agents/test_agents_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/bulk_operations/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/bulk_operations/test_bulk_operations.py`: Integration tests for bulk operations using real database fixtures.
- `apps/hindsight-service/tests/integration/bulk_operations/test_bulk_operations_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/bulk_operations/test_bulk_operations_audit.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/bulk_operations/test_bulk_operations_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/bulk_operations/test_bulk_operations_filters.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/bulk_operations/test_bulk_operations_worker.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/conftest.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/keywords/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/keywords/test_keyword_audit.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/keywords/test_keyword_extraction.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/keywords/test_keywords_additional.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/keywords/test_keywords_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/keywords/test_keywords_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_compression_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_compression_service.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_consolidation_suggestions.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_consolidation_worker.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_memory_blocks_additional.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_memory_blocks_advanced.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_memory_blocks_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_memory_blocks_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_memory_optimization.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_memory_optimization_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_memory_optimization_suggestions.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/memory_blocks/test_pruning_service_db.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/notifications/test_notifications_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_dynamic_role_permissions.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_invitations_audit.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_invitations_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_invitations_negative.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_member_addition_regression.py`: Regression tests for organization member addition with notifications.
- `apps/hindsight-service/tests/integration/organizations/test_member_notifications.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_member_notifications_fixed.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_memberships_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_org_membership_roles.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_organizations_additional.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/organizations/test_organizations_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/test_audit_logs.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/test_audit_logs_filters.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/test_audits_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/test_auth_additional.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/test_permissions.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/test_scope_changes_audit.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/permissions/test_scope_filters.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/search/__init__.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/search/test_search_api.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/search/test_search_hybrid.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/test_archived_memory_blocks_regression.py`: Test to reproduce and prevent regression of archived memory blocks frontend issue.
- `apps/hindsight-service/tests/integration/test_archived_visibility_debug.py`: Test to debug the archived memory blocks visibility issue.
- `apps/hindsight-service/tests/integration/test_archived_with_data.py`: Test archived endpoint with actual data to verify it works properly.
- `apps/hindsight-service/tests/integration/test_async_bulk_coverage.py`: Targeted tests for async_bulk_operations.py and other high-impact uncovered lines.
- `apps/hindsight-service/tests/integration/test_bulk_operations_coverage.py`: Targeted tests for bulk_operations.py to improve coverage.
- `apps/hindsight-service/tests/integration/test_coverage_boost.py`: Simple focused tests to improve coverage of key modules
- `apps/hindsight-service/tests/integration/test_crud_coverage.py`: Tests for core CRUD operations to improve coverage
- `apps/hindsight-service/tests/integration/test_final_80_percent_push.py`: Final targeted tests to push coverage from ~75% to 80%.
- `apps/hindsight-service/tests/integration/test_final_coverage_push.py`: Final push tests to reach 80% coverage - targeting specific missing lines
- `apps/hindsight-service/tests/integration/test_main_endpoints.py`: (no module docstring)
- `apps/hindsight-service/tests/integration/test_main_scope_change_coverage.py`: Targeted tests for main.py scope change functionality to improve coverage.
- `apps/hindsight-service/tests/integration/test_memory_blocks_frontend_regression.py`: Test to reproduce and prevent regression of frontend memory blocks loading issue.
- `apps/hindsight-service/tests/integration/test_memory_optimization_coverage.py`: Targeted tests for memory_optimization.py to improve coverage.
- `apps/hindsight-service/tests/integration/test_scope_utils_coverage.py`: Tests for scope_utils to improve coverage
- `apps/hindsight-service/tests/unit/test_agent_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_async_bulk_operations.py`: Unit tests for the async_bulk_operations module.
- `apps/hindsight-service/tests/unit/test_audit_logging.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_audits_api_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_auth_deps.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_bulk_operations_planning.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_bulk_ops_api_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_database_coverage.py`: Targeted tests for database.py to improve coverage.
- `apps/hindsight-service/tests/unit/test_email_service.py`: Tests for email template functionality and transactional email service.
- `apps/hindsight-service/tests/unit/test_keyword_association_api_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_keyword_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_main_middleware.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_memory_block_crud.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_memory_blocks_actions_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_memory_optimization_api_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_notification_service.py`: Unit tests for the NotificationService class.
- `apps/hindsight-service/tests/unit/test_notification_service_extra.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_notification_service_smoke_extra.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_notifications_api_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_org_invitations_api_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_organization_access_control.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_permissions.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_permissions_helpers.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_pruning_service_mock.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_repositories_smoke.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_role_permissions.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_role_permissions_script.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_scope_utils.py`: Tests for core.db.scope_utils module.
- `apps/hindsight-service/tests/unit/test_search_service.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_support_endpoints.py`: (no module docstring)
- `apps/hindsight-service/tests/unit/test_transactional_email_service_extra.py`: (no module docstring)
- `apps/hindsight-service/update_member_permissions.py`: Script to update existing organization members' permissions based on their roles.
- `scripts/generate_architecture_docs.py`: Generate architecture documentation for the repository.
