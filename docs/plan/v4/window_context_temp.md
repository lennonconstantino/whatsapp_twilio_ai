SOLO Builder

src/core/di/container.py

src/modules/ai/engines/lchain/core/agents/agent_factory.py

agent_factory.py
src/modules/ai/engines/lchain/core/agents/agent_factory.py

+ 23 - 2

Open Diff

src/modules/ai/engines/lchain/feature/finance/finance_agent.py

src/modules/ai/engines/lchain/feature/relationships/relationships_agent.py

finance_agent.py
src/modules/ai/engines/lchain/feature/finance/finance_agent.py

+ 5 - 1

Open Diff

relationships_agent.py
src/modules/ai/engines/lchain/feature/relationships/relationships_agent.py

+ 2 - 1

Open Diff

src/modules/ai/engines/lchain/core/agents/routing_agent.py

routing_agent.py
src/modules/ai/engines/lchain/core/agents/routing_agent.py

+ 70 - 0

Open Diff

container.py
src/core/di/container.py

+ 9 - 0

Open Diff

container.py
src/core/di/container.py

+ 1 - 0

Open Diff

whatsapp_twilio_ai
In Sandbox
Terminal

$ mkdir -p tests/integration/ai/memory

test_agent_memory_integration.py
tests/integration/ai/memory/test_agent_memory_integration.py

+ 104 - 0

Open Diff

whatsapp_twilio_ai
In Sandbox
Terminal

$ python -m pytest tests/integration/ai/memory/test_agent_memory_integration.py

======================================================= test session starts ========================================================
platform darwin -- Python 3.12.2, pytest-8.3.3, pluggy-1.6.0
rootdir: /Users/lennon/projects/ai_engineering/whatsapp_twilio_ai
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-0.24.0, cov-5.0.0, langsmith-0.6.4
asyncio: mode=Mode.AUTO, default_loop_scope=function
collected 3 items                                                                                                                  

tests/integration/ai/memory/test_agent_memory_integration.py FFF                                                             [100%]

============================================================= FAILURES =============================================================
___________________________________ TestAgentMemoryIntegration.test_agent_reads_memory_on_start ____________________________________

self = <test_agent_memory_integration.TestAgentMemoryIntegration object at 0x127d663f0>
mock_redis_repo = <MagicMock spec='RedisMemoryRepository' id='4963328624'>, mock_llm = {'ollama': <MagicMock id='4963334432'>}

    def test_agent_reads_memory_on_start(self, mock_redis_repo, mock_llm):
        """
        Test that RoutingAgent calls memory_service.get_context() on run().
        """
        # Arrange
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            agent_context={"owner_id": "owner1", "user": {"phone": "123"}}
        )
    
        # Act
>       agent.run("Hello AI")

tests/integration/ai/memory/test_agent_memory_integration.py:42: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.modules.ai.engines.lchain.core.agents.routing_agent.RoutingAgent object at 0x127d67980>, user_input = 'Hello AI'
kwargs = {}, context_formatted = '', memory_formatted = '', task_formatted = ''
current_agent_context = {'owner_id': 'owner1', 'user': {'phone': '123'}}
ctx_data = {'owner_id': 'owner1', 'user': {'phone': '123'}}

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""
    
        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}
    
        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}
    
>       self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
E       pydantic_core._pydantic_core.ValidationError: 2 validation errors for AgentContext
E       correlation_id
E         Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
E           For further information visit https://errors.pydantic.dev/2.9/v/string_type
E       channel
E         Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
E           For further information visit https://errors.pydantic.dev/2.9/v/string_type

src/modules/ai/engines/lchain/core/agents/routing_agent.py:69: ValidationError
________________________________ TestAgentMemoryIntegration.test_agent_saves_interaction_to_memory _________________________________

self = <test_agent_memory_integration.TestAgentMemoryIntegration object at 0x127d66390>
mock_redis_repo = <MagicMock spec='RedisMemoryRepository' id='4963463248'>, mock_llm = {'ollama': <MagicMock id='4963456672'>}

    def test_agent_saves_interaction_to_memory(self, mock_redis_repo, mock_llm):
        """
        Test that RoutingAgent calls memory_service.add_message() for user input and AI response.
        """
        # Arrange
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            agent_context={"owner_id": "owner1", "user": {"phone": "123"}}
        )
    
        # Act
>       agent.run("Hello AI")

tests/integration/ai/memory/test_agent_memory_integration.py:63: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.modules.ai.engines.lchain.core.agents.routing_agent.RoutingAgent object at 0x127d86ff0>, user_input = 'Hello AI'
kwargs = {}, context_formatted = '', memory_formatted = '', task_formatted = ''
current_agent_context = {'owner_id': 'owner1', 'user': {'phone': '123'}}
ctx_data = {'owner_id': 'owner1', 'user': {'phone': '123'}}

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""
    
        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}
    
        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}
    
