from src.modules.ai.ai_result.services.ai_log_thought_service import \
    AILogThoughtService
from src.modules.ai.engines.lchain.core.agents.routing_agent import \
    RoutingAgent
from src.modules.ai.engines.lchain.core.agents.task_agent import TaskAgent
from src.modules.ai.engines.lchain.core.utils.utils import \
    generate_query_context
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer, Expense, Revenue)
from src.modules.ai.engines.lchain.feature.finance.prompts.routing import \
    PROMPT_EXTRA
from src.modules.ai.engines.lchain.feature.finance.prompts.routing import \
    SYSTEM_MESSAGE as ROUTING_SYSTEM_MESSAGE
from src.modules.ai.engines.lchain.feature.finance.prompts.task import \
    SYSTEM_MESSAGE as TASK_SYSTEM_MESSAGE
from src.modules.ai.engines.lchain.feature.finance.tools.add import (
    add_customer_tool, add_expense_tool, add_revenue_tool)
from src.modules.ai.engines.lchain.feature.finance.tools.query import \
    query_data_tool

query_task_agent = TaskAgent(
    name="query_agent",
    description="An agent that can perform queries on multiple data sources",
    create_user_context=lambda: generate_query_context(Expense, Revenue, Customer),
    tools=[query_data_tool],
    system_message=TASK_SYSTEM_MESSAGE,
)

add_expense_agent = TaskAgent(
    name="add_expense_agent",
    description="An agent that can add an expense to the database",
    create_user_context=lambda: generate_query_context(Expense)
    + "\nRemarks: The tax rate is 0.19. The user provide the net amount you need to calculate the gross amount.",
    tools=[add_expense_tool],
    system_message=TASK_SYSTEM_MESSAGE,
)

add_revenue_agent = TaskAgent(
    name="add_revenue_agent",
    description="An agent that can add a revenue entry to the database",
    create_user_context=lambda: generate_query_context(Revenue)
    + "\nRemarks: The tax rate is 0.19. The user provide the gross_amount you should use the tax rate to calculate the net_amount.",
    tools=[add_revenue_tool],
    system_message=TASK_SYSTEM_MESSAGE,
)

add_customer_agent = TaskAgent(
    name="add_customer_agent",
    description="An agent that can add a customer to the database",
    create_user_context=lambda: generate_query_context(Customer),
    tools=[add_customer_tool],
    system_message=TASK_SYSTEM_MESSAGE,
)


def create_finance_agent(ai_log_thought_service: AILogThoughtService) -> RoutingAgent:
    return RoutingAgent(
        task_agents=[
            query_task_agent,
            add_expense_agent,
            add_revenue_agent,
            add_customer_agent,
        ],
        system_message=ROUTING_SYSTEM_MESSAGE,
        prompt_extra=PROMPT_EXTRA,
        ai_log_thought_service=ai_log_thought_service,
    )
