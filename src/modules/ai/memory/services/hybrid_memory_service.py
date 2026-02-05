from typing import Any, Dict, List, Optional

from src.core.config.settings import settings
from src.core.utils.logging import get_logger
from src.modules.ai.memory.interfaces.memory_interface import MemoryInterface
from src.modules.ai.memory.repositories.redis_memory_repository import RedisMemoryRepository
from src.modules.ai.memory.repositories.vector_memory_repository import VectorMemoryRepository
from src.modules.conversation.repositories.message_repository import MessageRepository
from src.modules.conversation.enums.message_owner import MessageOwner

logger = get_logger(__name__)


class HybridMemoryService(MemoryInterface):
    """
    Hybrid Memory Service (L1 Cache + L2 Persistence + L3 Semantic).
    Orchestrates data flow between Redis, PostgreSQL and Vector Store.
    """

    def __init__(
        self,
        redis_repo: RedisMemoryRepository,
        message_repo: MessageRepository,
        vector_repo: Optional[VectorMemoryRepository] = None,
    ):
        self.redis_repo = redis_repo
        self.message_repo = message_repo
        self.vector_repo = vector_repo

    def get_context(
        self,
        session_id: str,
        limit: int = 10,
        query: Optional[str] = None,
        owner_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves context with Read-Through strategy:
        1. Try L1 (Redis)
        2. If miss, try L2 (DB) and populate L1
        3. If query provided, try L3 (Vector) and append relevant info
        """
        context_messages = []
        
        # 1. Try Redis
        try:
            messages = self.redis_repo.get_context(
                session_id,
                limit,
                owner_id=owner_id,
                user_id=user_id,
            )
            if messages:
                logger.debug(f"Cache HIT for session {session_id}")
                context_messages = messages
        except Exception as e:
            logger.warning(f"Error reading from Redis: {e}")

        # 2. Fallback to DB if Redis failed or returned empty (and we expect messages)
        # Note: Empty list from Redis might mean "really empty" or "cache miss".
        # RedisMemoryRepository returns [] on miss.
        # But if the conversation is new, DB is also empty.
        # Ideally, Redis should differentiate Miss from Empty.
        # But for now, if empty, we check DB just to be sure (safe fallback).
        if not context_messages:
            logger.debug(f"Cache MISS or EMPTY for session {session_id}. Fetching from DB.")
            try:
                # session_id is conversation_id (conv_id)
                db_messages = self.message_repo.find_recent_by_conversation(session_id, limit)
                
                if db_messages:
                    # Convert to Agent format
                    agent_messages = []
                    for msg in db_messages:
                        # Map Message entity to Agent dict format
                        role = "user" if msg.message_owner == MessageOwner.USER else "assistant"
                        content = msg.body or ""
                        
                        # Basic validation
                        if not content.strip():
                            continue
                            
                        formatted_msg = {
                            "role": role,
                            "content": content
                        }
                        agent_messages.append(formatted_msg)
                    
                    context_messages = agent_messages

                    # 3. Populate Redis (Read-Through)
                    # Optimization: Only populate if list is not empty
                    if agent_messages:
                        self.redis_repo.add_messages_bulk(session_id, agent_messages)
            except Exception as e:
                logger.error(f"Error reading from DB for session {session_id}: {e}")
        
        # 4. Semantic Search (L3)
        if query and self.vector_repo:
            if not owner_id:
                logger.error("Memory retrieval L3 requires owner_id for security isolation. Skipping vector search.")
                # We skip L3 search to prevent cross-tenant data leakage
                return context_messages

            try:
                retrieval_filter: Dict[str, Any] = {}
                retrieval_filter["owner_id"] = owner_id
                
                if user_id:
                    retrieval_filter["user_id"] = user_id
                
                logger.info(f"HybridMemoryService: executing semantic search query='{query}' filters={retrieval_filter}")

                top_k = settings.memory.semantic_top_k
                match_threshold = settings.memory.semantic_match_threshold

                if settings.memory.enable_hybrid_retrieval:
                    semantic_results = self.vector_repo.hybrid_search_relevant(
                        owner_id=owner_id,
                        query=query,
                        limit=top_k,
                        match_threshold=match_threshold,
                        filter=retrieval_filter or None,
                        weight_vector=settings.memory.hybrid_weight_vector,
                        weight_text=settings.memory.hybrid_weight_text,
                        rrf_k=settings.memory.hybrid_rrf_k,
                        fts_language=settings.memory.fts_language,
                    )
                else:
                    semantic_results = self.vector_repo.vector_search_relevant(
                        owner_id=owner_id,
                        query=query,
                        limit=top_k,
                        match_threshold=match_threshold,
                        filter=retrieval_filter or None,
                    )
                
                if semantic_results:
                    logger.info(f"HybridMemoryService: found {len(semantic_results)} raw results")
                    recent_contents = {str(m.get("content", "")).strip() for m in context_messages if m.get("content")}
                    deduped_results = []
                    for res in semantic_results:
                        content = str(res.get("content", "")).strip()
                        if not content:
                            continue
                        if content in recent_contents:
                            continue
                        deduped_results.append(res)

                    relevant_info = "\n".join([f"- {res['content']}" for res in deduped_results])
                    system_msg = {
                        "role": "system",
                        "content": f"Relevant Information from past conversations:\n{relevant_info}"
                    }
                    # Prepend to context
                    context_messages.insert(0, system_msg)
                    logger.info(f"Added {len(deduped_results)} semantic results to context")
            except Exception as e:
                logger.warning(f"Error in semantic search: {e}")

        return context_messages

    def add_message(self, session_id: str, message: Dict[str, Any]) -> None:
        """
        Adds message to Memory (Write-Through or Write-Back).
        In our architecture:
        - DB write happens in Webhook (Source of Truth).
        - Here we just update the Cache (Redis).
        """
        # We assume DB is already updated by the time this is called, 
        # OR this is called by Agent to "remember" something (but Agent relies on Webhook for persistence).
        # Actually, Agent sends response -> Webhook -> DB.
        # Then Webhook should update Cache.
        # But if Agent calls memory.add_message, it's updating the "Thought" memory?
        # The MemoryInterface is for Conversation History.
        
        # If the Agent adds a message here, it should be reflected in Redis.
        self.redis_repo.add_message(session_id, message)