>       self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
E       pydantic_core._pydantic_core.ValidationError: 2 validation errors for AgentContext
E       correlation_id
E         Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
E           For further information visit https://errors.pydantic.dev/2.9/v/string_type
E       channel
E         Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
E           For further information visit https://errors.pydantic.dev/2.9/v/string_type

src/modules/ai/engines/lchain/core/agents/routing_agent.py:69: ValidationError
_______________________________ TestAgentMemoryIntegration.test_agent_populates_context_from_memory ________________________________

self = <test_agent_memory_integration.TestAgentMemoryIntegration object at 0x127d66600>
mock_redis_repo = <MagicMock spec='RedisMemoryRepository' id='4963905520'>, mock_llm = {'ollama': <MagicMock id='4964205440'>}

    def test_agent_populates_context_from_memory(self, mock_redis_repo, mock_llm):
        """
        Test that memory content is injected into agent context.
        """
        # Arrange
        mock_redis_repo.get_context.return_value = [
            {"role": "user", "content": "My name is Lennon"},
            {"role": "assistant", "content": "Hello Lennon"}
        ]
    
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            agent_context={"owner_id": "owner1", "user": {"phone": "123"}}
        )
    
        # Act
>       agent.run("Who am I?")

tests/integration/ai/memory/test_agent_memory_integration.py:97: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.modules.ai.engines.lchain.core.agents.routing_agent.RoutingAgent object at 0x127df2fc0>, user_input = 'Who am I?'
kwargs = {}, context_formatted = '', memory_formatted = '', task_formatted = ''
current_agent_context = {'owner_id': 'owner1', 'user': {'phone': '123'}}
ctx_data = {'owner_id': 'owner1', 'user': {'phone': '123'}}

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""
    
        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}
    
        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}
    
>       self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
E       pydantic_core._pydantic_core.ValidationError: 2 validation errors for AgentContext
E       correlation_id
E         Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
E           For further information visit https://errors.pydantic.dev/2.9/v/string_type
E       channel
E         Input should be a valid string [type=string_type, input_value=None, input_type=NoneType]
E           For further information visit https://errors.pydantic.dev/2.9/v/string_type

src/modules/ai/engines/lchain/core/agents/routing_agent.py:69: ValidationError
========================================================= warnings summary =========================================================
.venv/lib/python3.12/site-packages/supabase/__init__.py:1
  /Users/lennon/projects/ai_engineering/whatsapp_twilio_ai/.venv/lib/python3.12/site-packages/supabase/__init__.py:1: DeprecationWarning: The `gotrue` package is deprecated, is not going to receive updates in the future. Please, use `supabase_auth` instead.
    from gotrue.errors import (

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
===================================================== short test summary info ======================================================
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_reads_memory_on_start - pydantic_core._pydantic_core.ValidationError: 2 validation errors for AgentContext
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_saves_interaction_to_memory - pydantic_core._pydantic_core.ValidationError: 2 validation errors for AgentContext
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_populates_context_from_memory - pydantic_core._pydantic_core.ValidationError: 2 validation errors for AgentContext
=================================================== 3 failed, 1 warning in 0.99s ===================================================

test_agent_memory_integration.py
tests/integration/ai/memory/test_agent_memory_integration.py

+ 18 - 3

Open Diff

whatsapp_twilio_ai
In Sandbox
Terminal

$ python -m pytest tests/integration/ai/memory/test_agent_memory_integration.py

(some characters truncated)...
ontext.memory:
            memory_formatted = f"Memory Context:\n'''{self.agent_context.memory}'''"
        if self.agent_context.additional_context:
            task_formatted = (
                f"Task Context:\n'''{self.agent_context.additional_context}'''"
            )
    
        combined_context = "".join(
            [
                (
                    memory_formatted + "\n---------------------------------\n"
                    if memory_formatted
                    else ""
                ),
                (
                    task_formatted + "\n---------------------------------\n"
                    if task_formatted
                    else ""
                ),
            ]
        )
    
        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input
    
        logger.info("Starting Routing Agent", event_type="routing_agent_start")
        logger.info(
            "Routing Agent Context",
            event_type="routing_agent_context",
            correlation_id=self.agent_context.correlation_id,
            feature=self.agent_context.feature,
            owner_id=self.agent_context.owner_id,
            channel=self.agent_context.channel,
            phone=(
                self.agent_context.user.get("phone") if self.agent_context.user else "N/A"
            ),
        )
        logger.info(
            "Prompt Formatted", event_type="routing_agent_prompt", prompt=context_formatted
        )
    
        partial_variables = {**self.prompt_extra, "context": context_formatted}
        system_message = self.system_message.format(**partial_variables)
    
        # Converter mensagens para formato LangChain
        messages = [
            SystemMessage(content=system_message),
            *[
                (
                    HumanMessage(content=ex["content"])
                    if ex["role"] == "user"
                    else AIMessage(content=ex["content"])
                )
                for ex in self.examples
            ],
            HumanMessage(content=user_input),
        ]
    
        # Converter Task Agents para Tools em formato LangChain
        tools = [tool.langchain_tool_schema for tool in self.task_agents]
    
        # Bind tools e invocar
>       model = self.llm[LLM]
E       KeyError: 'ollama/gpt-oss:20b'

src/modules/ai/engines/lchain/core/agents/routing_agent.py:189: KeyError
________________________________ TestAgentMemoryIntegration.test_agent_saves_interaction_to_memory _________________________________

self = <test_agent_memory_integration.TestAgentMemoryIntegration object at 0x10c6668a0>
mock_redis_repo = <MagicMock spec='RedisMemoryRepository' id='4503116720'>, mock_llm = {'ollama': <MagicMock id='4503115328'>}

    def test_agent_saves_interaction_to_memory(self, mock_redis_repo, mock_llm):
        """
        Test that RoutingAgent calls memory_service.add_message() for user input and AI response.
        """
        # Arrange
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            agent_context={
                "owner_id": "owner1",
                "user": {"phone": "123"},
                "correlation_id": "corr123",
                "channel": "whatsapp"
            }
        )
    
        # Act
