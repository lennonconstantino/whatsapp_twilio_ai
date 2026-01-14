# Plano de Ação - Conformidade Ciclo 05

**Data:** 13 de Janeiro de 2026
**Objetivo:** Resolver gaps de conformidade identificados na análise `conformidade_05.md`, focando em robustez de estados, consistência de dados e recuperação de erros.

---

## 1. Priorização de Encerramento (`close_conversation_with_priority`)

**Problema:** Atualmente, o sistema não arbitra conflitos quando múltiplos eventos tentam fechar uma conversa simultaneamente (ex: timeout vs erro crítico vs ação do usuário).
**Impacto:** Risco de estados inconsistentes ou perda de sinalização de erro crítico.

### Alterações Planejadas:
*   **Arquivo:** [`src/services/conversation_service.py`](src/services/conversation_service.py)
*   **Ação:** Implementar método `close_conversation_with_priority` que respeita a seguinte hierarquia:
    1.  `FAILED` (Máxima prioridade - erros críticos sobrescrevem tudo)
    2.  `USER_CLOSED` (Decisão do usuário prevalece sobre timeouts/agente)
    3.  `SUPPORT_CLOSED` (Escalação prevalece sobre fechamento normal de agente)
    4.  `AGENT_CLOSED`
    5.  `EXPIRED` / `IDLE_TIMEOUT` (Menor prioridade)

## 2. Timers Diferenciados (`PENDING` vs `PROGRESS`)

**Problema:** O sistema usa um único timer de expiração (24h) para todos os estados.
**Impacto:** Conversas `PENDING` (apenas iniciadas) deveriam ter tolerância maior (48h) que conversas em `PROGRESS` (24h), conforme especificação.

### Alterações Planejadas:
*   **Arquivo:** [`src/config/settings.py`](src/config/settings.py)
    *   Adicionar `pending_expiration_minutes` (padrão: 2880 min / 48h).
    *   Renomear/Manter `expiration_minutes` como referência para `progress_expiration_minutes` (padrão: 1440 min / 24h).
*   **Arquivo:** [`src/services/conversation_service.py`](src/services/conversation_service.py)
    *   Ajustar `_create_new_conversation` para usar `pending_expiration_minutes` ao iniciar em `PENDING`.
    *   Atualizar `update_status` ou lógica de transição para redefinir o `expires_at` quando a conversa transicionar para `PROGRESS`.

## 3. Rastreabilidade de Falhas (Recuperação de Contexto)

**Problema:** Quando uma conversa é recriada após um erro (`FAILED`), perde-se o vínculo com o incidente anterior.
**Impacto:** Dificuldade em diagnósticos e suporte ao cliente.

### Alterações Planejadas:
*   **Arquivo:** [`src/services/conversation_service.py`](src/services/conversation_service.py)
    *   Modificar a lógica de criação de nova conversa (`get_active_conversation` / `_create_new_conversation`) para aceitar metadados de origem.
    *   Se a conversa anterior terminou em `FAILED` ou `EXPIRED`, injetar `previous_conversation_id` e `previous_failure_reason` nos metadados da nova conversa.

## 4. Mitigação de Race Conditions (Optimistic Locking)

**Problema:** O método `update_status` busca a conversa e depois atualiza, permitindo que o estado mude nesse intervalo em cenários de alta concorrência.
**Impacto:** Transições inválidas ou perda de atualizações.

### Alterações Planejadas:
*   **Arquivo:** [`src/repositories/conversation_repository.py`](src/repositories/conversation_repository.py)
    *   Alterar `update_status` para utilizar uma abordagem de *Optimistic Concurrency Control*.
    *   Ao executar o update no banco, incluir cláusula `status = current_status` (se possível via cliente Supabase/Postgrest) ou reforçar a verificação.
    *   *Nota:* Devido às limitações de algumas bibliotecas client-side, garantiremos ao menos que a validação seja feita o mais próximo possível da escrita.

---

## Ordem de Execução Sugerida

1.  **Refatoração de Configuração:** Adicionar novos timers em `settings.py`.
2.  **Core Service:** Implementar `close_conversation_with_priority` e lógica de timers.
3.  **Vínculo de Conversas:** Implementar passagem de contexto na recriação.
4.  **Segurança de Concorrência:** Reforçar `conversation_repository.py`.
