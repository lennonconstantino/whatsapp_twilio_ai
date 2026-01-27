from typing import Type

from pydantic import BaseModel, Field

from src.modules.ai.engines.lchain.core.tools.tool import Tool, ToolResult
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    PersonCreate, InteractionCreate, ReminderCreate
)
from src.modules.ai.engines.lchain.feature.relationships.repositories.repository_relationships import (
    get_person_repository,
    get_interaction_repository,
    get_reminder_repository,
)


# === Add Person Tool ===

class AddPersonTool(Tool):
    name: str = "add_person"
    description: str = "Add a new person to your contacts database"
    args_schema: Type[BaseModel] = PersonCreate
    model: Type[BaseModel] = PersonCreate
    parse_model: bool = True
    
    def execute(self, input_data: PersonCreate) -> ToolResult:
        repo = get_person_repository()
        person = repo.create_from_schema(input_data)
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
    
    def execute(self, input_data: InteractionCreate) -> ToolResult:
        repo = get_interaction_repository()
        interaction = repo.create_from_schema(input_data)
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
    
    def execute(self, input_data: ReminderCreate) -> ToolResult:
        repo = get_reminder_repository()
        reminder = repo.create_from_schema(input_data)
        if reminder:
            return ToolResult(content=f"Scheduled reminder id={reminder.id} for person_id={reminder.person_id}", success=True)
        return ToolResult(content="Failed to schedule reminder", success=False)


# === Tool Instances ===
add_person_tool = AddPersonTool()
log_interaction_tool = LogInteractionTool()
schedule_reminder_tool = ScheduleReminderTool()