>       agent.run("Hello AI")

tests/integration/ai/memory/test_agent_memory_integration.py:73: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.modules.ai.engines.lchain.core.agents.routing_agent.RoutingAgent object at 0x10c683710>, user_input = 'Hello AI'
kwargs = {}, context_formatted = 'Hello AI', memory_formatted = '', task_formatted = ''
current_agent_context = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}
ctx_data = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}, user_phone = '123'
session_id = 'owner1:123'

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""
    
        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}
    
        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}
    
        self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
    
        # ------------------------------------------------------------------
        # INTEGRATION: Load memory from MemoryService if available and not present
        # ------------------------------------------------------------------
        if self.memory_service and not self.agent_context.memory:
            # We use a simple session_id for now.
            # Ideally, session_id should be unique per conversation.
            # In Twilio context, we can use user phone or conversation_id if available.
            # But AgentContext doesn't strictly enforce conversation_id field yet.
            # We'll use owner_id + user_phone as session key fallback if needed.
    
            user_phone = "unknown"
            if self.agent_context.user:
                 user_phone = self.agent_context.user.get("phone", "unknown")
    
            # Construct a session key.
            # Strategy: If conversation_id is passed in kwargs/context, use it.
            # Otherwise use owner_id:user_phone
    
            session_id = ctx_data.get("conversation_id")
            if not session_id:
                session_id = f"{self.agent_context.owner_id}:{user_phone}"
    
            try:
                # Synchronous call for now (RedisMemoryRepository is sync-compatible via blocking calls if needed,
                # but our implementation uses standard redis client which blocks)
                # Wait, our RedisMemoryRepository implementation is synchronous?
                # Let's check... Yes, we implemented it with 'redis' lib, not 'aioredis' (except the import name confusion in previous step).
                # But wait, we imported 'redis' and used 'redis.from_url', which is sync.
    
                # So we can call it directly.
                history = self.memory_service.get_context(session_id, limit=10)
                if history:
                    # Format history as text for the prompt
                    # This is a simple concatenation.
                    # Ideally, we should inject this into message history list, but RoutingAgent uses a single prompt.
                    # We will append it to memory_formatted string.
                    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                    self.agent_context.memory = history_text
            except Exception as e:
                logger.error(f"Failed to load memory context: {e}")
    
        if self.agent_context.memory:
            memory_formatted = f"Memory Context:\n'''{self.agent_context.memory}'''"
        if self.agent_context.additional_context:
            task_formatted = (
                f"Task Context:\n'''{self.agent_context.additional_context}'''"
            )
    
        combined_context = "".join(
            [
                (
                    memory_formatted + "\n---------------------------------\n"
                    if memory_formatted
                    else ""
                ),
                (
                    task_formatted + "\n---------------------------------\n"
                    if task_formatted
                    else ""
                ),
            ]
        )
    
        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input
    
        logger.info("Starting Routing Agent", event_type="routing_agent_start")
        logger.info(
            "Routing Agent Context",
            event_type="routing_agent_context",
            correlation_id=self.agent_context.correlation_id,
            feature=self.agent_context.feature,
            owner_id=self.agent_context.owner_id,
            channel=self.agent_context.channel,
            phone=(
                self.agent_context.user.get("phone") if self.agent_context.user else "N/A"
            ),
        )
        logger.info(
            "Prompt Formatted", event_type="routing_agent_prompt", prompt=context_formatted
        )
    
        partial_variables = {**self.prompt_extra, "context": context_formatted}
        system_message = self.system_message.format(**partial_variables)
    
        # Converter mensagens para formato LangChain
        messages = [
            SystemMessage(content=system_message),
            *[
                (
                    HumanMessage(content=ex["content"])
                    if ex["role"] == "user"
                    else AIMessage(content=ex["content"])
                )
                for ex in self.examples
            ],
            HumanMessage(content=user_input),
        ]
    
        # Converter Task Agents para Tools em formato LangChain
        tools = [tool.langchain_tool_schema for tool in self.task_agents]
    
        # Bind tools e invocar
