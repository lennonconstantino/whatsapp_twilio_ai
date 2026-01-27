from typing import Optional

from src.core.config import settings
from src.core.utils import get_logger
from src.modules.channels.twilio.models.domain import TwilioAccount
from src.modules.channels.twilio.repositories.account_repository import \
    TwilioAccountRepository

logger = get_logger(__name__)


class TwilioAccountService:
    """
    Service to handle Twilio Account logic.
    """

    def __init__(self, twilio_account_repo: TwilioAccountRepository):
        self.repo = twilio_account_repo

    def resolve_account(
        self, to_number: Optional[str], account_sid: Optional[str]
    ) -> Optional[TwilioAccount]:
        """
        Resolve the TwilioAccount based on the To number or Account SID.

        Strategies:
        1. Try by Account SID
        2. Try by Phone Number
        3. Fallback to default from settings (Development only ideally)
        """
        normalized_to_number = to_number or ""
        if normalized_to_number.startswith("whatsapp:"):
            normalized_to_number = normalized_to_number.split(":", 1)[1]

        account = None

        # 1. Try by Account SID
        if account_sid:
            account = self.repo.find_by_account_sid(account_sid)

        # 2. Try by Phone Number
        if not account and normalized_to_number:
            account = self.repo.find_by_phone_number(normalized_to_number)

        # 3. Fallback to default from settings (Development only)
        if getattr(settings.api, "environment", "production") == "development":
            if not account and getattr(settings.twilio, "account_sid", None):
                account = self.repo.find_by_account_sid(settings.twilio.account_sid)

        if not account:
            logger.warning(
                "Twilio Account lookup failed",
                to_number=to_number,
                account_sid=account_sid,
            )

        return account
