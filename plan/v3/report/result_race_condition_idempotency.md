# Relatório de Correção: Race Condition na Idempotência

**Data:** 23/01/2026
**Atividade:** Correção de Race Condition na Idempotência de Webhooks Twilio

## 1. Problema Identificado
Conforme apontado na análise de riscos (`plan/v3/research_04.md`), o sistema possuía uma vulnerabilidade de "Race Condition" no processamento de webhooks. A verificação de idempotência era feita apenas via aplicação (`SELECT` antes do `INSERT`), o que permitia que requisições simultâneas (ex: retries rápidos do Twilio) passassem pela verificação e criassem mensagens duplicadas.

## 2. Solução Implementada
Foi implementada uma estratégia de **Defesa em Profundidade** utilizando o banco de dados como fonte da verdade para unicidade.

### 2.1. Banco de Dados (Constraint)
Criada uma migração SQL para adicionar um índice único na coluna `metadata` (JSONB) especificamente no campo `message_sid`.
- **Arquivo:** `migrations/006_unique_message_sid.sql`
- **Comando:** `CREATE UNIQUE INDEX ... ON messages ((metadata->>'message_sid'));`

### 2.2. Repositório (Tratamento de Exceção)
O `MessageRepository` foi atualizado para detectar violações de unicidade (código de erro Postgres `23505`) e lançar uma exceção de domínio específica `DuplicateError`.
- **Arquivo:** `src/modules/conversation/repositories/message_repository.py`

### 2.3. Serviço de Conversação (Propagação)
O método `add_message` no `ConversationService` foi ajustado para **não** tratar a duplicidade como erro crítico (que causaria o fechamento da conversa como `FAILED`), mas sim propagar a exceção `DuplicateError` para quem chamou.
- **Arquivo:** `src/modules/conversation/services/conversation_service.py`

### 2.4. Webhook Service (Idempotência Robusta)
O `TwilioWebhookService` agora envolve a persistência da mensagem em um bloco `try/except DuplicateError`. Se uma duplicidade for detectada pelo banco:
1. O erro é capturado silenciosamente.
2. Um log informativo é gerado ("Duplicate inbound message caught").
3. O sistema busca a mensagem original para retornar os IDs corretos.
4. Uma resposta de sucesso (`200 OK`) é retornada ao Twilio, garantindo a idempotência.
- **Arquivo:** `src/modules/channels/twilio/services/webhook_service.py`

## 3. Arquivos Alterados
1. `migrations/006_unique_message_sid.sql` (Novo)
2. `src/core/utils/exceptions.py`
3. `src/modules/conversation/repositories/message_repository.py`
4. `src/modules/conversation/services/conversation_service.py`
5. `src/modules/channels/twilio/services/webhook_service.py`

## 4. Próximos Passos
- Executar a migração `migrations/006_unique_message_sid.sql` no ambiente de produção.
- Monitorar os logs por entradas "Duplicate inbound message caught" para validar a eficácia da correção.
