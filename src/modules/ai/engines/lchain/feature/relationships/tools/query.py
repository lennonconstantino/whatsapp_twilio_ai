from typing import Type, Optional

from pydantic import BaseModel, Field

from src.modules.ai.engines.lchain.core.tools.tool import Tool, ToolResult
from src.modules.ai.engines.lchain.feature.relationships.repositories.person_repository import PersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.interaction_repository import InteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.reminder_repository import ReminderRepository


# === Query People Tool ===

class QueryPeople(BaseModel):
    name_contains: Optional[str] = Field(default=None, description="Buscar por nome (primeiro ou último)")
    tag_contains: Optional[str] = Field(default=None, description="Buscar por tags")

class QueryPeopleTool(Tool):
    name: str = "query_people"
    description: str = "Search for people in your contacts. You can search by name (first or last name) or by tags. Both parameters are optional - if neither is provided, all contacts will be returned."
    args_schema: Type[BaseModel] = QueryPeople
    model: Type[BaseModel] = QueryPeople
    repository: PersonRepository
    
    def execute(self, **kwargs) -> ToolResult:
        name_contains = kwargs.get("name_contains")
        tag_contains = kwargs.get("tag_contains")
        
        results = self.repository.search_by_name_or_tags(name=name_contains, tags=tag_contains)
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
    repository: InteractionRepository
    
    def execute(self, **kwargs) -> ToolResult:
        results = self.repository.search(
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
    repository: ReminderRepository
    
    def execute(self, **kwargs) -> ToolResult:
        days = kwargs.get("days_ahead", 7)
        results = self.repository.get_upcoming(days=days)
        return ToolResult(content=str([r.model_dump() for r in results]), success=True)
