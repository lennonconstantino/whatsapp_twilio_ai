import pytest
from datetime import datetime, timedelta, timezone
from src.services.conversation_service import ConversationService
from src.models.domain import MessageCreateDTO
from src.models.enums import ConversationStatus, MessageOwner
from src.utils import get_logger

logger = get_logger(__name__)

def test_complete_conversation_lifecycle():
    """Testa ciclo completo: PENDING → PROGRESS → IDLE_TIMEOUT → PROGRESS → AGENT_CLOSED"""
    service = ConversationService()
    
    # Gerar números aleatórios para evitar colisão
    import random
    suffix = random.randint(1000, 9999)
    from_number = f"+55119{suffix}"
    to_number = f"+55118{suffix}"
    
    # 1. Criar conversa (PENDING)
    logger.info("Step 1: Creating conversation (PENDING)")
    conv = service.get_or_create_conversation(
        owner_id=1,
        from_number=from_number,
        to_number=to_number,
        channel="whatsapp"
    )
    assert conv.status == ConversationStatus.PENDING.value
    
    # 2. Usuário envia mensagem (permanece PENDING)
    logger.info("Step 2: User message (Keep PENDING)")
    user_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number=from_number,
        to_number=to_number,
        body="Preciso de ajuda",
        message_owner=MessageOwner.USER
    )
    service.add_message(conv, user_msg)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PENDING.value
    
    # 3. Agente aceita (PENDING → PROGRESS)
    logger.info("Step 3: Agent accepts (PENDING -> PROGRESS)")
    agent_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number=to_number,
        to_number=from_number,
        body="Olá! Como posso ajudar?",
        message_owner=MessageOwner.AGENT
    )
    service.add_message(conv, agent_msg)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    # Verificar contexto
    assert conv.context is not None
    assert 'accepted_by' in conv.context
    assert conv.context['accepted_by']['agent_type'] == MessageOwner.AGENT.value
    
    # 4. Simular inatividade (PROGRESS → IDLE_TIMEOUT)
    logger.info("Step 4: Simulate IDLE (PROGRESS -> IDLE_TIMEOUT)")
    # Atualizar updated_at para simular inatividade
    # Usando acesso direto ao cliente do repositório para "hackear" o tempo
    past_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    service.conversation_repo.client.table("conversations")\
        .update({"updated_at": past_time.isoformat()})\
        .eq("conv_id", conv.conv_id)\
        .execute()
    
    # Processar idle (assumindo que 15 min é o timeout configurado ou passado)
    processed_count = service.process_idle_conversations(idle_minutes=15)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    # Se o processamento funcionou, deve estar em IDLE_TIMEOUT
    # Nota: process_idle_conversations busca active_statuses. PROGRESS é active.
    assert conv.status == ConversationStatus.IDLE_TIMEOUT.value
    
    # 5. Usuário retorna (IDLE_TIMEOUT → PROGRESS)
    logger.info("Step 5: User returns (IDLE_TIMEOUT -> PROGRESS)")
    user_msg2 = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number=from_number,
        to_number=to_number,
        body="Ainda está aí?",
        message_owner=MessageOwner.USER
    )
    service.add_message(conv, user_msg2)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    assert 'reactivated_from_idle' in conv.context
    
    # 6. Encerramento natural (PROGRESS → AGENT_CLOSED)
    logger.info("Step 6: Natural closure (PROGRESS -> AGENT_CLOSED)")
    
    # Agente encerra
    # A política de fechamento pode depender de detecção de intenção ou comando explícito
    # Aqui vamos usar o close_conversation direto ou simular mensagem de encerramento se o detector estiver ativo
    
    # Vamos forçar o fechamento via service para garantir
    service.close_conversation(conv, ConversationStatus.AGENT_CLOSED)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.AGENT_CLOSED.value
