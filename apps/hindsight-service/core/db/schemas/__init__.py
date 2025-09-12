"""
Domain-split Pydantic schemas with a compatibility aggregator.

This package re-exports the same names previously provided by
`core.db.schemas`.
"""

# Import order: define base/simple types first to satisfy forward refs
from .users import UserBase, UserCreate, User
from .organizations import (
    OrganizationBase,
    OrganizationCreate,
    OrganizationUpdate,
    Organization,
    OrganizationMemberBase,
    OrganizationMemberCreate,
    OrganizationMemberUpdate,
    OrganizationMember,
    OrganizationInvitationBase,
    OrganizationInvitationCreate,
    OrganizationInvitationUpdate,
    OrganizationInvitation,
)
from .agents import (
    AgentBase,
    AgentCreate,
    AgentUpdate,
    Agent,
    AgentTranscriptBase,
    AgentTranscriptCreate,
    AgentTranscriptUpdate,
    AgentTranscript,
)
from .keywords import KeywordBase, KeywordCreate, KeywordUpdate, Keyword
from .memory import (
    MemoryBlockBase,
    MemoryBlockCreate,
    MemoryBlockUpdate,
    MemoryBlock,
    MemoryBlockKeywordAssociation,
    FeedbackLogBase,
    FeedbackLogCreate,
    FeedbackLogUpdate,
    FeedbackLog,
    ConsolidationSuggestionBase,
    ConsolidationSuggestionCreate,
    ConsolidationSuggestionUpdate,
    ConsolidationSuggestion,
    PaginatedConsolidationSuggestions,
    PaginatedMemoryBlocks,
    MemoryBlockWithScore,
    SearchMetadata,
    PaginatedMemoryBlocksWithSearch,
    FulltextSearchRequest,
    SemanticSearchRequest,
    HybridSearchRequest,
)
from .audits import AuditLogBase, AuditLogCreate, AuditLog
from .bulk_ops import (
    BulkOperationBase,
    BulkOperationCreate,
    BulkOperation,
    BulkOperationUpdate,
)
from .notifications import (
    UserNotificationPreferenceBase,
    UserNotificationPreferenceCreate,
    UserNotificationPreferenceUpdate,
    UserNotificationPreference,
    NotificationBase,
    NotificationCreate,
    Notification,
    EmailNotificationLogBase,
    EmailNotificationLogCreate,
    EmailNotificationLog,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationStatsResponse,
)

# Resolve forward references across split modules (e.g., MemoryBlock -> Keyword)
try:  # pragma: no cover - safe rebuilds
    MemoryBlock.model_rebuild()
    MemoryBlockWithScore.model_rebuild()
except Exception:
    pass

__all__ = [
    # Users
    "UserBase",
    "UserCreate",
    "User",
    # Orgs
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationUpdate",
    "Organization",
    "OrganizationMemberBase",
    "OrganizationMemberCreate",
    "OrganizationMemberUpdate",
    "OrganizationMember",
    "OrganizationInvitationBase",
    "OrganizationInvitationCreate",
    "OrganizationInvitationUpdate",
    "OrganizationInvitation",
    # Agents
    "AgentBase",
    "AgentCreate",
    "AgentUpdate",
    "Agent",
    "AgentTranscriptBase",
    "AgentTranscriptCreate",
    "AgentTranscriptUpdate",
    "AgentTranscript",
    # Keywords
    "KeywordBase",
    "KeywordCreate",
    "KeywordUpdate",
    "Keyword",
    # Memory
    "MemoryBlockBase",
    "MemoryBlockCreate",
    "MemoryBlockUpdate",
    "MemoryBlock",
    "MemoryBlockKeywordAssociation",
    "FeedbackLogBase",
    "FeedbackLogCreate",
    "FeedbackLogUpdate",
    "FeedbackLog",
    "ConsolidationSuggestionBase",
    "ConsolidationSuggestionCreate",
    "ConsolidationSuggestionUpdate",
    "ConsolidationSuggestion",
    "PaginatedConsolidationSuggestions",
    "PaginatedMemoryBlocks",
    "MemoryBlockWithScore",
    "SearchMetadata",
    "PaginatedMemoryBlocksWithSearch",
    "FulltextSearchRequest",
    "SemanticSearchRequest",
    "HybridSearchRequest",
    # Audits
    "AuditLogBase",
    "AuditLogCreate",
    "AuditLog",
    # Bulk
    "BulkOperationBase",
    "BulkOperationCreate",
    "BulkOperation",
    "BulkOperationUpdate",
    # Notifications
    "UserNotificationPreferenceBase",
    "UserNotificationPreferenceCreate",
    "UserNotificationPreferenceUpdate",
    "UserNotificationPreference",
    "NotificationBase",
    "NotificationCreate",
    "Notification",
    "EmailNotificationLogBase",
    "EmailNotificationLogCreate",
    "EmailNotificationLog",
    "NotificationListResponse",
    "NotificationPreferencesResponse",
    "NotificationStatsResponse",
]