>       model = self.llm[LLM]
E       KeyError: 'ollama/gpt-oss:20b'

src/modules/ai/engines/lchain/core/agents/routing_agent.py:189: KeyError
_______________________________ TestAgentMemoryIntegration.test_agent_populates_context_from_memory ________________________________

self = <test_agent_memory_integration.TestAgentMemoryIntegration object at 0x10c666960>
mock_redis_repo = <MagicMock spec='RedisMemoryRepository' id='4503581856'>, mock_llm = {'ollama': <MagicMock id='4507142048'>}

    def test_agent_populates_context_from_memory(self, mock_redis_repo, mock_llm):
        """
        Test that memory content is injected into agent context.
        """
        # Arrange
        mock_redis_repo.get_context.return_value = [
            {"role": "user", "content": "My name is Lennon"},
            {"role": "assistant", "content": "Hello Lennon"}
        ]
    
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            agent_context={
                "owner_id": "owner1",
                "user": {"phone": "123"},
                "correlation_id": "corr123",
                "channel": "whatsapp"
            }
        )
    
        # Act
>       agent.run("Who am I?")

tests/integration/ai/memory/test_agent_memory_integration.py:112: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.modules.ai.engines.lchain.core.agents.routing_agent.RoutingAgent object at 0x10c6f3590>, user_input = 'Who am I?'
kwargs = {}
context_formatted = "Memory Context:\n'''user: My name is Lennon\nassistant: Hello Lennon'''\n---------------------------------\n\n---\n\nUser Message: Who am I?"
memory_formatted = "Memory Context:\n'''user: My name is Lennon\nassistant: Hello Lennon'''", task_formatted = ''
current_agent_context = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}
ctx_data = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}, user_phone = '123'
session_id = 'owner1:123'

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""
    
        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}
    
        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}
    
        self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
    
        # ------------------------------------------------------------------
        # INTEGRATION: Load memory from MemoryService if available and not present
        # ------------------------------------------------------------------
        if self.memory_service and not self.agent_context.memory:
            # We use a simple session_id for now.
            # Ideally, session_id should be unique per conversation.
            # In Twilio context, we can use user phone or conversation_id if available.
            # But AgentContext doesn't strictly enforce conversation_id field yet.
            # We'll use owner_id + user_phone as session key fallback if needed.
    
            user_phone = "unknown"
            if self.agent_context.user:
                 user_phone = self.agent_context.user.get("phone", "unknown")
    
            # Construct a session key.
            # Strategy: If conversation_id is passed in kwargs/context, use it.
            # Otherwise use owner_id:user_phone
    
            session_id = ctx_data.get("conversation_id")
            if not session_id:
                session_id = f"{self.agent_context.owner_id}:{user_phone}"
    
            try:
                # Synchronous call for now (RedisMemoryRepository is sync-compatible via blocking calls if needed,
                # but our implementation uses standard redis client which blocks)
                # Wait, our RedisMemoryRepository implementation is synchronous?
                # Let's check... Yes, we implemented it with 'redis' lib, not 'aioredis' (except the import name confusion in previous step).
                # But wait, we imported 'redis' and used 'redis.from_url', which is sync.
    
                # So we can call it directly.
                history = self.memory_service.get_context(session_id, limit=10)
                if history:
                    # Format history as text for the prompt
                    # This is a simple concatenation.
                    # Ideally, we should inject this into message history list, but RoutingAgent uses a single prompt.
                    # We will append it to memory_formatted string.
                    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                    self.agent_context.memory = history_text
            except Exception as e:
                logger.error(f"Failed to load memory context: {e}")
    
        if self.agent_context.memory:
            memory_formatted = f"Memory Context:\n'''{self.agent_context.memory}'''"
        if self.agent_context.additional_context:
            task_formatted = (
                f"Task Context:\n'''{self.agent_context.additional_context}'''"
            )
    
        combined_context = "".join(
            [
                (
                    memory_formatted + "\n---------------------------------\n"
                    if memory_formatted
                    else ""
                ),
                (
                    task_formatted + "\n---------------------------------\n"
                    if task_formatted
                    else ""
                ),
            ]
        )
    
        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input
    
        logger.info("Starting Routing Agent", event_type="routing_agent_start")
        logger.info(
            "Routing Agent Context",
            event_type="routing_agent_context",
            correlation_id=self.agent_context.correlation_id,
            feature=self.agent_context.feature,
            owner_id=self.agent_context.owner_id,
            channel=self.agent_context.channel,
            phone=(
                self.agent_context.user.get("phone") if self.agent_context.user else "N/A"
            ),
        )
        logger.info(
            "Prompt Formatted", event_type="routing_agent_prompt", prompt=context_formatted
        )
    
        partial_variables = {**self.prompt_extra, "context": context_formatted}
        system_message = self.system_message.format(**partial_variables)
    
        # Converter mensagens para formato LangChain
        messages = [
            SystemMessage(content=system_message),
            *[
                (
                    HumanMessage(content=ex["content"])
                    if ex["role"] == "user"
                    else AIMessage(content=ex["content"])
                )
                for ex in self.examples
            ],
            HumanMessage(content=user_input),
        ]
    
        # Converter Task Agents para Tools em formato LangChain
        tools = [tool.langchain_tool_schema for tool in self.task_agents]
    
        # Bind tools e invocar
