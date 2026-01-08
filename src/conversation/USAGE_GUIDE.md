# Guia de Uso - Conversation Manager

## Índice

1. [Instalação e Configuração](#instalação-e-configuração)
2. [Conceitos Principais](#conceitos-principais)
3. [Uso Básico](#uso-básico)
4. [Casos de Uso Avançados](#casos-de-uso-avançados)
5. [Background Jobs](#background-jobs)
6. [Detecção de Encerramento](#detecção-de-encerramento)
7. [API Reference](#api-reference)

---

## Instalação e Configuração

### 1. Instalar dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e configure:

```bash
cp .env.example .env
```

Edite o `.env`:

```env
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=sua-chave-anon
DATABASE_SCHEMA=conversations
CONVERSATION_EXPIRY_HOURS=24
IDLE_TIMEOUT_MINUTES=30
```

### 3. Criar schema e tabelas no banco

```bash
python -m conversation_manager.scripts.setup_database
```

### 4. (Opcional) Carregar dados fake para testes

```bash
python -m conversation_manager.seeds.load_seeds
```

---

## Conceitos Principais

### Entidades

#### Conversation
Representa uma conversa entre usuário e sistema/agente.

**Campos principais:**
- `id`: Identificador único
- `phone_number`: Número de telefone do usuário
- `status`: Status atual (PENDING, PROGRESS, etc)
- `context`: Contexto da conversa (dict)
- `expires_at`: Data/hora de expiração
- `metadata`: Metadados (canal, dispositivo, etc)

**Estados possíveis:**
- `PENDING`: Aguardando interação
- `PROGRESS`: Em andamento
- `IDLE_TIMEOUT`: Inativa por timeout
- `USER_CLOSED`: Encerrada pelo usuário
- `AGENT_CLOSED`: Encerrada pelo agente
- `SUPPORT_CLOSED`: Encerrada pelo suporte
- `EXPIRED`: Expirada automaticamente
- `FAILED`: Fechada por falha

#### Message
Representa uma mensagem trocada na conversa.

**Campos principais:**
- `id`: Identificador único
- `conversation_id`: ID da conversa
- `content`: Conteúdo da mensagem
- `message_owner`: Quem enviou (USER, AGENT, SYSTEM, TOOL, SUPPORT)
- `message_type`: Tipo (TEXT, IMAGE, AUDIO, VIDEO, DOCUMENT)
- `direction`: Direção (INBOUND, OUTBOUND)

---

## Uso Básico

### 1. Criar uma conversa

```python
from conversation_manager.service.conversation_service import ConversationService

service = ConversationService()

# Criar nova conversa
conversation = await service.create_conversation(
    phone_number="+5511999999999",
    channel="whatsapp",
    initial_context={"user_name": "João Silva"}
)

print(f"Conversa criada: {conversation.id}")
```

### 2. Enviar e receber mensagens

```python
from conversation_manager.service.message_service import MessageService

msg_service = MessageService()

# Receber mensagem do usuário
user_msg = await msg_service.receive_user_message(
    conversation_id=conversation.id,
    content="Olá, preciso de ajuda!"
)

# Enviar resposta do agente
agent_msg = await msg_service.send_agent_message(
    conversation_id=conversation.id,
    content="Olá! Como posso ajudá-lo?"
)
```

### 3. Transicionar estados

```python
# Iniciar conversa (PENDING -> PROGRESS)
await service.start_conversation(conversation.id)

# Fechar conversa
await service.close_conversation(conversation.id, closed_by="user")
```

### 4. Listar mensagens

```python
# Buscar todas as mensagens da conversa
messages = await msg_service.get_conversation_messages(conversation.id)

for msg in messages:
    print(f"{msg.message_owner.value}: {msg.content}")
```

---

## Casos de Uso Avançados

### 1. Buscar ou criar conversa ativa

```python
# Buscar conversa ativa existente ou criar nova
active = await service.get_active_conversation(phone_number)

if not active:
    active = await service.create_conversation(
        phone_number=phone_number,
        channel="whatsapp"
    )
```

### 2. Atualizar contexto da conversa

```python
# Adicionar informações ao contexto
await service.update_context(
    conversation.id,
    {
        "last_intent": "check_order",
        "order_number": "12345",
        "resolved": True
    },
    merge=True  # Faz merge com contexto existente
)
```

### 3. Mensagens de mídia

```python
# Receber imagem do usuário
await msg_service.receive_user_message(
    conversation_id=conversation.id,
    content="Segue foto do problema",
    message_type=MessageType.IMAGE,
    path="/path/to/image.jpg"
)
```

### 4. Obter resumo da conversa

```python
summary = await msg_service.get_conversation_summary(conversation.id)

print(f"Total de mensagens: {summary['total_messages']}")
print(f"Mensagens do usuário: {summary['user_messages']}")
print(f"Mensagens do agente: {summary['agent_messages']}")
print(f"Última mensagem: {summary['last_message_at']}")
```

### 5. Estatísticas gerais

```python
stats = await service.get_statistics()

print(f"Total de conversas: {stats['total']}")
print(f"Conversas ativas: {stats['active']}")
print(f"Conversas fechadas: {stats['closed']}")
```

---

## Background Jobs

O módulo inclui jobs automáticos para:
- Verificar e expirar conversas antigas
- Detectar e marcar conversas inativas

### Iniciar background jobs

```python
from conversation_manager.service.background_jobs import start_background_jobs, stop_background_jobs

# Iniciar
await start_background_jobs()

# Seu código aqui...

# Parar quando necessário
await stop_background_jobs()
```

### Processar manualmente

```python
# Processar conversas expiradas
expired_ids = await service.process_expired_conversations()
print(f"{len(expired_ids)} conversas expiradas")

# Processar conversas inativas
idle_ids = await service.process_idle_conversations()
print(f"{len(idle_ids)} conversas inativas")
```

---

## Detecção de Encerramento

O módulo detecta automaticamente quando o usuário deseja encerrar a conversa através de:

### 1. Palavras-chave (configurável)

Palavras detectadas por padrão:
- "obrigado", "obrigada"
- "tchau", "até logo"
- "valeu", "pode fechar"
- "já resolvi", "entendi"
- etc.

Configure suas próprias palavras em `.env`:

```env
CLOSURE_KEYWORDS=obrigado,tchau,até logo,valeu
```

### 2. Sinais nos metadados

```python
# Mensagem com sinal explícito de encerramento
await msg_service.receive_user_message(
    conversation_id=conversation.id,
    content="Obrigado!",
    metadata={
        "explicit_closure": True  # Sinal explícito
    }
)
```

### 3. Eventos de canal

```python
# Evento de canal indicando encerramento
await msg_service.receive_user_message(
    conversation_id=conversation.id,
    content="",
    metadata={
        "channel_event": "conversation_end"  # ou "user_left", "session_closed"
    }
)
```

---

## API Reference

### ConversationService

#### `create_conversation(phone_number, channel=None, initial_context=None)`
Cria uma nova conversa.

#### `get_conversation(conversation_id)`
Busca conversa por ID.

#### `get_active_conversation(phone_number)`
Busca conversa ativa para um telefone.

#### `start_conversation(conversation_id)`
Inicia conversa (PENDING → PROGRESS).

#### `close_conversation(conversation_id, closed_by="user")`
Fecha conversa.

#### `update_context(conversation_id, context_updates, merge=True)`
Atualiza contexto da conversa.

#### `process_expired_conversations()`
Processa conversas expiradas.

#### `get_statistics()`
Retorna estatísticas das conversas.

### MessageService

#### `create_message(conversation_id, content, message_owner, ...)`
Cria uma nova mensagem.

#### `get_conversation_messages(conversation_id, limit=None, order="asc")`
Lista mensagens da conversa.

#### `send_agent_message(conversation_id, content)`
Envia mensagem do agente.

#### `receive_user_message(conversation_id, content, ...)`
Recebe mensagem do usuário.

#### `get_conversation_summary(conversation_id)`
Retorna resumo da conversa.

#### `search_messages(conversation_id, search_term)`
Busca mensagens por conteúdo.

---

## Exemplos Práticos

### Integração com WhatsApp

```python
async def handle_whatsapp_message(phone: str, message: str, media_url: str = None):
    """Handler para mensagens do WhatsApp"""
    
    # Buscar ou criar conversa
    conversation = await conv_service.get_active_conversation(phone)
    if not conversation:
        conversation = await conv_service.create_conversation(
            phone_number=phone,
            channel="whatsapp"
        )
    
    # Processar mensagem
    if media_url:
        await msg_service.receive_user_message(
            conversation.id,
            content=message,
            message_type=MessageType.IMAGE,
            path=media_url
        )
    else:
        await msg_service.receive_user_message(
            conversation.id,
            content=message
        )
    
    # Gerar resposta do agente (sua lógica aqui)
    response = generate_ai_response(message)
    
    await msg_service.send_agent_message(
        conversation.id,
        content=response
    )
```

### Sistema de Filas com Status

```python
# Marcar conversa como aguardando suporte
await conv_service.update_context(
    conversation.id,
    {"waiting_support": True, "queue_position": 3}
)

# Quando suporte atender
await conv_service.update_context(
    conversation.id,
    {"waiting_support": False, "attended_by": "agent_123"}
)
```

---

## Troubleshooting

### Conversa não fecha automaticamente

Verifique se:
1. As palavras-chave estão configuradas corretamente
2. A mensagem é realmente do usuário (MessageOwner.USER)
3. A conversa está ativa (não fechada)

### Background jobs não funcionam

Certifique-se de:
1. Chamar `await start_background_jobs()` no início
2. Manter o loop de eventos rodando
3. Não bloquear o thread principal

### Erro de conexão com Supabase

Verifique:
1. URL e KEY do Supabase no `.env`
2. Schema criado corretamente no banco
3. Permissões de acesso ao schema

---

## Suporte

Para mais informações ou problemas, consulte:
- Documentação do Supabase: https://supabase.com/docs
- Issues do projeto
