import json
from typing import List, Optional

from supabase import Client
from starlette.concurrency import run_in_threadpool

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.channels.twilio.models.domain import TwilioAccount
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository

logger = get_logger(__name__)


class SupabaseTwilioAccountRepository(SupabaseRepository[TwilioAccount], TwilioAccountRepository):
    """Supabase implementation of TwilioAccountRepository."""

    def __init__(self, client: Client):
        """
        Initialize twilio account repository.
        Note: Primary key (tw_account_id) is still INTEGER, but foreign key
        (owner_id) is now ULID, so we enable validation.
        """
        super().__init__(client, "twilio_accounts", TwilioAccount, validates_ulid=True)

    async def find_by_owner(self, owner_id: str) -> Optional[TwilioAccount]:
        """
        Find Twilio account by owner ID.
        owner_id is ULID, validated automatically.
        """
        def _find():
            accounts = self.find_by({"owner_id": owner_id}, limit=1)
            return accounts[0] if accounts else None
        
        return await run_in_threadpool(_find)

    async def find_by_account_sid(self, account_sid: str) -> Optional[TwilioAccount]:
        """
        Find Twilio account by account SID.
        """
        def _find():
            accounts = self.find_by({"account_sid": account_sid}, limit=1)
            return accounts[0] if accounts else None
        
        return await run_in_threadpool(_find)

    async def find_by_phone_number(self, phone_number: str) -> Optional[TwilioAccount]:
        """
        Find Twilio account by phone number.
        """
        def _find():
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
        
        return await run_in_threadpool(_find)

    async def update_phone_numbers(
        self, tw_account_id: int, phone_numbers: List[str]
    ) -> Optional[TwilioAccount]:
        """
        Update Twilio account phone numbers.
        """
        def _update():
            return self.update(
                tw_account_id, {"phone_numbers": phone_numbers}, id_column="tw_account_id"
            )
        
        return await run_in_threadpool(_update)

    async def add_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        """
        Add a phone number to Twilio account.
        """
        def _add():
            account = self.find_by_id(tw_account_id, id_column="tw_account_id")
            if not account:
                return None

            phone_numbers = account.phone_numbers or []
            if phone_number not in phone_numbers:
                phone_numbers.append(phone_number)
                return self.update(
                    tw_account_id, {"phone_numbers": phone_numbers}, id_column="tw_account_id"
                )

            return account
        
        return await run_in_threadpool(_add)

    async def remove_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        """
        Remove a phone number from Twilio account.
        """
        def _remove():
            account = self.find_by_id(tw_account_id, id_column="tw_account_id")
            if not account:
                return None

            phone_numbers = account.phone_numbers or []
            if phone_number in phone_numbers:
                phone_numbers.remove(phone_number)
                return self.update(
                    tw_account_id, {"phone_numbers": phone_numbers}, id_column="tw_account_id"
                )

            return account
        
        return await run_in_threadpool(_remove)
