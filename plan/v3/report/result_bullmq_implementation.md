# Relatório de Implementação: Suporte a BullMQ (Redis)

## Resumo
Este relatório documenta a implementação do suporte ao **BullMQ** como backend de fila, atendendo ao requisito de "Default para produção SaaS". A solução utiliza a biblioteca `bullmq` (Python port) sobre Redis, garantindo compatibilidade com dashboards e ferramentas do ecossistema BullMQ.

## Mudanças Realizadas

### 1. Novo Backend `BullMQBackend`
Criado em `src/core/queue/backends/bullmq.py`.
*   Implementa a interface `QueueBackend`.
*   **Enqueue**: Utiliza `Queue.add` para enviar mensagens para o Redis, compatível com consumidores Node.js/Python.
*   **Start Consuming**: Implementa um consumidor robusto utilizando `Worker` da biblioteca BullMQ.
*   **Processamento**: Converte os jobs do BullMQ de volta para `QueueMessage` e invoca o handler registrado.

### 2. Refatoração do `QueueService`
O serviço foi atualizado para suportar tanto backends baseados em **Pull** (SQLite) quanto em **Push** (BullMQ/Redis).
*   Adicionado suporte ao método `start_consuming` na interface `QueueBackend`.
*   O `QueueService.start_worker` agora delega o controle do loop para o backend via `start_consuming`.
*   Adicionado factory logic em `_init_backend` para instanciar `BullMQBackend` quando `QUEUE_BACKEND=bullmq`.

### 3. Configuração
*   Adicionado campo `redis_url` em `QueueSettings` (`src/core/config/settings.py`).
*   Adicionado suporte a variáveis de ambiente:
    *   `QUEUE_BACKEND`: `sqlite` (dev) ou `bullmq` (prod).
    *   `QUEUE_REDIS_URL`: URL de conexão Redis (ex: `redis://localhost:6379`).

## Como Usar em Produção (SaaS)

1.  Instalar dependências (já incluídas): `bullmq`, `redis`.
2.  Configurar variáveis de ambiente no `.env`:
    ```env
    QUEUE_BACKEND=bullmq
    QUEUE_REDIS_URL=redis://user:pass@redis-host:6379/0
    ```
3.  Rodar o Worker normalmente:
    ```bash
    python3 -m src.core.queue.worker
    ```

## Trade-offs e Considerações
*   **BullMQ vs Redis Puro**: O uso da biblioteca `bullmq` traz recursos avançados (retries exponenciais, rate limiting, prioridade) "de graça", mas adiciona uma dependência levemente mais complexa que um simples `LPUSH/RPOP`.
*   **Compatibilidade**: A implementação permite que, futuramente, dashboards como [Taskforce.sh](https://taskforce.sh/) ou [Bull Board](https://github.com/felixmosh/bull-board) sejam usados para monitorar as filas visualmente.
*   **Fallback**: O sistema mantém total compatibilidade com SQLite para ambientes de desenvolvimento onde subir um Redis não é desejado.

## Próximos Passos
*   Testar conexão com cluster Redis em staging.
*   Configurar retries e dead-letter queue (DLQ) nas opções do BullMQ se necessário customização além do padrão.
