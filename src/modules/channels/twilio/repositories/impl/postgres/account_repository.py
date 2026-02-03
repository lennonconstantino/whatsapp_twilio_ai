import json
from typing import List, Optional

from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.core.utils import get_logger
from src.modules.channels.twilio.models.domain import TwilioAccount
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository

logger = get_logger(__name__)


class PostgresTwilioAccountRepository(PostgresRepository[TwilioAccount], TwilioAccountRepository):
    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "twilio_accounts", TwilioAccount)

    def find_by_owner(self, owner_id: str) -> Optional[TwilioAccount]:
        accounts = self.find_by({"owner_id": owner_id}, limit=1)
        return accounts[0] if accounts else None

    def find_by_account_sid(self, account_sid: str) -> Optional[TwilioAccount]:
        accounts = self.find_by({"account_sid": account_sid}, limit=1)
        return accounts[0] if accounts else None

    def find_by_phone_number(self, phone_number: str) -> Optional[TwilioAccount]:
        query = sql.SQL(
            "SELECT * FROM twilio_accounts "
            "WHERE phone_numbers @> %s::jsonb "
            "LIMIT 1"
        )
        payload = json.dumps([phone_number])
        with self.db.connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            try:
                cur.execute(query, (payload,))
                row = cur.fetchone()
                return self.model_class(**row) if row else None
            except Exception as e:
                logger.error(
                    "Error finding Twilio account by phone number", error=str(e)
                )
                raise
            finally:
                cur.close()

    def update_phone_numbers(
        self, tw_account_id: int, phone_numbers: List[str]
    ) -> Optional[TwilioAccount]:
        return self.update(
            tw_account_id, {"phone_numbers": phone_numbers}, id_column="tw_account_id"
        )

    def add_phone_number(
        self, tw_account_id: int, phone_number: str
    ) -> Optional[TwilioAccount]:
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
        account = self.find_by_id(tw_account_id, id_column="tw_account_id")
        if not account:
            return None
        phone_numbers = account.phone_numbers or []
        if phone_number in phone_numbers:
            phone_numbers.remove(phone_number)
            return self.update_phone_numbers(tw_account_id, phone_numbers)
        return account

