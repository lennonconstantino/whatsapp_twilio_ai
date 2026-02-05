from src.modules.ai.engines.lchain.core.agents.task_agent import TaskAgent
from src.modules.ai.engines.lchain.core.tools.identity.update_preferences import \
    UpdateUserPreferencesTool
from src.modules.ai.engines.lchain.core.interfaces.identity_provider import IdentityProvider

IDENTITY_SYSTEM_MESSAGE = """
You are an expert agent specialized in managing user identity and preferences.
Your role is to help users update their profile settings and durable preferences.

When a user asks to "change my name", "remember that I like X", "set my language to Y", 
or any other preference-related request, you should use the available tools to update their profile.

Always confirm the action with the user after updating.
"""

def create_identity_agent(identity_provider: IdentityProvider) -> TaskAgent:
    update_preferences_tool = UpdateUserPreferencesTool(identity_provider=identity_provider)

    return TaskAgent(
        name="identity_management_agent",
        description="Agent responsible for managing user profile, settings and preferences (e.g. name, language, durable preferences)",
        create_user_context=lambda: "Available tools allow updating user preferences.",
        tools=[update_preferences_tool],
        system_message=IDENTITY_SYSTEM_MESSAGE,
    )
