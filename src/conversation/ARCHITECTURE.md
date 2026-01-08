# Arquitetura - Conversation Manager

## Visão Geral

O Conversation Manager é um módulo Python para gestão de conversas com arquitetura em camadas, seguindo princípios de Clean Architecture e Domain-Driven Design (DDD).

```
┌─────────────────────────────────────────────────────────┐
│                    VIEW LAYER (DTOs)                     │
│         Conversão de dados para APIs/Interfaces          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   SERVICE LAYER                          │
│         Lógica de Negócio e Orquestração                │
│  • ConversationService  • MessageService                │
│  • BackgroundJobs                                        │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 REPOSITORY LAYER                         │
│            Acesso e Persistência de Dados               │
│  • ConversationRepository  • MessageRepository          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                   ENTITY LAYER                           │
│              Modelos de Domínio                         │
│  • Conversation  • Message  • Enums                     │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                 DATABASE LAYER                           │
│           PostgreSQL (Supabase)                         │
│  Schema: conversations                                  │
│  • conversations  • messages                            │
└─────────────────────────────────────────────────────────┘
```

---

## Estrutura de Diretórios

```
conversation_manager/
│
├── entity/                      # Camada de Entidades (Domain)
│   ├── __init__.py
│   ├── conversation.py          # Entidade Conversation + ConversationStatus
│   └── message.py               # Entidade Message + Enums
│
├── repository/                  # Camada de Repositórios
│   ├── __init__.py
│   ├── base_repository.py       # Classe base abstrata
│   ├── conversation_repository.py
│   └── message_repository.py
│
├── service/                     # Camada de Serviços (Business Logic)
│   ├── __init__.py
│   ├── conversation_service.py  # Lógica de conversas
│   ├── message_service.py       # Lógica de mensagens
│   └── background_jobs.py       # Jobs assíncronos
│
├── view/                        # Camada de Apresentação (DTOs)
│   ├── __init__.py
│   ├── conversation_dto.py      # DTOs para conversas
│   └── message_dto.py           # DTOs para mensagens
│
├── config/                      # Configurações
│   ├── __init__.py
│   └── settings.py              # Settings com Pydantic
│
├── scripts/                     # Scripts de setup
│   ├── __init__.py
│   ├── setup_database.py        # Setup do banco
│   └── 01_create_schema.sql    # Schema SQL
│
├── seeds/                       # Dados iniciais
│   ├── __init__.py
│   └── load_seeds.py            # Carga de dados fake
│
├── examples/                    # Exemplos de uso
│   ├── __init__.py
│   └── basic_usage.py
│
├── __init__.py                  # Módulo principal
├── .env.example                 # Exemplo de configuração
├── requirements.txt             # Dependências
├── README.md                    # Documentação principal
├── USAGE_GUIDE.md              # Guia de uso
└── ARCHITECTURE.md             # Este arquivo
```

---

## Camadas Detalhadas

### 1. Entity Layer (Domínio)

**Responsabilidade:** Definir as entidades do negócio e suas regras.

**Princípios:**
- Entidades são agnósticas de infraestrutura
- Contêm apenas lógica de negócio relacionada ao próprio objeto
- Imutabilidade sempre que possível (usando dataclasses)

**Componentes:**

#### `Conversation`
- Representa uma conversa no sistema
- Gerencia seu próprio ciclo de vida através de `ConversationStatus`
- Valida transições de estado
- Armazena contexto e metadados

#### `Message`
- Representa uma mensagem trocada
- Detecta intenções (ex: encerramento)
- Categoriza por tipo e proprietário

#### Enums
- `ConversationStatus`: Estados da conversa
- `MessageOwner`: Quem enviou a mensagem
- `MessageType`: Tipo de conteúdo
- `MessageDirection`: Direção da mensagem

---

### 2. Repository Layer

**Responsabilidade:** Abstrair o acesso ao banco de dados.

**Padrões:**
- Repository Pattern
- Generic Repository (BaseRepository)
- Async/Await para operações IO

