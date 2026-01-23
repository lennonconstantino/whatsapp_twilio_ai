# Arquitetura do Sistema

## Visão Macro
O sistema segue uma **Arquitetura Modular em Camadas**, fortemente inspirada em princípios de Domain-Driven Design (DDD) e Clean Architecture. O código é organizado para separar responsabilidades de infraestrutura, lógica de negócio e interfaces externas.

### Estrutura de Diretórios
- `src/core`: Componentes transversais e de infraestrutura (Config, Database, DI, Queue, Logging). Código agnóstico ao negócio.
- `src/modules`: Domínios de negócio isolados (`AI`, `Channels`, `Conversation`, `Identity`).
- `src/api`: Pontos de entrada da aplicação (Controllers/Routes).

## Padrões Adotados

### 1. Injeção de Dependência (DI)
Utiliza a biblioteca `dependency-injector` para gerenciar o ciclo de vida dos componentes.
- **Benefício**: Desacoplamento total entre camadas. Facilita testes unitários através de Mocks e permite troca de implementações (ex: trocar backend de fila) sem alterar o código cliente.
- **Container**: Definido em `src/core/di/container.py`.

### 2. Strategy Pattern (Filas)
O sistema de filas (`src/core/queue`) define uma interface comum (`QueueService`) e implementações intercambiáveis:
- `SqliteBackend`: Para desenvolvimento local e testes simples.
- `BullMQBackend`: Para produção com Redis (alta performance).
- `SQSBackend`: Para ambientes AWS Serverless.

### 3. Repository Pattern
Abstração da camada de dados (`src/core/database/base_repository.py`).
- **Genéricos**: Uso de `Generic[T]` para garantir retorno tipado dos modelos.
- **Isolamento**: O código de negócio não conhece detalhes do SQL ou da biblioteca `supabase-py` diretamente (embora haja um vazamento de abstração conhecido sendo mitigado).

### 4. Compensaçao (Saga Pattern Simplificado)
Para operações que exigem atomicidade em múltiplos passos sem suporte a transações de banco nativas (devido à API REST do Supabase):
- Implementado no `IdentityService` para garantir que falhas na criação de Usuários revertam a criação da Organização (Owner).

### 5. Máquina de Estados (Conversation Lifecycle)
O ciclo de vida da conversa é gerido por uma máquina de estados explícita (`ConversationLifecycle`):
- Estados: `PENDING`, `PROGRESS`, `IDLE_TIMEOUT`, `EXPIRED`, `CLOSED` (vários tipos).
- Regras: Transições válidas são estritamente definidas para evitar estados inconsistentes.
- Concorrência: Uso de Optimistic Locking (`version` column) para prevenir race conditions em atualizações de estado.

## Fluxo de Dados (Data Flow)

1.  **Ingestão**: Webhook do Twilio recebe mensagem -> `TwilioWebhookService`.
2.  **Idempotência**: Verifica unicidade (`message_sid`) e insere no banco. Duplicatas são rejeitadas (DB Constraint).
3.  **Processamento**: Mensagem é processada, contexto da conversa é recuperado/criado.
4.  **Decisão (AI)**: Motor de IA (`LChain`) processa a intenção e gera resposta.
5.  **Resposta**: `TwilioService` envia resposta ao usuário via API do Twilio.
6.  **Background**: Tarefas de manutenção (expiração, timeout) rodam via `QueueService` agendado.
