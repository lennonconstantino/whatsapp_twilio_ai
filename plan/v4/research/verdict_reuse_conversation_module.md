# Veredito: Reutilização do Módulo Conversation para Memória de IA

**Data:** 29/01/2026
**Contexto:** Decisão sobre a criação de uma nova tabela `ai_chat_history` versus reutilização do módulo existente `src/modules/conversation`.

---

## 1. Análise da Situação Atual

Uma investigação do código fonte revelou a existência de um domínio consolidado de conversação:

*   **Entidade `Message`:** Definida em `src/modules/conversation/models/message.py`. Possui atributos essenciais como `body`, `direction` (INBOUND/OUTBOUND), `message_owner` (USER/SYSTEM/IA), `conv_id` e `timestamp`.
*   **Repositório:** `src/modules/conversation/repositories/message_repository.py` já implementa métodos de busca por conversa, mensagens recentes e mensagens de usuário.
*   **Fluxo de Ingestão:** O `TwilioWebhookMessageHandler` já persiste automaticamente todas as mensagens recebidas (User) e enviadas (System/AI) nesta estrutura.

## 2. Racional

Criar uma tabela paralela `ai_chat_history` traria os seguintes problemas:

1.  **Duplicação de Dados:** Cada interação seria salva duas vezes (uma na tabela `messages` pelo webhook e outra na `ai_chat_history` pelo agente), desperdiçando armazenamento e I/O.
2.  **Inconsistência:** Riscos de desincronia entre o que o usuário vê no WhatsApp e o que o Agente "lembra".
3.  **Complexidade de Manutenção:** Necessidade de manter dois schemas e dois fluxos de persistência sincronizados.
4.  **Violação de DRY (Don't Repeat Yourself):** O conceito de "mensagem de chat" já está modelado e em uso.

Por outro lado, utilizar `src/modules/conversation` como a camada de persistência (Cold Storage) oferece:

1.  **Single Source of Truth:** O histórico da IA reflete exatamente a conversa real.
2.  **Integração Imediata:** As mensagens chegam via Webhook, são salvas, e o Agente pode lê-las imediatamente do banco (ou cache) sem lógica extra de ingestão.
3.  **Simplicidade:** O `MemoryService` da IA foca apenas em *recuperação* inteligente (Redis/Vector) e não em *armazenamento* primário (que fica a cargo do módulo `conversation` e `channels`).

## 3. Veredito

**NÃO criar a tabela `ai_chat_history`.**

A arquitetura de memória deve ser ajustada para:
1.  **Camada de Persistência (L3):** Utilizar o `MessageRepository` existente no módulo `conversation`.
2.  **Camada de Cache (L1/L2):** Implementar Redis cacheando os objetos `Message` existentes.
3.  **Camada Semântica (Vector):** Indexar o conteúdo das entidades `Message` no Vector Store, referenciando o `msg_id` original (ULID).

## 4. Ajuste no Plano de Desenvolvimento

O "Plano C: Arquitetura Híbrida" deve ser modificado:

*   **Fase 2 (Persistência):** Em vez de criar tabelas e workers de persistência de mensagem, o foco será apenas na **integração** com o `MessageRepository`. O Agente não precisa "salvar" a mensagem de input (pois o Webhook já salvou). O Agente precisa apenas garantir que suas **respostas** sejam salvas via `ConversationService` (o que já parece ser o padrão via `TwilioService` e handlers, mas deve ser validado no fluxo do Agente).
*   **Foco Principal:** A implementação se voltará para a camada de **Cache (Redis)** para acelerar a leitura (evitando ir no Postgres a cada turno) e na camada **Vetorial** para recuperação de contexto antigo.
