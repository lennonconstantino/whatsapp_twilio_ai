"""
Twilio service for sending and receiving messages.
"""
import os
from typing import Optional, Dict, Any
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException

from src.modules.conversation.enums.message_direction import MessageDirection
from src.modules.channels.twilio.repositories.account_repository import TwilioAccountRepository
from src.core.config import settings
from src.core.utils import get_logger

logger = get_logger(__name__)


class TwilioService:
    """
    Service for Twilio integration.
    Handles sending and receiving messages via Twilio.
    """
    
    def __init__(
        self,
        twilio_repo: TwilioAccountRepository
    ):
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
            
            # Try to use default credentials
            if settings.twilio.account_sid and settings.twilio.auth_token:
                logger.info("Using default Twilio credentials")
                client = TwilioClient(
                    settings.twilio.account_sid,
                    settings.twilio.auth_token
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
                "Error creating Twilio client",
                owner_id=owner_id,
                error=str(e)
            )
            return None
    
    def __send_via_fake_sender(self, owner_id: str,
                                     from_number: str,        
                                     to_number: str,
                                     body: str,
                                     media_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        
        return {
            "sid": f'SM_{os.urandom(16).hex()}',
            "status": "sent",
            "to": to_number,
            "from": from_number,
            "body": body,
            "message": "",
            "direction": MessageDirection.OUTBOUND.value
        }

    def send_message(
        self,
        owner_id: str,
        from_number: str,        
        to_number: str,
        body: str,
        media_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send a message via Twilio.
        
        Args:
            owner_id: Owner ID (ULID)
            to_number: Recipient phone number
            from_number: Sender phone number (Twilio number)
            body: Message body
            media_url: Optional media URL
            
        Returns:
            Message data dict or None
        """
        # Only send via fake sender in development environment
        if settings.api.environment == "development" and settings.api.use_fake_sender:
            logger.warning("Message sent via fake sender")
            return self.__send_via_fake_sender(owner_id, from_number, to_number, body, media_url)

        client = self._get_client(owner_id)
        if not client:
            logger.error("Cannot send message: no Twilio client", owner_id=owner_id)
            return None
        
        try:
            message_params = {
                "body": body,
                "from_": from_number,
                "to": to_number
            }
            
            if media_url:
                message_params["media_url"] = [media_url]
            
            message = client.messages.create(**message_params)
            
            logger.info(
                "Message sent via Twilio",
                message_sid=message.sid,
                to=to_number,
                from_=from_number
            )
            
            return {
                "sid": message.sid,
                "status": message.status,
                "to": message.to,
                "from": message.from_,
                "body": message.body,
                "message": message,
                "direction": MessageDirection.OUTBOUND.value
            }
        except TwilioRestException as e:
            logger.error(
                "Error sending message via Twilio",
                error=str(e),
                error_code=e.code
            )
            return None
    
    def get_message_status(
        self,
        owner_id: int,
        message_sid: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get message status from Twilio.
        
        Args:
            owner_id: Owner ID
            message_sid: Twilio message SID
            
        Returns:
            Message status dict or None
        """
        client = self._get_client(owner_id)
        if not client:
            return None
        
        try:
            message = client.messages(message_sid).fetch()
            
            return {
                "sid": message.sid,
                "status": message.status,
                "error_code": message.error_code,
                "error_message": message.error_message
            }
        except TwilioRestException as e:
            logger.error(
                "Error fetching message status",
                message_sid=message_sid,
                error=str(e)
            )
            return None
    
    def validate_webhook_signature(
        self,
        url: str,
        params: Dict[str, str],
        signature: str,
        auth_token: Optional[str] = None
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