>       model = self.llm[LLM]
E       KeyError: 'ollama/gpt-oss:20b'

src/modules/ai/engines/lchain/core/agents/routing_agent.py:189: KeyError
========================================================= warnings summary =========================================================
.venv/lib/python3.12/site-packages/supabase/__init__.py:1
  /Users/lennon/projects/ai_engineering/whatsapp_twilio_ai/.venv/lib/python3.12/site-packages/supabase/__init__.py:1: DeprecationWarning: The `gotrue` package is deprecated, is not going to receive updates in the future. Please, use `supabase_auth` instead.
    from gotrue.errors import (

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
===================================================== short test summary info ======================================================
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_reads_memory_on_start - KeyError: 'ollama/gpt-oss:20b'
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_saves_interaction_to_memory - KeyError: 'ollama/gpt-oss:20b'
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_populates_context_from_memory - KeyError: 'ollama/gpt-oss:20b'
=================================================== 3 failed, 1 warning in 1.00s ===================================================

src/modules/ai/infrastructure/llm.py

test_agent_memory_integration.py
tests/integration/ai/memory/test_agent_memory_integration.py

+ 8 - 1

Open Diff

whatsapp_twilio_ai
In Sandbox
Terminal

$ python -m pytest tests/integration/ai/memory/test_agent_memory_integration.py

(some characters truncated)...
phone": "123"},
                "correlation_id": "corr123",
                "channel": "whatsapp"
            }
        )
    
        # Act
>       agent.run("Hello AI")

tests/integration/ai/memory/test_agent_memory_integration.py:80: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.modules.ai.engines.lchain.core.agents.routing_agent.RoutingAgent object at 0x121c83d40>, user_input = 'Hello AI'
kwargs = {}, context_formatted = 'Hello AI', memory_formatted = '', task_formatted = ''
current_agent_context = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}
ctx_data = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}, user_phone = '123'
session_id = 'owner1:123'

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""
    
        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}
    
        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}
    
        self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
    
        # ------------------------------------------------------------------
        # INTEGRATION: Load memory from MemoryService if available and not present
        # ------------------------------------------------------------------
        if self.memory_service and not self.agent_context.memory:
            # We use a simple session_id for now.
            # Ideally, session_id should be unique per conversation.
            # In Twilio context, we can use user phone or conversation_id if available.
            # But AgentContext doesn't strictly enforce conversation_id field yet.
            # We'll use owner_id + user_phone as session key fallback if needed.
    
            user_phone = "unknown"
            if self.agent_context.user:
                 user_phone = self.agent_context.user.get("phone", "unknown")
    
            # Construct a session key.
            # Strategy: If conversation_id is passed in kwargs/context, use it.
            # Otherwise use owner_id:user_phone
    
            session_id = ctx_data.get("conversation_id")
            if not session_id:
                session_id = f"{self.agent_context.owner_id}:{user_phone}"
    
            try:
                # Synchronous call for now (RedisMemoryRepository is sync-compatible via blocking calls if needed,
                # but our implementation uses standard redis client which blocks)
                # Wait, our RedisMemoryRepository implementation is synchronous?
                # Let's check... Yes, we implemented it with 'redis' lib, not 'aioredis' (except the import name confusion in previous step).
                # But wait, we imported 'redis' and used 'redis.from_url', which is sync.
    
                # So we can call it directly.
                history = self.memory_service.get_context(session_id, limit=10)
                if history:
                    # Format history as text for the prompt
                    # This is a simple concatenation.
                    # Ideally, we should inject this into message history list, but RoutingAgent uses a single prompt.
                    # We will append it to memory_formatted string.
                    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                    self.agent_context.memory = history_text
            except Exception as e:
                logger.error(f"Failed to load memory context: {e}")
    
        if self.agent_context.memory:
            memory_formatted = f"Memory Context:\n'''{self.agent_context.memory}'''"
        if self.agent_context.additional_context:
            task_formatted = (
                f"Task Context:\n'''{self.agent_context.additional_context}'''"
            )
    
        combined_context = "".join(
            [
                (
                    memory_formatted + "\n---------------------------------\n"
                    if memory_formatted
                    else ""
                ),
                (
                    task_formatted + "\n---------------------------------\n"
                    if task_formatted
                    else ""
                ),
            ]
        )
    
        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input
    
        logger.info("Starting Routing Agent", event_type="routing_agent_start")
        logger.info(
            "Routing Agent Context",
            event_type="routing_agent_context",
            correlation_id=self.agent_context.correlation_id,
            feature=self.agent_context.feature,
            owner_id=self.agent_context.owner_id,
            channel=self.agent_context.channel,
            phone=(
                self.agent_context.user.get("phone") if self.agent_context.user else "N/A"
            ),
        )
        logger.info(
            "Prompt Formatted", event_type="routing_agent_prompt", prompt=context_formatted
        )
    
        partial_variables = {**self.prompt_extra, "context": context_formatted}
        system_message = self.system_message.format(**partial_variables)
    
        # Converter mensagens para formato LangChain
        messages = [
            SystemMessage(content=system_message),
            *[
                (
                    HumanMessage(content=ex["content"])
                    if ex["role"] == "user"
                    else AIMessage(content=ex["content"])
                )
                for ex in self.examples
            ],
            HumanMessage(content=user_input),
        ]
    
        # Converter Task Agents para Tools em formato LangChain
        tools = [tool.langchain_tool_schema for tool in self.task_agents]
    
        # Bind tools e invocar
        model = self.llm[LLM]
        model_with_tools = model.bind_tools(tools)
        response = model_with_tools.invoke(messages)
    
        # ------------------------------------------------------------------
        # INTEGRATION: Save User Input & AI Response to Memory
        # ------------------------------------------------------------------
        if self.memory_service:
            try:
                # Re-derive session_id
                user_phone = "unknown"
                if self.agent_context.user:
                     user_phone = self.agent_context.user.get("phone", "unknown")
                session_id = ctx_data.get("conversation_id")
                if not session_id:
                    session_id = f"{self.agent_context.owner_id}:{user_phone}"
    
                # Save User Input
                self.memory_service.add_message(session_id, {"role": "user", "content": user_input})
    
                # Save AI Response (if content exists)
                if response.content:
                    self.memory_service.add_message(session_id, {"role": "assistant", "content": response.content})
            except Exception as e:
                 logger.error(f"Failed to save memory context: {e}")
    
    