**Componentes:**

#### `BaseRepository<T>`
Classe genérica abstrata que define operações CRUD:
- `find_by_id()`
- `find_all()`
- `create()`
- `update()`
- `delete()`
- `count()`

#### `ConversationRepository`
Operações específicas para conversas:
- `find_by_phone_number()`
- `find_active_by_phone()`
- `find_expired_conversations()`
- `find_idle_conversations()`
- `update_status()`
- `get_statistics()`

#### `MessageRepository`
Operações específicas para mensagens:
- `find_by_conversation()`
- `find_last_message()`
- `find_user_messages()`
- `search_by_content()`
- `find_media_messages()`

---

### 3. Service Layer

**Responsabilidade:** Implementar a lógica de negócio e orquestrar operações.

**Princípios:**
- Um serviço por agregado (Conversation, Message)
- Coordena múltiplos repositórios quando necessário
- Implementa regras de negócio complexas
- Gerencia transações e consistência

**Componentes:**

#### `ConversationService`
Gerencia o ciclo de vida completo de conversas:
- Criação e inicialização
- Transições de estado validadas
- Processamento de expirações
- Atualização de contexto
- Estatísticas

**Métodos principais:**
```python
create_conversation()
start_conversation()
close_conversation()
transition_status()
process_expired_conversations()
process_idle_conversations()
```

#### `MessageService`
Gerencia mensagens e detecta intenções:
- Envio/recebimento de mensagens
- Detecção automática de encerramento
- Busca e análise de histórico
- Resumos e estatísticas

**Métodos principais:**
```python
receive_user_message()
send_agent_message()
get_conversation_messages()
get_conversation_summary()
```

#### `BackgroundJobScheduler`
Executa tarefas periódicas:
- Verificação de conversas expiradas
- Detecção de conversas inativas
- Agendamento configurável

---

### 4. View Layer (DTOs)

**Responsabilidade:** Definir contratos de dados para APIs/interfaces.

**Princípios:**
- Separação entre modelo de domínio e modelo de apresentação
- Validação de entrada
- Serialização/desserialização
- Versionamento de API

**DTOs de Conversation:**
- `ConversationCreateDTO`: Criação
- `ConversationUpdateDTO`: Atualização
- `ConversationResponseDTO`: Resposta simples
- `ConversationDetailDTO`: Resposta detalhada
- `ConversationListDTO`: Lista com paginação
- `ConversationStatsDTO`: Estatísticas

**DTOs de Message:**
- `MessageCreateDTO`: Criação
- `SendMessageDTO`: Envio
- `ReceiveMessageDTO`: Recebimento
- `MessageResponseDTO`: Resposta
- `MessageListDTO`: Lista
- `MessageSummaryDTO`: Resumo

---

## Fluxos de Dados

### 1. Criação de Conversa

```
Cliente
  │
  ▼
[View] ConversationCreateDTO
  │
  ▼
[Service] ConversationService.create_conversation()
  │
  ├─► Valida dados
  ├─► Verifica conversa ativa existente
  ├─► Cria entidade Conversation
  ├─► Define tempo de expiração
  │
  ▼
[Repository] ConversationRepository.create()
  │
  ▼
[Database] INSERT em conversations
  │
  ▼
[Entity] Conversation
  │
  ▼
[View] ConversationResponseDTO
  │
  ▼
Cliente
```

### 2. Recebimento de Mensagem do Usuário

```
Mensagem do Usuário
  │
  ▼
[View] ReceiveMessageDTO
  │
  ▼
[Service] MessageService.receive_user_message()
  │
  ├─► Valida conversa
  ├─► Cria entidade Message
  ├─► Salva mensagem
  │
  ▼
[Repository] MessageRepository.create()
  │
  ▼
[Database] INSERT em messages
  │
  ▼
[Service] MessageService._check_closure_intent()
  │
  ├─► Analisa palavras-chave
  ├─► Verifica metadados
  │
  ├─► Se detectar encerramento:
  │   ├─► Atualiza contexto
  │   └─► Fecha conversa
  │
  ▼
[View] MessageResponseDTO
  │
  ▼
Cliente
```

