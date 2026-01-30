# Registro de Correções e Melhorias (v4)

**Data:** 30/01/2026
**Versão:** 4.0
**Status:** Consolidado

Este documento registra as correções técnicas, refatorações e melhorias de estabilidade implementadas na versão 4.0 do projeto, além de manter o histórico da versão anterior.

---

## 🚀 Ciclo de Estabilização v4 (Janeiro/2026)

Foco principal: Estabilização da suíte de testes (`make test`), robustez da injeção de dependência e correções de infraestrutura (banco de dados e filas).

### 1. Arquitetura e Injeção de Dependência (DI)
*   **Quebra de Ciclos de Importação**: Resolvido ciclo entre `relationships_agent` e `prompts/__init__.py` que impedia a inicialização da aplicação.
*   **Factory de Agentes**: Refatoração do `TwilioWebhookService` para injetar `AgentFactory` em vez de uma instância fixa de `RoutingAgent`, permitindo seleção dinâmica de agentes por feature (Multi-tenant).
*   **Singleton de Transcrição**: `TranscriptionService` (Whisper) configurado como Singleton no container DI para evitar recarga custosa do modelo a cada requisição. Tornou-se uma dependência opcional no Webhook para facilitar testes.

### 2. Módulo Conversation (Migração V2)
*   **Arquitetura de Componentes**: Validação e estabilização da arquitetura V2 (Facade), delegando responsabilidades para `Lifecycle`, `Finder` e `Closer`.
*   **Correção Massiva de Testes**: Atualização de dezenas de testes unitários que quebravam devido a mocks desatualizados e novas assinaturas de métodos (ex: `update_status` vs `update`).
*   **Locking Otimista**: Implementação e correção de testes para controle de concorrência (`current_version`) nas transições de estado.
*   **Schema**: Ajuste para ignorar inserção da coluna gerada `session_key` (`exclude_on_create`) e suporte a campos calculados no Repositório Base.

### 3. Infraestrutura e Segurança
*   **Correção PostgREST (JSONB)**: Solução para erro 400 em queries de filtro `.contains()` no Supabase, forçando serialização manual de JSON (`json.dumps`).
*   **Migrações Idempotentes**: Refatoração do script `000_drop_schema.sql` para usar `CASCADE` e ordem inversa de dependência, corrigindo falhas de "Duplicate Table" no `make migrate`.
*   **Atomicidade no Identity**: Correção de testes de atomicidade no registro de organizações, atualizando mocks para incluir `SubscriptionService` e `PlanService`.
*   **Vector Store**: Automação da migração SQL para habilitar a extensão `vector` e criar tabela `message_embeddings`, corrigindo erros no worker de embeddings.

### 4. Módulo Twilio e Mídia
*   **Download Seguro de Mídia**: Refatoração completa de `TwilioHelpers` para usar `settings` (segurança), detectar extensões via `mimetypes` e salvar em diretório isolado `downloads/`.
*   **Correção de Argumentos**: Fix de bug de ordem de argumentos (`url, type` invertidos) que impedia downloads.
*   **Webhook ACK**: Ajuste na mensagem de resposta do webhook para "Processing started", alinhando contrato de teste com a natureza assíncrona do sistema.
*   **Correção de Testes de Webhook**: Refatoração de testes monolíticos para testes de componentes (`test_owner_resolver`, `test_message_handler`), atingindo 100% de sucesso.

### 5. AI e Contexto
*   **Correção de Contexto (Feature ID)**: Inclusão do `feature_id` no `AgentContext` para permitir persistência correta de pensamentos (`AILogThoughtService`) e correlação com features ativas.
*   **Logging Estruturado**: Resolução de conflito de argumentos (`TypeError`) no `structlog` ao renomear o argumento `event` para `event_type`.

---

## 📜 Histórico: Correções da v3 (Legado)

*Registro mantido para rastreabilidade.*

### 1. Atomicidade no Identity Module
- **Problema**: O registro de organizações (`register_organization`) não era atômico. Falhas na criação do usuário admin deixavam a organização "órfã".
- **Correção**: Implementado **Padrão de Compensação (Manual Rollback)**. Deleção física (Hard Delete) do Owner caso a criação do usuário falhe.
- **Status**: ✅ Resolvido.

### 2. Unificação de Background Tasks
- **Problema**: Dualidade no processamento (QueueService vs Script legado com `while True`).
- **Correção**: Unificação total via **QueueService** e **Scheduler Leve**.
- **Status**: ✅ Resolvido. Escalabilidade horizontal habilitada.

### 3. Race Condition na Idempotência (Webhooks)
- **Problema**: Lógica "Check-Then-Act" vulnerável a concorrência.
- **Correção**: Adoção de **"Insert-Then-Catch"** com índice único no banco (`message_sid`). O banco tornou-se a fonte de verdade.
- **Status**: ✅ Resolvido.

### 4. Tipagem Estrita em Serviços
- **Problema**: Retornos de dicionários genéricos (`Dict[str, Any]`) propensos a erros.
- **Correção**: Adoção de **Pydantic Models** (ex: `TwilioMessageResult`) para retornos de serviço.
- **Status**: ✅ Resolvido.

### 5. Resiliência em AI Workers
- **Problema**: Falhas silenciosas em workers de IA.
- **Correção**: Mecanismo de **Fallback** (mensagem de erro amigável ao usuário) e flag de erro no histórico.
- **Status**: ✅ Resolvido.