>       self.ai_log_thought_service.log_agent_thought(
            agent_context=self.agent_context,
            user_input="",
            output=response.content,
            history=self.step_history,
            result_type=AIResultType.AGENT_LOG,
            message=response,
        )
E       AttributeError: 'NoneType' object has no attribute 'log_agent_thought'

src/modules/ai/engines/lchain/core/agents/routing_agent.py:216: AttributeError
_______________________________ TestAgentMemoryIntegration.test_agent_populates_context_from_memory ________________________________

self = <test_agent_memory_integration.TestAgentMemoryIntegration object at 0x121c663f0>
mock_redis_repo = <MagicMock spec='RedisMemoryRepository' id='4861726304'>
mock_llm = {'ollama/gpt-oss:20b': <MagicMock id='4861725056'>}

    def test_agent_populates_context_from_memory(self, mock_redis_repo, mock_llm):
        """
        Test that memory content is injected into agent context.
        """
        # Arrange
        mock_redis_repo.get_context.return_value = [
            {"role": "user", "content": "My name is Lennon"},
            {"role": "assistant", "content": "Hello Lennon"}
        ]
    
        agent = RoutingAgent(
            llm=mock_llm,
            memory_service=mock_redis_repo,
            agent_context={
                "owner_id": "owner1",
                "user": {"phone": "123"},
                "correlation_id": "corr123",
                "channel": "whatsapp"
            }
        )
    
        # Act
>       agent.run("Who am I?")

tests/integration/ai/memory/test_agent_memory_integration.py:119: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ 

