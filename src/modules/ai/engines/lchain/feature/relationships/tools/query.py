from typing import Type, Optional

from pydantic import BaseModel, Field

from src.modules.ai.engines.lchain.core.tools.tool import Tool, ToolResult
from src.modules.ai.engines.lchain.feature.relationships.repositories.repository_relationships import (
    get_person_repository,
    get_interaction_repository,
    get_reminder_repository,
)


# === Query People Tool ===

class QueryPeople(BaseModel):
    name_contains: Optional[str] = Field(default=None, description="Buscar por nome (primeiro ou último)")
    tag_contains: Optional[str] = Field(default=None, description="Buscar por tags")

class QueryPeopleTool(Tool):
    name: str = "query_people"
    description: str = "Search for people in your contacts. You can search by name (first or last name) or by tags. Both parameters are optional - if neither is provided, all contacts will be returned."
    args_schema: Type[BaseModel] = QueryPeople
    model: Type[BaseModel] = QueryPeople
    
    def execute(self, **kwargs) -> ToolResult:
        repo = get_person_repository()
        name_contains = kwargs.get("name_contains")
        tag_contains = kwargs.get("tag_contains")
        
        # If no args provided, maybe return all? The repo method handles None for optional filters.
        # But if both are None, repo.search_by_name_or_tags returns all.
        
        results = repo.search_by_name_or_tags(name=name_contains, tags=tag_contains)
        return ToolResult(content=str([r.model_dump() for r in results]), success=True)


# === Query Interactions Tool ===

class QueryInteractions(BaseModel):
    person_id: Optional[int] = Field(default=None, description="ID da pessoa para filtrar")
    channel: Optional[str] = Field(default=None, description="Canal de comunicação para filtrar")
    type: Optional[str] = Field(default=None, description="Tipo de interação para filtrar")

class QueryInteractionsTool(Tool):
    name: str = "query_interactions"
    description: str = "Search for interaction history with optional filters"
    args_schema: Type[BaseModel] = QueryInteractions
    model: Type[BaseModel] = QueryInteractions
    
    def execute(self, **kwargs) -> ToolResult:
        repo = get_interaction_repository()
        results = repo.search(
            person_id=kwargs.get("person_id"),
            channel=kwargs.get("channel"),
            type_=kwargs.get("type")
        )
        return ToolResult(content=str([r.model_dump() for r in results]), success=True)


# === Upcoming Reminders Tool ===

class UpcomingReminders(BaseModel):
    days_ahead: int = Field(default=7, description="Número de dias à frente para buscar lembretes")

class UpcomingRemindersTool(Tool):
    name: str = "upcoming_reminders"
    description: str = "Get reminders due in the next specified number of days (default: 7 days)"
    args_schema: Type[BaseModel] = UpcomingReminders
    model: Type[BaseModel] = UpcomingReminders
    
    def execute(self, **kwargs) -> ToolResult:
        repo = get_reminder_repository()
        days = kwargs.get("days_ahead", 7)
        results = repo.get_upcoming(days=days)
        return ToolResult(content=str([r.model_dump() for r in results]), success=True)


# === Tool Instances ===
query_people_tool = QueryPeopleTool()
query_interactions_tool = QueryInteractionsTool()
upcoming_reminders_tool = UpcomingRemindersTool()