### 3. Background Job - Expiração

```
Scheduler (cron)
  │
  ▼
[Service] BackgroundJobScheduler._run_expiry_check_job()
  │
  ▼
[Service] ConversationService.process_expired_conversations()
  │
  ▼
[Repository] ConversationRepository.find_expired_conversations()
  │
  ▼
[Database] SELECT com filtros
  │
  ▼
Para cada conversa expirada:
  │
  ▼
[Service] ConversationService.mark_as_expired()
  │
  ▼
[Repository] ConversationRepository.update_status()
  │
  ▼
[Database] UPDATE status = 'expired'
```

---

## Máquina de Estados - Conversation

```
┌──────────┐
│ PENDING  │◄──── Conversa criada
└─────┬────┘
      │ start_conversation()
      ▼
┌──────────┐
│ PROGRESS │◄──── Conversa ativa
└─────┬────┘
      │
      ├─► Inatividade ──► IDLE_TIMEOUT ──┐
      │                                   │
      │                      reactivate() │
      │◄──────────────────────────────────┘
      │
      ├─► Usuario fecha ──► USER_CLOSED
      ├─► Agente fecha ──► AGENT_CLOSED
      ├─► Suporte fecha ──► SUPPORT_CLOSED
      ├─► Expiração ──────► EXPIRED
      └─► Falha ──────────► FAILED

Estados finais (não transitam):
• USER_CLOSED
• AGENT_CLOSED
• SUPPORT_CLOSED
• EXPIRED
• FAILED
```

**Validação de Transições:**
```python
ConversationStatus.can_transition_to(from_status, to_status)
```

---

## Detecção Inteligente de Encerramento

### Algoritmo Multi-Camada

1. **Análise de Palavras-Chave**
   - Lista configurável de palavras em português
   - Case-insensitive
   - Suporte a frases completas

2. **Sinais Explícitos em Metadados**
   ```python
   metadata = {"explicit_closure": True}
   ```

3. **Eventos de Canal**
   ```python
   metadata = {
       "channel_event": "conversation_end"
       # ou "user_left", "session_closed"
   }
   ```

**Fluxo de Detecção:**
```python
if message.is_user_message():
    has_keyword = check_keywords(message.content)
    has_explicit = message.metadata.get("explicit_closure")
    has_event = message.metadata.get("channel_event") in CLOSURE_EVENTS
    
    if has_keyword or has_explicit or has_event:
        close_conversation()
```

---

## Padrões de Design Utilizados

### 1. Repository Pattern
Abstração do acesso a dados, permitindo trocar implementações.

### 2. Service Layer Pattern
Centraliza lógica de negócio, separada de infraestrutura.

### 3. DTO Pattern
Objetos dedicados para transferência de dados.

### 4. Strategy Pattern
Diferentes estratégias de detecção de encerramento.

### 5. Factory Pattern
Criação de entidades a partir de dicionários (`from_dict()`).

### 6. Observer Pattern (implícito)
Background jobs observam estado do sistema.

### 7. State Machine Pattern
Gerenciamento de estados da conversa com transições validadas.

---

## Princípios SOLID

### Single Responsibility
Cada classe tem uma única responsabilidade:
- `ConversationRepository`: apenas acesso a dados de conversas
- `ConversationService`: apenas lógica de negócio de conversas

### Open/Closed
Aberto para extensão, fechado para modificação:
- `BaseRepository` pode ser estendido sem alteração
- Novos tipos de mensagem podem ser adicionados

### Liskov Substitution
Subclasses podem substituir classes base:
- Qualquer `Repository<T>` pode ser usado onde `BaseRepository<T>` é esperado

### Interface Segregation
Interfaces específicas em vez de genéricas:
- DTOs específicos para cada caso de uso

