"""CRUD operations — thin re-export facade.

All per-resource logic lives in ``core/db/repositories/``.
Existing callers (``from core.db import crud; crud.foo(...)``) continue to
work without modification via these re-exports.
"""
from __future__ import annotations

# bulk operations
from core.db.repositories.bulk_ops import (
    create_bulk_operation,
    get_bulk_operation,
    get_bulk_operations,
    update_bulk_operation,
)
# audit logs
from core.db.repositories.audits import (
    create_audit_log,
    get_audit_logs,
)
# agents and transcripts
from core.db.repositories.agents import (
    create_agent,
    get_agent,
    get_agent_by_name,
    get_agents,
    search_agents,
    update_agent,
    delete_agent,
    create_agent_transcript,
    get_agent_transcript,
    get_agent_transcripts_by_agent,
    get_agent_transcripts_by_conversation,
    update_agent_transcript,
    delete_agent_transcript,
)
# keywords
from core.db.repositories.keywords import (
    create_keyword,
    get_keyword,
    get_keyword_by_text,
    get_scoped_keyword_by_text,
    get_keywords,
    update_keyword,
    delete_keyword,
    create_memory_block_keyword,
    delete_memory_block_keyword,
    get_memory_block_keywords,
    get_keyword_memory_blocks,
    get_keyword_memory_blocks_count,
)
# memory blocks
from core.db.repositories.memory_blocks import (
    create_memory_block,
    get_memory_block,
    get_memory_blocks_by_agent,
    get_memory_blocks_by_conversation,
    get_all_memory_blocks,
    update_memory_block,
    archive_memory_block,
    delete_memory_block,
    retrieve_relevant_memories,
    report_memory_feedback,
    create_feedback_log,
    get_feedback_log,
    get_feedback_logs_by_memory_block,
    update_feedback_log,
    delete_feedback_log,
)
# organizations
from core.db.repositories.organizations import (
    create_organization,
    get_organization,
    get_organizations,
    update_organization,
    delete_organization,
    create_organization_member,
    get_organization_member,
    get_organization_members,
    update_organization_member,
    delete_organization_member,
    create_organization_invitation,
    get_organization_invitation,
    get_organization_invitations,
    update_organization_invitation,
    delete_organization_invitation,
)
# consolidation suggestions
from core.db.repositories.consolidation_suggestions import (
    ConsolidationOriginalMismatchError,
    create_consolidation_suggestion,
    get_consolidation_suggestion,
    get_consolidation_suggestions,
    get_consolidation_suggestions_scoped,
    update_consolidation_suggestion,
    delete_consolidation_suggestion,
    apply_consolidation,
)
# search
from core.services.search_service import search_memory_blocks_enhanced