self = <src.modules.ai.engines.lchain.core.agents.routing_agent.RoutingAgent object at 0x121c820f0>, user_input = 'Who am I?'
kwargs = {}
context_formatted = "Memory Context:\n'''user: My name is Lennon\nassistant: Hello Lennon'''\n---------------------------------\n\n---\n\nUser Message: Who am I?"
memory_formatted = "Memory Context:\n'''user: My name is Lennon\nassistant: Hello Lennon'''", task_formatted = ''
current_agent_context = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}
ctx_data = {'channel': 'whatsapp', 'correlation_id': 'corr123', 'owner_id': 'owner1', 'user': {'phone': '123'}}, user_phone = '123'
session_id = 'owner1:123'

    def run(self, user_input: str, **kwargs):
        # Coleta todos os contextos disponíveis
        context_formatted = ""
        memory_formatted = ""
        task_formatted = ""
    
        # Handle self.agent_context being either dict or AgentContext object
        current_agent_context = self.agent_context
        if hasattr(current_agent_context, "model_dump"):
            current_agent_context = current_agent_context.model_dump()
        elif not isinstance(current_agent_context, dict):
            current_agent_context = {}
    
        # Merge context data from self.agent_context and kwargs
        ctx_data = {**current_agent_context, **kwargs}
    
        self.agent_context = AgentContext(
            owner_id=ctx_data.get("owner_id"),
            correlation_id=ctx_data.get("correlation_id"),
            feature=ctx_data.get("feature"),
            feature_id=ctx_data.get("feature_id"),  # Required to populate the ai_result table.
            msg_id=ctx_data.get("msg_id"),
            user_input=user_input,
            user=ctx_data.get("user"),
            channel=ctx_data.get("channel"),
            memory=ctx_data.get("memory"),
            additional_context=ctx_data.get("context")
            or ctx_data.get("additional_context")
            or "",
        )
    
        # ------------------------------------------------------------------
        # INTEGRATION: Load memory from MemoryService if available and not present
        # ------------------------------------------------------------------
        if self.memory_service and not self.agent_context.memory:
            # We use a simple session_id for now.
            # Ideally, session_id should be unique per conversation.
            # In Twilio context, we can use user phone or conversation_id if available.
            # But AgentContext doesn't strictly enforce conversation_id field yet.
            # We'll use owner_id + user_phone as session key fallback if needed.
    
            user_phone = "unknown"
            if self.agent_context.user:
                 user_phone = self.agent_context.user.get("phone", "unknown")
    
            # Construct a session key.
            # Strategy: If conversation_id is passed in kwargs/context, use it.
            # Otherwise use owner_id:user_phone
    
            session_id = ctx_data.get("conversation_id")
            if not session_id:
                session_id = f"{self.agent_context.owner_id}:{user_phone}"
    
            try:
                # Synchronous call for now (RedisMemoryRepository is sync-compatible via blocking calls if needed,
                # but our implementation uses standard redis client which blocks)
                # Wait, our RedisMemoryRepository implementation is synchronous?
                # Let's check... Yes, we implemented it with 'redis' lib, not 'aioredis' (except the import name confusion in previous step).
                # But wait, we imported 'redis' and used 'redis.from_url', which is sync.
    
                # So we can call it directly.
                history = self.memory_service.get_context(session_id, limit=10)
                if history:
                    # Format history as text for the prompt
                    # This is a simple concatenation.
                    # Ideally, we should inject this into message history list, but RoutingAgent uses a single prompt.
                    # We will append it to memory_formatted string.
                    history_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                    self.agent_context.memory = history_text
            except Exception as e:
                logger.error(f"Failed to load memory context: {e}")
    
        if self.agent_context.memory:
            memory_formatted = f"Memory Context:\n'''{self.agent_context.memory}'''"
        if self.agent_context.additional_context:
            task_formatted = (
                f"Task Context:\n'''{self.agent_context.additional_context}'''"
            )
    
        combined_context = "".join(
            [
                (
                    memory_formatted + "\n---------------------------------\n"
                    if memory_formatted
                    else ""
                ),
                (
                    task_formatted + "\n---------------------------------\n"
                    if task_formatted
                    else ""
                ),
            ]
        )
    
        if combined_context:
            context_formatted = f"{combined_context}\n---\n\nUser Message: {user_input}"
        else:
            context_formatted = user_input
    
        logger.info("Starting Routing Agent", event_type="routing_agent_start")
        logger.info(
            "Routing Agent Context",
            event_type="routing_agent_context",
            correlation_id=self.agent_context.correlation_id,
            feature=self.agent_context.feature,
            owner_id=self.agent_context.owner_id,
            channel=self.agent_context.channel,
            phone=(
                self.agent_context.user.get("phone") if self.agent_context.user else "N/A"
            ),
        )
        logger.info(
            "Prompt Formatted", event_type="routing_agent_prompt", prompt=context_formatted
        )
    
        partial_variables = {**self.prompt_extra, "context": context_formatted}
        system_message = self.system_message.format(**partial_variables)
    
        # Converter mensagens para formato LangChain
        messages = [
            SystemMessage(content=system_message),
            *[
                (
                    HumanMessage(content=ex["content"])
                    if ex["role"] == "user"
                    else AIMessage(content=ex["content"])
                )
                for ex in self.examples
            ],
            HumanMessage(content=user_input),
        ]
    
        # Converter Task Agents para Tools em formato LangChain
        tools = [tool.langchain_tool_schema for tool in self.task_agents]
    
        # Bind tools e invocar
        model = self.llm[LLM]
        model_with_tools = model.bind_tools(tools)
        response = model_with_tools.invoke(messages)
    
        # ------------------------------------------------------------------
        # INTEGRATION: Save User Input & AI Response to Memory
        # ------------------------------------------------------------------
        if self.memory_service:
            try:
                # Re-derive session_id
                user_phone = "unknown"
                if self.agent_context.user:
                     user_phone = self.agent_context.user.get("phone", "unknown")
                session_id = ctx_data.get("conversation_id")
                if not session_id:
                    session_id = f"{self.agent_context.owner_id}:{user_phone}"
    
                # Save User Input
                self.memory_service.add_message(session_id, {"role": "user", "content": user_input})
    
                # Save AI Response (if content exists)
                if response.content:
                    self.memory_service.add_message(session_id, {"role": "assistant", "content": response.content})
            except Exception as e:
                 logger.error(f"Failed to save memory context: {e}")
    
    
