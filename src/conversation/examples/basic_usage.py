"""
Exemplos de uso básico do Conversation Manager
"""
import asyncio
from conversation_manager.service.conversation_service import ConversationService
from conversation_manager.service.message_service import MessageService
from conversation_manager.service.background_jobs import start_background_jobs, stop_background_jobs
from conversation_manager.entity.message import MessageType


async def example_1_create_conversation():
    """Exemplo 1: Criar uma nova conversa"""
    print("\n" + "=" * 60)
    print("EXEMPLO 1: Criar uma nova conversa")
    print("=" * 60)
    
    service = ConversationService()
    
    # Criar conversa
    conversation = await service.create_conversation(
        phone_number="+5511999999999",
        channel="whatsapp",
        initial_context={"user_name": "João Silva"}
    )
    
    if conversation:
        print(f"✓ Conversa criada: {conversation.id}")
        print(f"  - Telefone: {conversation.phone_number}")
        print(f"  - Status: {conversation.status.value}")
        print(f"  - Canal: {conversation.get_channel()}")
        return conversation.id
    else:
        print("✗ Erro ao criar conversa")
        return None


async def example_2_send_and_receive_messages(conversation_id: str):
    """Exemplo 2: Enviar e receber mensagens"""
    print("\n" + "=" * 60)
    print("EXEMPLO 2: Enviar e receber mensagens")
    print("=" * 60)
    
    message_service = MessageService()
    
    # Receber mensagem do usuário
    user_msg = await message_service.receive_user_message(
        conversation_id=conversation_id,
        content="Olá! Preciso de ajuda com meu pedido"
    )
    
    if user_msg:
        print(f"✓ Mensagem do usuário recebida: {user_msg.id}")
        print(f"  - Conteúdo: {user_msg.content}")
    
    # Enviar resposta do agente
    agent_msg = await message_service.send_agent_message(
        conversation_id=conversation_id,
        content="Olá! Claro, vou te ajudar. Qual é o número do seu pedido?"
    )
    
    if agent_msg:
        print(f"✓ Resposta do agente enviada: {agent_msg.id}")
        print(f"  - Conteúdo: {agent_msg.content}")
    
    # Receber outra mensagem do usuário
    user_msg2 = await message_service.receive_user_message(
        conversation_id=conversation_id,
        content="É o pedido #12345"
    )
    
    if user_msg2:
        print(f"✓ Mensagem do usuário recebida: {user_msg2.id}")


async def example_3_conversation_flow(conversation_id: str):
    """Exemplo 3: Fluxo completo de conversa"""
    print("\n" + "=" * 60)
    print("EXEMPLO 3: Fluxo completo de conversa")
    print("=" * 60)
    
    conv_service = ConversationService()
    msg_service = MessageService()
    
    # Iniciar conversa
    conversation = await conv_service.start_conversation(conversation_id)
    print(f"✓ Conversa iniciada: {conversation.status.value}")
    
    # Trocar algumas mensagens
    await msg_service.send_agent_message(
        conversation_id,
        "Encontrei seu pedido! Vou verificar o status."
    )
    
    await msg_service.receive_user_message(
        conversation_id,
        "Obrigado!"
    )
    
    await msg_service.send_agent_message(
        conversation_id,
        "Seu pedido está a caminho, deve chegar amanhã."
    )
    
    # Mensagem de encerramento do usuário
    await msg_service.receive_user_message(
        conversation_id,
        "Perfeito, muito obrigado pela ajuda! Até logo."
    )
    
    # Verificar se a conversa foi fechada automaticamente
    conversation = await conv_service.get_conversation(conversation_id)
    print(f"✓ Status final: {conversation.status.value}")
    
    if conversation.is_closed():
        print("✓ Conversa fechada automaticamente (intenção detectada)")


async def example_4_list_messages(conversation_id: str):
    """Exemplo 4: Listar mensagens de uma conversa"""
    print("\n" + "=" * 60)
    print("EXEMPLO 4: Listar mensagens")
    print("=" * 60)
    
    msg_service = MessageService()
    
    # Buscar todas as mensagens
    messages = await msg_service.get_conversation_messages(conversation_id)
    
    print(f"✓ {len(messages)} mensagens encontradas:")
    for msg in messages:
        owner_emoji = "👤" if msg.is_user_message() else "🤖"
        print(f"  {owner_emoji} [{msg.message_owner.value}] {msg.content[:50]}...")
    
    # Obter resumo
    summary = await msg_service.get_conversation_summary(conversation_id)
    print(f"\n✓ Resumo da conversa:")
    print(f"  - Total: {summary['total_messages']} mensagens")
    print(f"  - Usuário: {summary['user_messages']}")
    print(f"  - Agente: {summary['agent_messages']}")
    print(f"  - Sistema: {summary['system_messages']}")


async def example_5_statistics():
    """Exemplo 5: Estatísticas de conversas"""
    print("\n" + "=" * 60)
    print("EXEMPLO 5: Estatísticas")
    print("=" * 60)
    
    conv_service = ConversationService()
    
    stats = await conv_service.get_statistics()
    
    print("✓ Estatísticas das conversas:")
    print(f"  - Total: {stats['total']}")
    print(f"  - Ativas: {stats['active']}")
    print(f"  - Fechadas: {stats['closed']}")
    print(f"  - Pendentes: {stats.get('pending', 0)}")
    print(f"  - Em progresso: {stats.get('progress', 0)}")
    print(f"  - Expiradas: {stats.get('expired', 0)}")


async def example_6_background_jobs():
    """Exemplo 6: Jobs em background"""
    print("\n" + "=" * 60)
    print("EXEMPLO 6: Jobs em background")
    print("=" * 60)
    
    print("✓ Iniciando jobs em background...")
    await start_background_jobs()
    
    print("✓ Jobs rodando... (aguardando 30 segundos)")
    await asyncio.sleep(30)
    
    print("✓ Parando jobs...")
    await stop_background_jobs()
    print("✓ Jobs parados")


async def main():
    """Função principal"""
    print("\n" + "=" * 80)
    print(" " * 20 + "CONVERSATION MANAGER - EXEMPLOS DE USO")
    print("=" * 80)
    
    try:
        # Exemplo 1: Criar conversa
        conversation_id = await example_1_create_conversation()
        
        if not conversation_id:
            print("\n✗ Erro ao criar conversa. Verifique as configurações.")
            return
        
        # Exemplo 2: Enviar e receber mensagens
        await example_2_send_and_receive_messages(conversation_id)
        
        # Exemplo 3: Fluxo completo
        await example_3_conversation_flow(conversation_id)
        
        # Exemplo 4: Listar mensagens
        await example_4_list_messages(conversation_id)
        
        # Exemplo 5: Estatísticas
        await example_5_statistics()
        
        # Exemplo 6: Background jobs (comentado por padrão)
        # await example_6_background_jobs()
        
        print("\n" + "=" * 80)
        print(" " * 30 + "EXEMPLOS CONCLUÍDOS!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n✗ Erro ao executar exemplos: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
