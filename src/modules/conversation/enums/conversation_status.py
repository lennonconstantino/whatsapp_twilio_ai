"""
Conversation status enumeration.

This module defines the possible states a conversation can be in,
both active and terminal.
"""

from enum import Enum


class ConversationStatus(Enum):
    """
    Enum for conversation status.

    Defines the state of the conversation lifecycle:

    Active States:
    - PENDING: Active conversation, awaiting interaction
    - PROGRESS: Conversation in progress

    Paused States:
    - IDLE_TIMEOUT: Conversation paused due to inactivity timeout

    Final States (Closed):
    - AGENT_CLOSED: Conversation closed by agent
    - SUPPORT_CLOSED: Conversation closed by support team
    - USER_CLOSED: Conversation closed by user
    - EXPIRED: Conversation automatically expired by system
    - FAILED: Conversation closed due to system failure
    """

    PENDING = "pending"
    PROGRESS = "progress"
    HUMAN_HANDOFF = "human_handoff"
    IDLE_TIMEOUT = "idle_timeout"
    AGENT_CLOSED = "agent_closed"
    SUPPORT_CLOSED = "support_closed"
    USER_CLOSED = "user_closed"
    EXPIRED = "expired"
    FAILED = "failed"

    @classmethod
    def active_statuses(cls):
        """
        Returns statuses considered as active.

        Active conversations can receive messages and transition to other states.
        """
        return [cls.PENDING, cls.PROGRESS, cls.HUMAN_HANDOFF]

    @classmethod
    def paused_statuses(cls):
        """
        Returns statuses considered as paused.

        Paused conversations are temporarily inactive but can be reactivated.
        """
        return [cls.IDLE_TIMEOUT]

    @classmethod
    def closed_statuses(cls):
        """
        Returns statuses considered as closed (final states).

        Closed conversations cannot be reactivated or modified.
        A new conversation must be created.
        """
        return [
            cls.AGENT_CLOSED,
            cls.SUPPORT_CLOSED,
            cls.USER_CLOSED,
            cls.EXPIRED,
            cls.FAILED,
        ]

    @classmethod
    def all_terminal_statuses(cls):
        """
        Returns all statuses where conversation is not actively progressing.

        Includes both paused and closed states.
        """
        return cls.paused_statuses() + cls.closed_statuses()

    def is_active(self):
        """Check if this status is active."""
        return self in self.active_statuses()

    def is_paused(self):
        """Check if this status is paused."""
        return self in self.paused_statuses()

    def is_closed(self):
        """Check if this status is closed (final)."""
        return self in self.closed_statuses()

    def can_receive_messages(self):
        """Check if conversation in this status can receive messages."""
        return self.is_active() or self.is_paused()

    def __repr__(self) -> str:
        return f"ConversationStatus.{self.name}"
