# Background Tasks: Arquitetura Unificada e Compatibilidade

## Status Atual: ✅ Arquitetura Unificada (Producer-Consumer)

A implementação antiga baseada em scripts monolíticos (`background_tasks.py`) foi substituída por uma arquitetura moderna e escalável utilizando o padrão **Producer-Consumer** sobre o `QueueService`.

### Componentes

1.  **Scheduler (Producer):**
    *   Arquivo: `src/modules/conversation/workers/scheduler.py`
    *   Função: Roda em loop (daemon), verifica intervalos de tempo e enfileira mensagens (`process_idle_conversations`, `process_expired_conversations`).
    *   Não executa lógica de negócio pesada, apenas agendamento.

2.  **Worker (Consumer):**
    *   Arquivo: `src/core/queue/worker.py` e `src/modules/conversation/workers/tasks.py`
    *   Função: Consome mensagens da fila e executa a lógica de negócio (queries de banco, updates, notificações).
    *   Escalável horizontalmente (pode ter múltiplos workers).

## Compatibilidade com Session Key

### ✅ Totalmente Compatível

A lógica de detecção de conversas ociosas ou expiradas baseia-se em queries que filtram por `status`, `updated_at` e `expires_at`. A introdução de `session_key` ou mudanças na unicidade de `from_number` não afetam negativamente essas queries. Pelo contrário, a redução de duplicidade de conversas melhora a performance das varreduras.

```python
# Exemplo de query utilizada (ConversationRepository)
def find_expired_conversations(self, limit: int = 100):
    return self.client.table(self.table_name)\
        .select("*")\
        .in_("status", ["pending", "progress"])\
        .lt("expires_at", now)\
        .limit(limit)\
        .execute()
```

## Benefícios da Nova Arquitetura

| Aspecto | Implementação Antiga (Script) | Nova Implementação (Queue) |
| :--- | :--- | :--- |
| **Escalabilidade** | Limitada (Single Thread) | Alta (Múltiplos Workers) |
| **Resiliência** | Se o script cair, para tudo | Se um worker cair, a fila persiste |
| **Monitoramento** | Logs em arquivo | Métricas de Fila (Jobs processed/failed) |
| **Manutenção** | Código misturado | Separação clara (Agendamento vs Execução) |

## Próximos Passos (Recomendados)

1.  **Monitoramento de Fila:** Adicionar métricas (Prometheus/Grafana) para monitorar o tamanho da fila e latência de processamento.
2.  **Dead Letter Queue:** Configurar tratamento para tarefas que falham repetidamente (já suportado pelo BullMQ/Redis, verificar implementação no SQLite se necessário).
