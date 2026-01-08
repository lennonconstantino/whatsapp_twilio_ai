"""
Script para carregar dados fake no banco de dados
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from faker import Faker

# Adicionar o diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from conversation_manager.entity.conversation import Conversation, ConversationStatus
from conversation_manager.entity.message import Message, MessageOwner, MessageType, MessageDirection
from conversation_manager.repository.conversation_repository import ConversationRepository
from conversation_manager.repository.message_repository import MessageRepository

fake = Faker('pt_BR')


async def create_fake_conversations(repo: ConversationRepository, count: int = 10):
    """Cria conversas fake"""
    conversations = []
    statuses = list(ConversationStatus)
    
    print(f"Criando {count} conversas fake...")
    
    for i in range(count):
        phone = fake.phone_number().replace(" ", "").replace("-", "")[:15]
        status = fake.random_element(statuses)
        
        created_at = fake.date_time_between(start_date='-30d', end_date='now')
        expires_at = created_at + timedelta(hours=24)
        
        conversation = Conversation(
            phone_number=phone,
            status=status,
            context={
                "user_name": fake.name(),
                "session_id": fake.uuid4(),
            },
            created_at=created_at,
            updated_at=created_at + timedelta(minutes=fake.random_int(1, 120)),
            expires_at=expires_at if status not in [
                ConversationStatus.AGENT_CLOSED,
                ConversationStatus.USER_CLOSED,
                ConversationStatus.EXPIRED,
                ConversationStatus.FAILED
            ] else None,
            metadata={
                "channel": fake.random_element(["whatsapp", "telegram", "webchat"]),
                "device": fake.random_element(["mobile", "desktop", "tablet"]),
            }
        )
        
        created = await repo.create(conversation)
        if created:
            conversations.append(created)
            print(f"  ✓ Conversa {i+1}/{count}: {created.id} ({created.status.value})")
    
    return conversations


async def create_fake_messages(repo: MessageRepository, conversation_id: str, count: int = 5):
    """Cria mensagens fake para uma conversa"""
    messages = []
    
    message_templates = [
        "Olá, preciso de ajuda com meu pedido",
        "Qual o status da minha solicitação?",
        "Obrigado pela ajuda!",
        "Não consegui resolver o problema",
        "Pode me passar mais informações?",
        "Entendi, muito obrigado!",
        "Quando posso esperar uma resposta?",
        "Perfeito, era isso mesmo que eu precisava",
        "Ainda tenho algumas dúvidas",
        "Tchau, até logo!",
    ]
    
    for i in range(count):
        # Alternar entre mensagens de usuário e agente
        is_user = i % 2 == 0
        owner = MessageOwner.USER if is_user else MessageOwner.AGENT
        direction = MessageDirection.INBOUND if is_user else MessageDirection.OUTBOUND
        
        content = fake.random_element(message_templates) if is_user else fake.sentence()
        
        message = Message(
            conversation_id=conversation_id,
            content=content,
            message_owner=owner,
            message_type=MessageType.TEXT,
            direction=direction,
            created_at=fake.date_time_between(start_date='-1d', end_date='now'),
            metadata={
                "platform": fake.random_element(["android", "ios", "web"]),
            }
        )
        
        created = await repo.create(message)
        if created:
            messages.append(created)
    
    return messages


async def main():
    """Função principal"""
    print("=" * 60)
    print("CARREGANDO DADOS FAKE")
    print("=" * 60)
    
    # Repositórios
    conversation_repo = ConversationRepository()
    message_repo = MessageRepository()
    
    try:
        # Criar conversas
        conversations = await create_fake_conversations(conversation_repo, count=15)
        print(f"\n✓ {len(conversations)} conversas criadas")
        
        # Criar mensagens para cada conversa
        print(f"\nCriando mensagens para as conversas...")
        total_messages = 0
        
        for conversation in conversations:
            # Apenas conversas ativas têm mensagens
            if conversation.is_active():
                msg_count = fake.random_int(3, 10)
                messages = await create_fake_messages(
                    message_repo, 
                    conversation.id, 
                    count=msg_count
                )
                total_messages += len(messages)
                print(f"  ✓ {len(messages)} mensagens para conversa {conversation.id}")
        
        print(f"\n✓ {total_messages} mensagens criadas")
        
        print("\n" + "=" * 60)
        print("DADOS FAKE CARREGADOS COM SUCESSO!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Erro ao carregar dados: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
