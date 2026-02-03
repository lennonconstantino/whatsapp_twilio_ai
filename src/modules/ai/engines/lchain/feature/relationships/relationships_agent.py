from src.modules.ai.ai_result.services.ai_log_thought_service import \
    AILogThoughtService
from src.modules.ai.engines.lchain.core.agents.routing_agent import \
    RoutingAgent
from src.modules.ai.engines.lchain.core.agents.task_agent import TaskAgent
from src.modules.ai.engines.lchain.core.utils.utils import \
    generate_query_context
from src.modules.ai.engines.lchain.feature.relationships.models.models import (
    Person, Interaction, Reminder)
from src.modules.ai.engines.lchain.feature.relationships.prompts.routing import \
    PROMPT_EXTRA
from src.modules.ai.engines.lchain.feature.relationships.prompts.routing import \
    SYSTEM_MESSAGE as ROUTING_SYSTEM_MESSAGE
from src.modules.ai.engines.lchain.feature.relationships.prompts.task import \
    SYSTEM_MESSAGE as TASK_SYSTEM_MESSAGE
from src.modules.ai.engines.lchain.feature.relationships.tools.add import (
    AddPersonTool, LogInteractionTool, ScheduleReminderTool)
from src.modules.ai.engines.lchain.feature.relationships.tools.query import (
    QueryPeopleTool, QueryInteractionsTool, UpcomingRemindersTool)
from src.modules.ai.engines.lchain.feature.relationships.repositories.person_repository import PersonRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.interaction_repository import InteractionRepository
from src.modules.ai.engines.lchain.feature.relationships.repositories.reminder_repository import ReminderRepository
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface


def create_relationships_agent(
    ai_log_thought_service: AILogThoughtService,
    person_repository: PersonRepository,
    interaction_repository: InteractionRepository,
    reminder_repository: ReminderRepository,
    identity_agent: TaskAgent,
    memory_service: MemoryInterface = None
) -> RoutingAgent:
    
    # Instantiate tools with injected repositories
    add_person_tool = AddPersonTool(repository=person_repository)
    log_interaction_tool = LogInteractionTool(repository=interaction_repository)
    schedule_reminder_tool = ScheduleReminderTool(repository=reminder_repository)
    
    query_people_tool = QueryPeopleTool(repository=person_repository)
    query_interactions_tool = QueryInteractionsTool(repository=interaction_repository)
    upcoming_reminders_tool = UpcomingRemindersTool(repository=reminder_repository)

    # Instantiate agents
    query_relationships_agent = TaskAgent(
        name="query_relationships_agent",
        description="Agent that can query people, interactions and upcoming reminders",
        create_user_context=lambda: generate_query_context(Person, Interaction, Reminder),
        tools=[
            query_people_tool,
            query_interactions_tool,
            upcoming_reminders_tool,
        ],
        system_message=TASK_SYSTEM_MESSAGE,
    )

    add_person_agent = TaskAgent(
        name="add_person_agent",
        description="Agent that can add a person to the database",
        create_user_context=lambda: generate_query_context(Person),
        tools=[add_person_tool],
        system_message=TASK_SYSTEM_MESSAGE
    )

    log_interaction_agent = TaskAgent(
        name="log_interaction_agent",
        description="Agent that can log an interaction for a person",
        create_user_context=lambda: generate_query_context(Interaction),
        tools=[log_interaction_tool],
        system_message=TASK_SYSTEM_MESSAGE
    )

    schedule_reminder_agent = TaskAgent(
        name="schedule_reminder_agent",
        description="Agent that can schedule reminders for a person",
        create_user_context=lambda: generate_query_context(Reminder, Person),
        tools=[schedule_reminder_tool, query_people_tool],
        system_message=TASK_SYSTEM_MESSAGE,
    )

    return RoutingAgent(
        task_agents=[
            query_relationships_agent,
            add_person_agent,
            log_interaction_agent,
            schedule_reminder_agent,
            identity_agent,
        ],
        system_message=ROUTING_SYSTEM_MESSAGE,
        prompt_extra=PROMPT_EXTRA,
        ai_log_thought_service=ai_log_thought_service,
        memory_service=memory_service,
    )
