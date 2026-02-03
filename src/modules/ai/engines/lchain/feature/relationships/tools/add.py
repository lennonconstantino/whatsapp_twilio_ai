from typing import Type

from pydantic import BaseModel, Field

from src.modules.ai.engines.lchain.core.tools.tool import Tool, ToolResult
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    PersonCreate, InteractionCreate, ReminderCreate
)
from src.modules.ai.engines.lchain.feature.relationships.repositories.person_repository import PersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.interaction_repository import InteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.reminder_repository import ReminderRepository


# === Add Person Tool ===

class AddPersonTool(Tool):
    name: str = "add_person"
    description: str = "Add a new person to your contacts database"
    args_schema: Type[BaseModel] = PersonCreate
    model: Type[BaseModel] = PersonCreate
    parse_model: bool = True
    repository: PersonRepository
    
    def execute(self, input_data: PersonCreate) -> ToolResult:
        person = self.repository.create_from_schema(input_data)
        if person:
            return ToolResult(content=f"Added person {person.first_name} {person.last_name} (id={person.id})", success=True)
        return ToolResult(content="Failed to add person", success=False)


# === Log Interaction Tool ===

class LogInteractionTool(Tool):
    name: str = "log_interaction"
    description: str = "Log an interaction with a person in your contacts"
    args_schema: Type[BaseModel] = InteractionCreate
    model: Type[BaseModel] = InteractionCreate
    parse_model: bool = True
    repository: InteractionRepository
    
    def execute(self, input_data: InteractionCreate) -> ToolResult:
        interaction = self.repository.create_from_schema(input_data)
        if interaction:
            return ToolResult(content=f"Logged interaction id={interaction.id} for person_id={interaction.person_id}", success=True)
        return ToolResult(content="Failed to log interaction", success=False)


# === Schedule Reminder Tool ===

class ScheduleReminderTool(Tool):
    name: str = "schedule_reminder"
    description: str = "Schedule a reminder for a person"
    args_schema: Type[BaseModel] = ReminderCreate
    model: Type[BaseModel] = ReminderCreate
    parse_model: bool = True
    repository: ReminderRepository
    
    def execute(self, input_data: ReminderCreate) -> ToolResult:
        reminder = self.repository.create_from_schema(input_data)
        if reminder:
            return ToolResult(content=f"Scheduled reminder id={reminder.id} for person_id={reminder.person_id}", success=True)
        return ToolResult(content="Failed to schedule reminder", success=False)
