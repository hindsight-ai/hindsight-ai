"""
Domain-split SQLAlchemy models with a compatibility aggregator.

This package exposes the same public API as the former
`core.db.models` module: `Base`, `now_utc`, and all ORM classes.
"""

from .base import Base, now_utc  # re-export

# Domain models
from .users import User
from .organizations import Organization, OrganizationMembership, OrganizationInvitation
from .agents import Agent, AgentTranscript
from .keywords import Keyword
from .memory import MemoryBlock, FeedbackLog, MemoryBlockKeyword, ConsolidationSuggestion
from .audit import AuditLog
from .bulk_ops import BulkOperation
from .notifications import UserNotificationPreference, Notification, EmailNotificationLog
from .tokens import PersonalAccessToken

__all__ = [
    # base
    "Base",
    "now_utc",
    # users/orgs
    "User",
    "Organization",
    "OrganizationMembership",
    "OrganizationInvitation",
    # agents
    "Agent",
    "AgentTranscript",
    # keywords/memory
    "Keyword",
    "MemoryBlock",
    "FeedbackLog",
    "MemoryBlockKeyword",
    "ConsolidationSuggestion",
    # audit/bulk
    "AuditLog",
    "BulkOperation",
    # notifications
    "UserNotificationPreference",
    "Notification",
    "EmailNotificationLog",
    # tokens
    "PersonalAccessToken",
]
