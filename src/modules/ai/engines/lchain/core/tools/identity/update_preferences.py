from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, Field

from src.core.database.session import get_db
from src.core.utils.logging import get_logger
from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.engines.lchain.core.tools.tool import Tool
from src.modules.identity.repositories.user_repository import UserRepository
from src.modules.identity.services.user_service import UserService

logger = get_logger(__name__)


class UpdateUserPreferencesSchema(BaseModel):
    preferences: Dict[str, Any] = Field(
        ...,
        description="Dictionary of preferences to update (e.g., {'theme': 'dark', 'language': 'pt-BR'}). keys will be merged with existing preferences."
    )
    user_id: str = Field(..., description="The ID of the user to update.")


def get_user_service() -> UserService:
    """Helper to get UserService with dependencies."""
    client = get_db()
    repo = UserRepository(client)
    return UserService(repo)


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

            service = get_user_service()
            
            # 1. Get current user
            user = service.get_user_by_id(user_id)
            if not user:
                 return ToolResult(success=False, content=f"User {user_id} not found.")

            # 2. Merge preferences
            current_prefs = user.preferences or {}
            updated_prefs = {**current_prefs, **preferences}
            
            # 3. Update
            updated_user = service.update_user(user_id, {"preferences": updated_prefs})
            
            if updated_user:
                return ToolResult(
                    success=True, 
                    content=f"Preferences updated successfully. New preferences: {updated_user.preferences}"
                )
            else:
                return ToolResult(success=False, content="Failed to update user.")

        except Exception as e:
            logger.error(f"Error updating user preferences: {e}")
            return ToolResult(success=False, content=str(e))


# Singleton instance
update_user_preferences_tool = UpdateUserPreferencesTool()
