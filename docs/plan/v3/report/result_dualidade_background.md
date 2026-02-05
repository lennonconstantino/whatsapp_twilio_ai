# Relatório de Implementação: Unificação do Processamento em Background

## 1. Contexto e Problema
Conforme identificado na análise de riscos (`plan/v3/research_04.md`), o módulo de Conversação implementava um loop customizado (`while running: sleep`) no arquivo `src/modules/conversation/workers/background_tasks.py` para processar timeouts (conversas ociosas e expiradas).

Isso gerava uma **Dualidade Perigosa**:
1.  **Inconsistência**: O módulo Twilio usava o `QueueService` (robusto, distribuído), enquanto Conversação usava um script ad-hoc.
2.  **Single Point of Failure**: O script rodava como um processo único. Se falhasse ou fosse reiniciado, não havia garantia de retomada robusta ou distribuição de carga.
3.  **Risco em Serverless**: Em ambientes como AWS Lambda, loops infinitos são terminados forçosamente.

## 2. Solução Implementada
Refatoramos a arquitetura para utilizar o `QueueService` como motor de execução centralizado. O antigo worker foi transformado em um **Agendador (Scheduler)** leve que apenas enfileira as tarefas, delegando a execução pesada para os workers da fila.

### Componentes Criados/Alterados

#### A. Novos Handlers de Tarefa (`src/modules/conversation/workers/tasks.py`)
Criada classe `ConversationTasks` contendo a lógica de execução encapsulada, compatível com o `QueueService`.

```python
class ConversationTasks:
    async def process_idle_conversations(self, payload): ...
    async def process_expired_conversations(self, payload): ...
```

#### B. Registro no Worker Principal (`src/core/queue/worker.py`)
O worker principal do sistema agora registra automaticamente os handlers de conversação ao iniciar.

```python
# src/core/queue/worker.py
conversation_tasks = ConversationTasks(conversation_service)
queue_service.register_handler("process_idle_conversations", conversation_tasks.process_idle_conversations)
queue_service.register_handler("process_expired_conversations", conversation_tasks.process_expired_conversations)
```

#### C. Scheduler Leve (`src/modules/conversation/workers/background_tasks.py`)
O arquivo original foi completamente reescrito. Agora ele é um `BackgroundScheduler` assíncrono que:
1.  Inicia um loop periódico (configurável, default 60s).
2.  Chama `queue_service.enqueue(...)` para despachar as tarefas.
3.  Não realiza processamento de banco de dados diretamente.

## 3. Benefícios
1.  **Escalabilidade**: O processamento das conversas (que pode ser pesado) agora é distribuído entre os workers da fila. Se a carga aumentar, basta adicionar mais workers.
2.  **Resiliência**: Se o Scheduler falhar, ele pode ser reiniciado rapidamente sem perda de estado (já que ele não mantém estado de conversas). Se um Worker falhar processando uma tarefa, a fila (dependendo do backend, ex: BullMQ/SQS) pode fazer retry.
3.  **Padronização**: Todo processamento assíncrono agora passa pelo `QueueService`, facilitando monitoramento e logging centralizado.

## 4. Próximos Passos
- Validar a execução em ambiente de staging com múltiplos workers para garantir que não há race conditions (o código de serviço já possui Optimistic Locking, o que mitiga isso).
- Considerar migrar o `Scheduler` para um cron externo (K8s CronJob, AWS EventBridge) no futuro para eliminar totalmente a necessidade do container "scheduler" em idle.
