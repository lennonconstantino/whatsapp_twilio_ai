from fastapi import HTTPException
from src.core.utils import get_logger
from src.modules.channels.twilio.models.domain import TwilioWhatsAppPayload
from src.modules.channels.twilio.services.twilio_account_service import TwilioAccountService
from src.modules.identity.services.identity_service import IdentityService
from starlette.concurrency import run_in_threadpool

logger = get_logger(__name__)

class TwilioWebhookOwnerResolver:
    """
    Component responsible for resolving and validating the owner of the request.
    """

    def __init__(
        self,
        twilio_account_service: TwilioAccountService,
        identity_service: IdentityService,
    ):
        self.twilio_account_service = twilio_account_service
        self.identity_service = identity_service

    async def resolve_owner_id(self, payload: TwilioWhatsAppPayload) -> str:
        """
        Resolve the Owner ID (Tenant) based on the To number or Account SID.
        """
        account = await self.twilio_account_service.resolve_account(
            to_number=payload.to_number, account_sid=payload.account_sid
        )

        if not account:
            logger.error(
                "Owner lookup failed",
                to_number=payload.to_number,
                account_sid=payload.account_sid,
            )
            raise HTTPException(
                status_code=403, detail="Owner not found for inbound/outbound number"
            )

        return account.owner_id

    async def validate_owner_access(self, owner_id: str) -> bool:
        """
        Validate if the owner has an active plan/access.
        """
        return await run_in_threadpool(
            self.identity_service.validate_owner_access, owner_id
        )
