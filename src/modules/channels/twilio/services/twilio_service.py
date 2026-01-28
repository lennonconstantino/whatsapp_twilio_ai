"""
Twilio service for sending and receiving messages.
"""

import os
from typing import Any, Dict, Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as TwilioClient

from src.core.config import settings
from src.core.utils import get_logger
from src.modules.channels.twilio.models.results import TwilioMessageResult
from src.modules.channels.twilio.repositories.account_repository import \
    TwilioAccountRepository
from src.modules.conversation.enums.message_direction import MessageDirection

logger = get_logger(__name__)


class TwilioService:
    """
    Service for Twilio integration.
    Handles sending and receiving messages via Twilio.
    """

    def __init__(self, twilio_repo: TwilioAccountRepository):
        """
        Initialize Twilio service.

        Args:
            twilio_repo: Twilio account repository
        """
        self.twilio_repo = twilio_repo
        self._clients: Dict[str, TwilioClient] = {}

    def _get_client(self, owner_id: str) -> Optional[TwilioClient]:
        """
        Get or create Twilio client for an owner.

        Args:
            owner_id: Owner ID (ULID)

        Returns:
            Twilio client or None
        """
        # Check cache
        if owner_id in self._clients:
            return self._clients[owner_id]

        # Get account from database
        account = self.twilio_repo.find_by_owner(owner_id)
        if not account:
            logger.warning(f"No Twilio account found for owner {owner_id}")

            # Try to use default credentials (Development only)
            if (
                settings.api.environment == "development"
                and settings.twilio.account_sid
                and settings.twilio.auth_token
            ):
                logger.info("Using default Twilio credentials (Development Mode)")
                client = TwilioClient(
                    settings.twilio.account_sid, settings.twilio.auth_token
                )
                self._clients[owner_id] = client
                return client

            return None

        # Create client
        try:
            client = TwilioClient(account.account_sid, account.auth_token)
            self._clients[owner_id] = client
            return client
        except TwilioRestException as e:
            logger.error(
                "Error creating Twilio client", owner_id=owner_id, error=str(e)
            )
            return None

    def __send_via_fake_sender(
        self,
        owner_id: str,
        from_number: str,
        to_number: str,
        body: str,
        media_url: Optional[str] = None,
    ) -> Optional[TwilioMessageResult]:

        return TwilioMessageResult(
            sid=f"SM_{os.urandom(16).hex()}",
            status="sent",
            to=to_number,
            from_number=from_number,
            body=body,
            direction=MessageDirection.OUTBOUND.value,
        )

    def send_message(
        self,
        owner_id: str,
        from_number: str,
        to_number: str,
        body: str,
        media_url: Optional[str] = None,
    ) -> Optional[TwilioMessageResult]:
        """
        Send a message via Twilio.

        Args:
            owner_id: Owner ID (ULID)
            to_number: Recipient phone number
            from_number: Sender phone number (Twilio number)
            body: Message body
            media_url: Optional media URL

        Returns:
            TwilioMessageResult object or None
        """
        # Only send via fake sender in development environment
        if settings.api.environment == "development" and settings.api.use_fake_sender:
            logger.warning("Message sent via fake sender")
            return self.__send_via_fake_sender(
                owner_id, from_number, to_number, body, media_url
            )

        client = self._get_client(owner_id)
        if not client:
            logger.error("Cannot send message: no Twilio client", owner_id=owner_id)
            return None

        try:
            # Split message if body exceeds limit (Twilio limit is 1600)
            # We use 1500 to be safe
            max_length = 1500
            chunks = [body[i : i + max_length] for i in range(0, len(body), max_length)]

            if not chunks:
                chunks = [""]  # Handle empty body if necessary

            first_message = None
            last_message = None
            total_media = 0

            for i, chunk in enumerate(chunks):
                message_params = {"body": chunk, "from_": from_number, "to": to_number}

                # Attach media only to the first chunk
                if i == 0 and media_url:
                    message_params["media_url"] = [media_url]

                message = client.messages.create(**message_params)

                if i == 0:
                    first_message = message
                last_message = message

                if message.num_media:
                    total_media += int(message.num_media)

                logger.info(
                    f"Message chunk {i+1}/{len(chunks)} sent via Twilio",
                    message_sid=message.sid,
                    to=to_number,
                    from_=from_number,
                )

            if not last_message:
                return None

            return TwilioMessageResult(
                sid=first_message.sid,  # Return first SID to track the start of the sequence
                status=last_message.status,
                to=last_message.to,
                from_number=last_message.from_,
                body=body,  # Return ORIGINAL full body
                direction=MessageDirection.OUTBOUND.value,
                num_media=total_media,
                error_code=last_message.error_code,
                error_message=last_message.error_message,
            )
        except TwilioRestException as e:
            logger.error(
                "Error sending message via Twilio", error=str(e), error_code=e.code
            )
            return None

    def get_message_status(
        self, owner_id: str, message_sid: str
    ) -> Optional[TwilioMessageResult]:
        """
        Get message status from Twilio.

        Args:
            owner_id: Owner ID
            message_sid: Twilio message SID

        Returns:
            TwilioMessageResult object or None
        """
        client = self._get_client(owner_id)
        if not client:
            return None

        try:
            message = client.messages(message_sid).fetch()

            return TwilioMessageResult(
                sid=message.sid,
                status=message.status,
                to=message.to,
                from_number=message.from_,
                body=message.body,
                direction=message.direction,  # Twilio returns direction
                num_media=int(message.num_media) if message.num_media else 0,
                error_code=message.error_code,
                error_message=message.error_message,
            )
        except TwilioRestException as e:
            logger.error(
                "Error fetching message status", message_sid=message_sid, error=str(e)
            )
            return None

    def validate_webhook_signature(
        self,
        url: str,
        params: Dict[str, str],
        signature: str,
        auth_token: Optional[str] = None,
    ) -> bool:
        """
        Validate Twilio webhook signature.

        Args:
            url: Webhook URL
            params: Request parameters
            signature: X-Twilio-Signature header
            auth_token: Auth token (uses default if None)

        Returns:
            True if signature is valid
        """
        from twilio.request_validator import RequestValidator

        token = auth_token or settings.twilio.auth_token
        if not token:
            logger.warning("No auth token available for webhook validation")
            return False

        validator = RequestValidator(token)
        return validator.validate(url, params, signature)