>       self.ai_log_thought_service.log_agent_thought(
            agent_context=self.agent_context,
            user_input="",
            output=response.content,
            history=self.step_history,
            result_type=AIResultType.AGENT_LOG,
            message=response,
        )
E       AttributeError: 'NoneType' object has no attribute 'log_agent_thought'

src/modules/ai/engines/lchain/core/agents/routing_agent.py:216: AttributeError
========================================================= warnings summary =========================================================
.venv/lib/python3.12/site-packages/supabase/__init__.py:1
  /Users/lennon/projects/ai_engineering/whatsapp_twilio_ai/.venv/lib/python3.12/site-packages/supabase/__init__.py:1: DeprecationWarning: The `gotrue` package is deprecated, is not going to receive updates in the future. Please, use `supabase_auth` instead.
    from gotrue.errors import (

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
===================================================== short test summary info ======================================================
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_reads_memory_on_start - AttributeError: 'NoneType' object has no attribute 'log_agent_thought'
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_saves_interaction_to_memory - AttributeError: 'NoneType' object has no attribute 'log_agent_thought'
FAILED tests/integration/ai/memory/test_agent_memory_integration.py::TestAgentMemoryIntegration::test_agent_populates_context_from_memory - AttributeError: 'NoneType' object has no attribute 'log_agent_thought'
=================================================== 3 failed, 1 warning in 1.02s ===================================================

test_agent_memory_integration.py
tests/integration/ai/memory/test_agent_memory_integration.py

+ 3 - 0

Open Diff

whatsapp_twilio_ai
In Sandbox
Terminal

$ python -m pytest tests/integration/ai/memory/test_agent_memory_integration.py

======================================================= test session starts ========================================================
platform darwin -- Python 3.12.2, pytest-8.3.3, pluggy-1.6.0
rootdir: /Users/lennon/projects/ai_engineering/whatsapp_twilio_ai
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-0.24.0, cov-5.0.0, langsmith-0.6.4
asyncio: mode=Mode.AUTO, default_loop_scope=function
collected 3 items                                                                                                                  

tests/integration/ai/memory/test_agent_memory_integration.py ...                                                             [100%]

========================================================= warnings summary =========================================================
.venv/lib/python3.12/site-packages/supabase/__init__.py:1
  /Users/lennon/projects/ai_engineering/whatsapp_twilio_ai/.venv/lib/python3.12/site-packages/supabase/__init__.py:1: DeprecationWarning: The `gotrue` package is deprecated, is not going to receive updates in the future. Please, use `supabase_auth` instead.
    from gotrue.errors import (

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=================================================== 3 passed, 1 warning in 0.92s ===================================================

report_memory_integration_di_03.md
plan/v4/report/report_memory_integration_di_03.md

+ 64 - 0

Open Diff

Concluí a Fase 1 - Atividade 3: Configuração de DI e Integração .

### 1. Ações Realizadas
1. Container de Injeção de Dependência:
   
   - Registrei o RedisMemoryRepository no Container ( src/core/di/container.py ) reutilizando a configuração existente do Redis.
   - Injetei o serviço de memória na AgentFactory .
2. Propagação da Dependência:
   
   - Atualizei AgentFactory para receber e passar memory_service .
   - Atualizei as funções criadoras ( create_finance_agent , create_relationships_agent ) para aceitar o serviço de memória.
   - Atualizei o RoutingAgent para integrar a lógica de memória no seu ciclo de vida ( run loop).
3. Lógica de Memória no Agente:
   
   - Leitura: Antes de invocar o LLM, o agente busca o histórico no Redis e o adiciona ao contexto.
   - Escrita: Após a resposta do LLM, o agente salva tanto o input do usuário quanto a resposta gerada no Redis.
### 2. Validação e Testes
Criei um teste de integração simulado ( tests/integration/ai/memory/test_agent_memory_integration.py ) que valida todo o fluxo sem depender de serviços externos reais.

- Resultado: 3 passed (Leitura no início, Escrita ao final, População de contexto).
### 3. Relatório
Gerei o relatório técnico consolidando a integração:

- Arquivo: plan/v4/report/report_memory_integration_di_03.md
### Próximos Passos
A Fase 1 (Cache L1 com Redis) está completa. O sistema agora tem memória de curto prazo funcional.

O próximo passo lógico é a Fase 2: Integração com Conversation (Cold Storage) .
Nesta fase, implementaremos o fallback: se o dado não estiver no Redis, buscamos no PostgreSQL ( MessageRepository ) e populamos o cache.

Deseja proceder para a Fase 2 ?

Artifacts

7 files changed + 303 - 4

Open Diff