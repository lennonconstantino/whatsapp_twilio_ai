from typing import Protocol, Dict, Any, runtime_checkable

@runtime_checkable
class IdentityProvider(Protocol):
    """
    Interface for identity management operations required by the AI module.
    This decouples the AI module from the concrete Identity module implementation.
    """

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Retrieve preferences for a given user.
        
        Args:
            user_id: The unique identifier of the user.
            
        Returns:
            Dict containing user preferences. Returns empty dict if not found or no preferences.
        """
        ...

    def update_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Update preferences for a given user.
        
        Args:
            user_id: The unique identifier of the user.
            preferences: The preferences to update (merge strategy depends on implementation, 
                       but usually this is a partial update).
            
        Returns:
            True if update was successful, False otherwise.
        """
        ...
