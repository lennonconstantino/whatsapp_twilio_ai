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
    add_person_tool, log_interaction_tool, schedule_reminder_tool)
from src.modules.ai.engines.lchain.feature.relationships.tools.query import (
    query_people_tool, query_interactions_tool, upcoming_reminders_tool)
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface


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


def create_relationships_agent(ai_log_thought_service: AILogThoughtService, memory_service: MemoryInterface = None) -> RoutingAgent:
    return RoutingAgent(
        task_agents=[
            query_relationships_agent,
            add_person_agent,
            log_interaction_agent,
            schedule_reminder_agent,
            identity_management_agent,
        ],
        system_message=ROUTING_SYSTEM_MESSAGE,
        prompt_extra=PROMPT_EXTRA,
        ai_log_thought_service=ai_log_thought_service,
        memory_service=memory_service,
    )
