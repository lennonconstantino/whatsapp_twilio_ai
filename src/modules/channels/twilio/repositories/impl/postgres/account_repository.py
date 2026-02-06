import json
from typing import List, Optional

from psycopg2 import sql
# from psycopg2.extras import RealDictCursor # Removed

from src.core.database.postgres_async_repository import PostgresAsyncRepository
from src.core.database.postgres_async_session import AsyncPostgresDatabase
from src.core.utils import get_logger
from src.modules.channels.twilio.models.domain import TwilioAccount
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository

logger = get_logger(__name__)


class PostgresTwilioAccountRepository(PostgresAsyncRepository[TwilioAccount], TwilioAccountRepository):
    def __init__(self, db: AsyncPostgresDatabase):
        super().__init__(db, "twilio_accounts", TwilioAccount)

    async def create(self, data: dict) -> Optional[TwilioAccount]:
        """
        Override create to serialize phone_numbers to JSON string.
        Required because psycopg2 converts list to ARRAY, but column is JSONB.
        """
        if "phone_numbers" in data and isinstance(data["phone_numbers"], list):
            data = data.copy()
            data["phone_numbers"] = json.dumps(data["phone_numbers"])
        return await super().create(data)

    async def find_by_owner(self, owner_id: str) -> Optional[TwilioAccount]:
        accounts = await self.find_by({"owner_id": owner_id}, limit=1)
        return accounts[0] if accounts else None

    async def find_by_account_sid(self, account_sid: str) -> Optional[TwilioAccount]:
        accounts = await self.find_by({"account_sid": account_sid}, limit=1)
        return accounts[0] if accounts else None

    async def find_by_phone_number(self, phone_number: str) -> Optional[TwilioAccount]:
        # Using sql.SQL for query composition, placeholders will be converted by _execute_query logic 
        # (assuming it uses the helper I wrote in PostgresAsyncRepository)
        # But wait, PostgresAsyncRepository._convert_query_to_asyncpg handles %s.
        # Here we have %s::jsonb. My converter splits by %s. 
        # "WHERE phone_numbers @> %s::jsonb" -> "WHERE phone_numbers @> $1::jsonb"
        # This should work fine.
        
        query = sql.SQL(
            "SELECT * FROM twilio_accounts "
            "WHERE phone_numbers @> %s::jsonb "
            "LIMIT 1"
        )
        payload = json.dumps([phone_number])
        
        result = await self._execute_query(query, (payload,), fetch_one=True)
        return self.model_class(**result) if result else None

    async def update_phone_numbers(
        self, tw_account_id: int, phone_numbers: List[str]
    ) -> Optional[TwilioAccount]:
        return await self.update(
            tw_account_id, {"phone_numbers": json.dumps(phone_numbers)}, id_column="tw_account_id"
        )

    async def add_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        account = await self.find_by_id(tw_account_id, id_column="tw_account_id")
        if not account:
            return None
        phone_numbers = account.phone_numbers or []
        if phone_number not in phone_numbers:
            phone_numbers.append(phone_number)
            return await self.update_phone_numbers(tw_account_id, phone_numbers)
        return account

    async def remove_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
        account = await self.find_by_id(tw_account_id, id_column="tw_account_id")
        if not account:
            return None
        phone_numbers = account.phone_numbers or []
        if phone_number in phone_numbers:
            phone_numbers.remove(phone_number)
            return await self.update_phone_numbers(tw_account_id, phone_numbers)
        return account
