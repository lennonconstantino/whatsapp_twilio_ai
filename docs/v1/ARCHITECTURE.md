# Arquitetura do Owner Project

## Visão Geral

O Owner Project é um sistema multi-tenant de gerenciamento de conversas com integração Twilio, construído seguindo princípios de Clean Architecture e Domain-Driven Design (DDD).

## Camadas da Arquitetura

### 1. Domain Layer (Modelos)

**Localização**: `src/models/`

Contém as entidades de negócio e enums do sistema:

- **Entidades**: Owner, User, Feature, TwilioAccount, Conversation, Message, AIResult
- **Enums**: ConversationStatus, MessageOwner, MessageType, MessageDirection, UserRole
- **DTOs**: Classes para transferência de dados (Create, Update, Response)

**Características**:
- Independente de frameworks
- Contém regras de negócio básicas
- Validações com Pydantic

### 2. Repository Layer (Persistência)

**Localização**: `src/repositories/`

Implementa o padrão Repository para abstração da persistência:

- **BaseRepository**: CRUD genérico reutilizável
- **Repositories específicos**: Métodos customizados por entidade
- **Isolamento**: Separa lógica de negócio da persistência

**Padrões**:
```python
# Exemplo de uso
owner_repo = OwnerRepository(db_client)
owner = owner_repo.find_by_email("admin@acme.com")
```

### 3. Service Layer (Lógica de Negócio)

**Localização**: `src/services/`

Implementa os casos de uso e regras de negócio complexas:

- **ConversationService**: Gerenciamento completo de conversas
- **ClosureDetector**: Detecção inteligente de encerramento
- **TwilioService**: Integração com Twilio

**Características**:
- Orquestra repositories
- Implementa regras de negócio
- Transações e validações complexas

### 4. API Layer (Apresentação)

**Localização**: `src/api/`

Endpoints REST com FastAPI:

- **conversations**: CRUD de conversas e mensagens
- **webhooks**: Integração Twilio
- **Validação**: Pydantic models
- **Documentação**: Swagger automático

## Fluxo de Dados

### Recebimento de Mensagem (Inbound)

```
Twilio → Webhook → ConversationService → ClosureDetector → Database
                                       ↓
                                  AI Processing (opcional)
```

1. Twilio envia webhook para `/webhooks/twilio/inbound`
2. Sistema identifica/cria conversa
3. Persiste mensagem no banco
4. ClosureDetector analisa intenção de encerramento
5. Retorna confirmação para Twilio

### Envio de Mensagem (Outbound)

```
API Client → ConversationService → TwilioService → Twilio API
                                                  ↓
                                              Cliente
```

1. Cliente chama API para enviar mensagem
2. ConversationService valida e persiste
3. TwilioService envia via API Twilio
4. Status callback atualiza estado

## Multi-Tenancy

### Isolamento de Dados

**Estratégia**: Schema compartilhado com `owner_id`

Todos os dados possuem `owner_id` para isolamento:
- Owners → Users, Features, Conversations
- Row Level Security (RLS) no PostgreSQL
- Policies para garantir acesso correto

### Configurações por Tenant

**Features**: Sistema flexível de habilitação
```json
{
  "feature_id": 1,
  "owner_id": 1,
  "name": "AI Chat Assistant",
  "enabled": true,
  "config_json": {
    "model": "gpt-4",
    "temperature": 0.7
  }
}
```

**Twilio Accounts**: Credenciais específicas por owner
- Permite diferentes números por tenant
- Auth tokens isolados
- Phone numbers em JSONB

## Ciclo de Vida das Conversas

### Estados

```
PENDING → PROGRESS → [CLOSED STATES]
            ↓
      (idle timeout)
            ↓
      IDLE_TIMEOUT
```

**Estados Finais**:
- `AGENT_CLOSED`: Fechada por agente
- `SUPPORT_CLOSED`: Fechada por suporte
- `USER_CLOSED`: Fechada por usuário
- `EXPIRED`: Expiração automática
- `FAILED`: Erro sistêmico
- `IDLE_TIMEOUT`: Inatividade

### Timeouts

**Expiration**: Tempo máximo de vida
```python
# Default: 24 horas
expires_at = started_at + timedelta(minutes=1440)
```

**Idle Timeout**: Inatividade
```python
# Default: 60 minutos
if (now - updated_at) > idle_timeout:
    close_conversation(status=IDLE_TIMEOUT)
```

## Closure Detection (Detecção de Encerramento)

### Algoritmo Multi-fatorial

O ClosureDetector usa múltiplos fatores com pesos:

```python
confidence = (
    keyword_score * 0.5 +      # 50% - Palavras-chave
    pattern_score * 0.3 +       # 30% - Padrões de mensagem
    context_score * 0.2         # 20% - Contexto da conversa
) * duration_modifier           # Penalidade se muito curta
```

