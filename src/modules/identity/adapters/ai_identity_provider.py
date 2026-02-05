from typing import Dict, Any

from src.modules.ai.engines.lchain.core.interfaces.identity_provider import IdentityProvider
from src.modules.identity.services.user_service import UserService

class AIIdentityProvider(IdentityProvider):
    """
    Adapter implementation of IdentityProvider using UserService.
    This allows the AI module to interact with user preferences without depending on Identity module models.
    """
    
    def __init__(self, user_service: UserService):
        self.user_service = user_service

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        user = self.user_service.get_user_by_id(user_id)
        if user and user.preferences:
            return user.preferences
        return {}

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        updated_user = self.user_service.update_user(user_id, {"preferences": preferences})
        return updated_user is not None
