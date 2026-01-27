"""
Twilio Account repository for database operations.
"""

import json
from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.channels.twilio.models.domain import TwilioAccount

logger = get_logger(__name__)


class TwilioAccountRepository(SupabaseRepository[TwilioAccount]):
    """Repository for TwilioAccount entity operations."""

    def __init__(self, client: Client):
        """
        Initialize twilio account repository.
        Note: Primary key (tw_account_id) is still INTEGER, but foreign key
        (owner_id) is now ULID, so we enable validation.
        """
        super().__init__(client, "twilio_accounts", TwilioAccount, validates_ulid=True)

    def find_by_owner(self, owner_id: str) -> Optional[TwilioAccount]:
        """
        Find Twilio account by owner ID.
        owner_id is ULID, validated automatically.
        Args:
            owner_id: Owner ID

        Returns:
            TwilioAccount instance or None
        """
        accounts = self.find_by({"owner_id": owner_id}, limit=1)
        return accounts[0] if accounts else None

    def find_by_account_sid(self, account_sid: str) -> Optional[TwilioAccount]:
        """
        Find Twilio account by account SID.

        Args:
            account_sid: Twilio account SID

        Returns:
            TwilioAccount instance or None
        """
        accounts = self.find_by({"account_sid": account_sid}, limit=1)
        return accounts[0] if accounts else None

    def find_by_phone_number(self, phone_number: str) -> Optional[TwilioAccount]:
        """
        Find Twilio account by phone number.

        Args:
            phone_number: Phone number to search for

        Returns:
            TwilioAccount instance or None
        """
        try:
            # Note: For JSONB columns, we must pass a valid JSON string for 'contains' filter.
            # Passing a Python list directly results in Postgres Array syntax (curly braces)
            # which causes "invalid input syntax for type json".
            result = (
                self.client.table(self.table_name)
                .select("*")
                .contains("phone_numbers", json.dumps([phone_number]))
                .limit(1)
                .execute()
            )
            if result.data:
                return self.model_class(**result.data[0])
            return None
        except Exception as e:
            logger.error("Error finding Twilio account by phone number", error=str(e))
            raise

    def update_phone_numbers(
        self, tw_account_id: int, phone_numbers: List[str]
    ) -> Optional[TwilioAccount]:
        """
        Update Twilio account phone numbers.

        Args:
            tw_account_id: Twilio account ID
            phone_numbers: List of phone numbers

        Returns:
            Updated TwilioAccount instance or None
        """
        return self.update(
            tw_account_id, {"phone_numbers": phone_numbers}, id_column="tw_account_id"
        )

    def add_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        """
        Add a phone number to Twilio account.

        Args:
            tw_account_id: Twilio account ID
            phone_number: Phone number to add

        Returns:
            Updated TwilioAccount instance or None
        """
        account = self.find_by_id(tw_account_id, id_column="tw_account_id")
        if not account:
            return None

        phone_numbers = account.phone_numbers or []
        if phone_number not in phone_numbers:
            phone_numbers.append(phone_number)
            return self.update_phone_numbers(tw_account_id, phone_numbers)

        return account

    def remove_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        """
        Remove a phone number from Twilio account.

        Args:
            tw_account_id: Twilio account ID
            phone_number: Phone number to remove

        Returns:
            Updated TwilioAccount instance or None
        """
        account = self.find_by_id(tw_account_id, id_column="tw_account_id")
        if not account:
            return None

        phone_numbers = account.phone_numbers or []
        if phone_number in phone_numbers:
            phone_numbers.remove(phone_number)
            return self.update_phone_numbers(tw_account_id, phone_numbers)

        return account
