# Relatório de Implementação: Fila Persistente (In-Memory Queue Risk)

## Resumo
Este relatório documenta a mitigação do risco "Perda de Dados em Reinício (In-Memory Queue)" identificado na análise técnica.
Foi implementado um sistema de fila persistente utilizando **SQLite** como backend padrão para desenvolvimento, substituindo o uso de `BackgroundTasks` (in-memory) do FastAPI para o processamento de respostas de AI.

## Mudanças Realizadas

### 1. Novo Módulo de Fila (`src/core/queue`)
Foi criada uma abstração de fila para permitir diferentes backends (Sqlite, Redis, SQS) no futuro.

*   **`interfaces.py`**: Define a interface `QueueBackend` (enqueue, dequeue, ack, nack).
*   **`models.py`**: Define o modelo `QueueMessage`.
*   **`backends/sqlite.py`**: Implementação do backend persistente usando SQLite.
    *   Cria automaticamente uma tabela `message_queue` no arquivo `queue.db` (configurável).
    *   Suporta persistência segura contra reinícios.
*   **`service.py`**: Serviço `QueueService` que gerencia o backend e o registro de handlers.
*   **`worker.py`**: Script worker dedicado para processar a fila independentemente da API.

### 2. Integração no `TwilioWebhookService`
O serviço de webhook foi refatorado para enfileirar tarefas em vez de executá-las em background threads voláteis.

*   Injeção de dependência do `QueueService`.
*   Substituição de `background_tasks.add_task` por `queue_service.enqueue`.
*   Criação do método `handle_ai_response_task` para processar mensagens desenfileiradas.

### 3. Configuração e Injeção de Dependência
*   **`settings.py`**: Adicionada configuração `QUEUE_BACKEND` e `QUEUE_SQLITE_DB_PATH`.
*   **`container.py`**: Registro do `QueueService` (Singleton) e injeção no `TwilioWebhookService`.

## Como Executar

### 1. Variáveis de Ambiente
Certifique-se de que as variáveis de fila estão configuradas no `.env` (ou use os defaults):

```env
QUEUE_BACKEND=sqlite
QUEUE_SQLITE_DB_PATH=queue.db
```

### 2. Rodar o Worker
O processamento das mensagens de AI agora acontece em um processo separado (Worker). Para iniciá-lo:

```bash
python3 -m src.core.queue.worker
```

Você verá logs indicando que o worker iniciou e registrou o handler `process_ai_response`.

### 3. Rodar a API
A API continua rodando normalmente. Ao receber um webhook, ela enfileira a tarefa no SQLite e retorna 200 OK rapidamente. O Worker pega a tarefa e processa a resposta da AI.

## Benefícios
*   **Persistência**: Se a API ou o Worker caírem, as mensagens continuam salvas no `queue.db` e serão processadas ao reiniciar.
*   **Desacoplamento**: O processamento pesado de AI não impacta a performance da API de Webhook.
*   **Escalabilidade**: Preparado para migrar para Redis/BullMQ ou SQS em produção apenas alterando a configuração e implementando o backend respectivo.

## Próximos Passos
*   Implementar backend `RedisQueueBackend` para produção (se necessário maior throughput).
*   Adicionar monitoramento/dashboard para a fila.
