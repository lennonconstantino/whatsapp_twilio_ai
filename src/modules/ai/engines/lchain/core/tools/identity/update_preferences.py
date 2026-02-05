from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field, ConfigDict

from src.core.utils.logging import get_logger
from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.engines.lchain.core.tools.tool import Tool
from src.modules.ai.engines.lchain.core.interfaces.identity_provider import IdentityProvider

logger = get_logger(__name__)


class UpdateUserPreferencesSchema(BaseModel):
    preferences: Dict[str, Any] = Field(
        ...,
        description="Dictionary of preferences to update (e.g., {'theme': 'dark', 'language': 'pt-BR'}). keys will be merged with existing preferences."
    )
    user_id: str = Field(..., description="The ID of the user to update.")


class UpdateUserPreferencesTool(Tool):
    """
    Tool to update user preferences in their profile.
    This allows storing durable facts about the user (e.g. language preference, communication style).
    """

    name: str = "update_user_preferences"
    description: str = (
        "Update the user's persistent preferences. "
        "Use this to store facts about the user that should be remembered across sessions. "
        "The provided preferences will be merged with existing ones."
    )
    args_schema: Type[BaseModel] = UpdateUserPreferencesSchema
    model: Type[BaseModel] = UpdateUserPreferencesSchema
    identity_provider: Optional[IdentityProvider] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, **kwargs) -> ToolResult:
        return self.execute(**kwargs)

    async def _arun(self, **kwargs) -> ToolResult:
        return self._run(**kwargs)

    def execute(self, **kwargs) -> ToolResult:
        try:
            user_id = kwargs.get("user_id")
            if not user_id:
                return ToolResult(success=False, content="user_id is required to update preferences.")

            preferences = kwargs.get("preferences", {})
            identity_provider = self.identity_provider
            
            if not identity_provider:
                return ToolResult(success=False, content="Internal Error: IdentityProvider not injected into tool.")
            
            # 1. Get current preferences
            current_prefs = identity_provider.get_user_preferences(user_id)
            
            # 2. Merge preferences
            updated_prefs = {**current_prefs, **preferences}
            
            # 3. Update
            success = identity_provider.update_user_preferences(user_id, updated_prefs)
            
            if success:
                return ToolResult(
                    success=True, 
                    content=f"Preferences updated successfully. New preferences: {updated_prefs}"
                )
            else:
                return ToolResult(success=False, content="Failed to update user preferences.")

        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return ToolResult(success=False, content=str(e))