### Dependency Inversion
Dependências apontam para abstrações:
- Services dependem de repositories (abstrações), não de Supabase diretamente

---

## Considerações de Performance

### Índices no Banco
```sql
-- Consultas por telefone e status
CREATE INDEX idx_conversations_phone_status ON conversations(phone_number, status);

-- Consultas por expiração
CREATE INDEX idx_conversations_expires_at ON conversations(expires_at);

-- Busca em JSONB
CREATE INDEX idx_conversations_metadata ON conversations USING GIN(metadata);

-- Full-text search em mensagens
CREATE INDEX idx_messages_content_search ON messages USING GIN(to_tsvector('portuguese', content));
```

### Async/Await
Todas as operações IO usam async/await para não bloquear.

### Caching (Futuro)
Potencial para adicionar cache em conversas ativas:
```python
# Redis ou similar
conversation = cache.get(f"conversation:{id}")
if not conversation:
    conversation = await repository.find_by_id(id)
    cache.set(f"conversation:{id}", conversation, ttl=300)
```

---

## Segurança

### Validação de Entrada
- DTOs validam dados de entrada
- Repository valida constraints do banco

### Prepared Statements
- Supabase usa prepared statements automaticamente
- Proteção contra SQL Injection

### Permissões
```sql
-- Controle de acesso no schema
GRANT USAGE ON SCHEMA conversations TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA conversations TO app_user;
```

---

## Testes (Sugestão de Implementação)

### Testes Unitários
```python
# test_conversation.py
def test_conversation_status_transition():
    conv = Conversation(phone_number="123", status=ConversationStatus.PENDING)
    assert conv.can_transition_to(ConversationStatus.PROGRESS)
    assert not conv.can_transition_to(ConversationStatus.EXPIRED)
```

### Testes de Integração
```python
# test_conversation_service.py
async def test_create_and_close_conversation():
    service = ConversationService()
    conv = await service.create_conversation("+5511999999999")
    assert conv.status == ConversationStatus.PENDING
    
    closed = await service.close_conversation(conv.id)
    assert closed.status == ConversationStatus.USER_CLOSED
```

### Testes E2E
```python
# test_full_flow.py
async def test_complete_conversation_flow():
    # Criar conversa
    # Enviar mensagens
    # Detectar encerramento
    # Verificar persistência
    pass
```

---

## Extensibilidade

### Adicionar Novo Canal
```python
# Adicionar lógica específica do canal
class TelegramMessageHandler:
    async def handle_message(self, telegram_msg):
        conversation = await get_or_create_conversation(
            phone=telegram_msg.user_id,
            channel="telegram"
        )
        # Processar mensagem...
```

### Adicionar Nova Regra de Encerramento
```python
# Adicionar estratégia de detecção
class SentimentClosureDetector:
    def detect(self, message: Message) -> bool:
        sentiment = analyze_sentiment(message.content)
        return sentiment == "highly_satisfied"

# Usar no MessageService
```

### Adicionar Novo Background Job
```python
# Em background_jobs.py
async def _run_cleanup_old_conversations(self):
    async def cleanup():
        # Limpar conversas muito antigas
        pass
    
    await self._run_periodic_job("Cleanup", 3600, cleanup)
```

---

## Roadmap de Melhorias

1. **Caching**: Redis para conversas ativas
2. **Webhooks**: Notificações de eventos
3. **Analytics**: Métricas e dashboards
4. **Multi-tenancy**: Suporte a múltiplos clientes
5. **Rate Limiting**: Controle de taxa de mensagens
6. **Internacionalização**: Suporte a múltiplos idiomas
7. **Auditoria**: Log de todas as operações
8. **Testes**: Suite completa de testes

---

## Conclusão

Esta arquitetura foi projetada para ser:
- **Escalável**: Suporta crescimento de dados e usuários
- **Manutenível**: Código organizado e desacoplado
- **Testável**: Camadas isoladas facilitam testes
- **Extensível**: Fácil adicionar novos recursos
- **Performática**: Uso de índices e async/await
