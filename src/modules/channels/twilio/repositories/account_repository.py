from abc import ABC, abstractmethod
from typing import List, Optional

from src.modules.channels.twilio.models.domain import TwilioAccount


class TwilioAccountRepository(ABC):
    """
    Abstract Base Class for Twilio Account Repository.
    Defines the contract for Twilio account data access.
    """

    @abstractmethod
    def find_by_owner(self, owner_id: str) -> Optional[TwilioAccount]:
        """Find Twilio account by owner ID."""
        pass

    @abstractmethod
    def find_by_account_sid(self, account_sid: str) -> Optional[TwilioAccount]:
        """Find Twilio account by account SID."""
        pass

    @abstractmethod
    def find_by_phone_number(self, phone_number: str) -> Optional[TwilioAccount]:
        """Find Twilio account by phone number."""
        pass

    @abstractmethod
    def update_phone_numbers(
        self, tw_account_id: int, phone_numbers: List[str]
    ) -> Optional[TwilioAccount]:
        """Update Twilio account phone numbers."""
        pass

    @abstractmethod
    def add_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        """Add a phone number to Twilio account."""
        pass

    @abstractmethod
    def remove_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        """Remove a phone number from Twilio account."""
        pass