### Thresholds

- `< 0.6`: Não fecha, continua normal
- `0.6 - 0.8`: Registra no contexto, aguarda confirmação
- `>= 0.8`: Fecha automaticamente

### Customização por Owner

```python
detector = ClosureDetector()
detector.set_owner_keywords(
    owner_id="1",
    keywords=["fim", "encerrar", "finalizar"]
)
```

## Database Schema

### Principais Tabelas

```sql
owners (1) ----< users (N)
  |
  +----< features (N)
  |
  +----< twilio_accounts (1)
  |
  +----< conversations (N)
          |
          +----< messages (N)
                  |
                  +----< ai_results (N)
```

### Índices de Performance

- `idx_conversations_owner_conv`: Busca por owner
- `idx_messages_conv_ts`: Mensagens ordenadas
- `idx_conversations_expires`: Busca expiradas
- `idx_conversations_updated`: Busca ociosas

### RLS (Row Level Security)

Políticas por tabela garantem isolamento:
```sql
CREATE POLICY "conversations_viewable_by_owner"
  ON conversations
  FOR SELECT
  USING (owner_id = current_setting('app.owner_id')::bigint);
```

## Segurança

### Validação de Webhooks

```python
is_valid = twilio_service.validate_webhook_signature(
    url=request.url,
    params=request.form(),
    signature=request.headers['X-Twilio-Signature']
)
```

### Sanitização

- Pydantic valida todos os inputs
- Queries parametrizadas (Supabase)
- Escape de conteúdo HTML/JSON

### Credenciais

- Variáveis de ambiente
- Nunca commitadas no código
- Auth tokens criptografados no banco

## Observabilidade

### Logging Estruturado

```python
logger.info(
    "Message processed",
    conv_id=conversation.conv_id,
    msg_id=message.msg_id,
    owner_id=conversation.owner_id
)
```

### Métricas (Futuro)

- Tempo de resposta
- Taxa de conversão
- Conversas por owner
- Taxa de detecção de encerramento

### Health Checks

- `/health`: Status da API
- `/webhooks/twilio/health`: Status dos webhooks
- Database connection check

## Escalabilidade

### Horizontal Scaling

- API stateless (pode replicar)
- Sessões no banco (não em memória)
- Load balancer distribuir requisições

### Performance

- Índices otimizados
- Paginação em queries
- Caching (futuro: Redis)
- Connection pooling

### Limites

- Rate limiting por owner (futuro)
- Quota de mensagens (futuro)
- Throttling de webhooks

## Extensibilidade

### Adicionar Nova Feature

1. Criar modelo em `models/domain.py`
2. Criar repository em `repositories/`
3. Criar service em `services/`
4. Adicionar rotas em `api/`
5. Migração SQL

### Adicionar Novo Canal

Além do Twilio:
1. Criar service específico (ex: `WhatsAppBusinessService`)
2. Implementar webhook handler
3. Adaptar `MessageCreate` para o canal
4. Configurar em `features`

### AI Processing

```python
class AIProcessor:
    def process_message(self, message: Message) -> AIResult:
        # Implementar lógica de IA
        result = call_ai_model(message.content)
        return AIResult(
            msg_id=message.msg_id,
            feature_id=feature_id,
            result_json=result
        )
```

## Testes

### Estrutura

```
tests/
├── unit/              # Testes unitários
│   ├── test_models.py
│   ├── test_repositories.py
│   └── test_services.py
├── integration/       # Testes de integração
│   ├── test_api.py
│   └── test_database.py
└── e2e/              # Testes end-to-end
    └── test_flows.py
```

### Mocks

```python
# Mockar repositories
mock_repo = Mock()
mock_repo.find_by_id.return_value = conversation

service = ConversationService(conversation_repo=mock_repo)
```

## Deploy

### Ambiente de Desenvolvimento

```bash
docker-compose up
```

### Ambiente de Produção

1. Build da imagem Docker
2. Deploy em Kubernetes/ECS
3. Configurar variáveis de ambiente
4. Rodar migrações
5. Health checks

### CI/CD

```yaml
# .github/workflows/deploy.yml
- name: Run tests
  run: pytest tests/
- name: Build image
  run: docker build -t owner-api .
- name: Deploy
  run: kubectl apply -f k8s/
```

## Próximos Passos

### Melhorias Planejadas

1. **Caching**: Redis para sessões e dados frequentes
2. **Queue**: Celery para processamento assíncrono
3. **Webhooks Outbound**: Notificar sistemas externos
4. **Analytics**: Dashboard de métricas
5. **AI Advanced**: NLP para melhor detecção
6. **Multi-channel**: Telegram, Instagram, SMS
7. **Backup**: Estratégia de backup automático
8. **Monitoring**: Prometheus + Grafana
