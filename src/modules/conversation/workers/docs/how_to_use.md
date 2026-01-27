# Scheduler e Workers

Este diretório contém os componentes responsáveis pelo processamento em background de conversas, incluindo timeouts (idle) e expiração.

## Estrutura

- `scheduler.py`: Processo produtor que roda continuamente e agenda tarefas periodicamente.
- `tasks.py`: Definição das tarefas que são executadas pelos workers.

## Como Utilizar

O sistema utiliza uma arquitetura Produtor-Consumidor. Você precisa rodar tanto o Scheduler quanto o Worker.

### Via Makefile (Local Development)

1. **Iniciar o Worker** (em um terminal):
   ```bash
   make run-worker
   ```

2. **Iniciar o Scheduler** (em outro terminal):
   ```bash
   make run-scheduler
   ```

### Via Docker Compose

O arquivo `docker-compose.yml` já está configurado com os serviços `worker` e `scheduler`.

```bash
docker-compose up -d
```

## Funcionamento

1. O **Scheduler** acorda a cada 60 segundos (configurável).
2. Ele enfileira tarefas `process_idle_conversations` e `process_expired_conversations` no sistema de filas (QueueService).
3. O **Worker** consome essas tarefas e executa a lógica de negócio (finalizar conversas expiradas/ociosas).

## Configuração

As configurações de tempo (idle timeout, expiration) estão no `src/core/config/settings.py` e podem ser ajustadas via variáveis de ambiente.
