# Relatório de Implementação - Tarefa 3: Vínculo de Conversas

## Resumo das Alterações
Implementamos a rastreabilidade entre conversas (Context Linking) para garantir que, quando uma nova conversa é criada em substituição a uma anterior (seja por expiração, fechamento manual ou falha crítica), o contexto histórico seja preservado nos metadados da nova sessão.

### Componentes Modificados
1. **ConversationService (`get_or_create_conversation`)**:
    *   **Cenário 1 (Ativa Expirada/Fechada):** Ao detectar que a conversa ativa está expirada ou fechada, agora captura explicitamente o `conv_id`, `status` e `ended_at` da conversa antiga antes de criar a nova.
    *   **Cenário 2 (Sem Ativa / Recuperação):** Se não há conversa ativa (retornou `None`), o sistema agora consulta o histórico (`find_all_by_session_key`) para encontrar a última conversa registrada. Isso permite vincular uma nova sessão a uma anterior que tenha falhado (`FAILED`) ou sido encerrada pelo agente.
    *   **Metadados Injetados:**
        *   `previous_conversation_id`: ID da conversa anterior.
        *   `previous_status`: Status final da anterior (ex: `failed`, `expired`, `user_closed`).
        *   `previous_ended_at`: Data de encerramento.
        *   `linked_at`: Timestamp do vínculo.
        *   `recovery_mode`: Flag booleana (`True`) caso a anterior tenha status `FAILED`.

## Validação
- Testes automatizados validaram com sucesso:
    - Vínculo correto ao substituir uma conversa ativa expirada.
    - Recuperação de contexto ao iniciar nova conversa após uma falha crítica (`FAILED`), identificando corretamente o ID anterior e ativando o modo de recuperação.

## Benefícios
- **Suporte:** Facilita a investigação de problemas, permitindo rastrear a cadeia de conversas de um usuário.
- **UX:** Permite que o agente (futuramente) saiba que o usuário vem de uma experiência frustrada (erro) e adapte a abordagem.

## Próximos Passos
- Avançar para a **Tarefa 4**: Mitigação de Race Conditions (Optimistic Locking).
