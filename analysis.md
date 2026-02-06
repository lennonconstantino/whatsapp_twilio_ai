# Análise Consolidada de Prioridades e Plano de Ação

**Data:** 06/02/2026
**Responsável:** Trae AI Assistant
**Base:** Análises de Conformidade (Core, Conversation, AI, Twilio, Identity) e Coesão/Acoplamento v1.0.

---

## 1. Visão Geral das Preocupações Críticas

Após a análise cruzada de todos os módulos, identificamos 3 áreas macro que exigem atenção imediata. A priorização foca em **Segurança** (Risco de Negócio), **Performance** (Escalabilidade) e **Manutenibilidade** (Dívida Técnica).

| Rank | Área | Problema Principal | Módulos Afetados | Nível de Risco |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Segurança** | **IDOR & SQL Injection Manual:** Falhas de validação de propriedade e parsing manual de SQL. | `Billing`, `AI` | 🔴 **Crítico** |
| **2** | **Performance** | **Gargalo Síncrono (Blocking I/O):** Módulos Core operando de forma bloqueante em ambiente Async. | `Identity`, `Twilio` | 🔴 **Crítico** |
| **3** | **Arquitetura** | **God Objects & Acoplamento:** Classes gigantes e Containers de DI centralizados. | `Core`, `AI` | 🟡 **Alto** |

---

## 2. Detalhamento das Preocupações e Planos de Ação

### Prioridade 1: Segurança (Hardening Imediato)

**Diagnóstico:**
*   **Billing:** Endpoints de assinatura expõem objetos sem validar se o `owner_id` da requisição corresponde ao dono do recurso (IDOR).
*   **AI:** O arquivo `query.py` implementa um parser SQL manual baseada em Regex/String manipulation, o que é frágil e propenso a injeção ou erros lógicos.

**Plano de Ação:**
1.  **[Billing] Implementar Middleware/Dependency de Validação de Propriedade:**
    *   Garantir que todo acesso a recursos (`Subscription`, `Plan`) valide `resource.owner_id == current_user.id`.
2.  **[AI] Substituir Parser Manual por Query Builder Seguro:**
    *   Refatorar `query.py` para utilizar `SQLAlchemy Core` ou `Pypika` para construção de queries dinâmicas, eliminando a manipulação direta de strings.
3.  **[Identity] Revisão de Logs:**
    *   Auditar logs de erro para garantir que dados sensíveis (PII) não vazem em exceções não tratadas.

### Prioridade 2: Migração para Full Async (Performance)

**Diagnóstico:**
*   **Identity:** Implementado com funções síncronas (`def`). Quando consumido pelo módulo `Twilio` (que é Async), obriga o uso de `run_in_threadpool`. Sob carga alta, isso esgota o pool de threads e trava o Event Loop.
*   **Core:** Uso do `SupabaseRepository` via REST adiciona latência HTTP desnecessária comparado a uma conexão TCP persistente (SQL/AsyncPG).

**Plano de Ação:**
1.  **[Identity] Converter Repositórios e Serviços para Async:**
    *   Alterar assinaturas para `async def`.
    *   Migrar driver de banco para `asyncpg` ou cliente Supabase Async.
2.  **[Twilio] Remover `run_in_threadpool`:**
    *   Após a migração do Identity, atualizar chamadas no `TwilioWebhookService` para `await identity_service.get_...`.
3.  **[Core] Padronizar PostgresRepository Async:**
    *   Priorizar o uso do `PostgresRepository` (SQL) em detrimento do REST para operações críticas de performance.

### Prioridade 3: Desacoplamento e Refatoração (Manutenibilidade)

**Diagnóstico:**
*   **Core DI (`container.py`):** Atua como um "God Object", conhecendo e instanciando todos os serviços de todos os módulos. Isso viola os limites dos módulos e dificulta testes isolados.
*   **AI God Classes:** `query.py` (500+ linhas) e `agent.py` misturam responsabilidades de validação, parsing, orquestração e lógica de negócio.

**Plano de Ação:**
1.  **[Core] Modularizar Injeção de Dependência:**
    *   Quebrar o `Container` principal em containers menores (`IdentityContainer`, `BillingContainer`, etc.).
    *   O Container Principal deve apenas compor os sub-containers, sem definir providers diretamente.
2.  **[AI] Decompor `query.py`:**
    *   Extrair classes menores: `SQLValidator`, `QueryBuilder`, `SchemaParser`.

---

## 3. Roteiro de Execução Sugerido

Recomenda-se a execução em **Sprints Semanais** focados:

*   **Semana 1 (Segurança):** Correção de IDOR no Billing e Refatoração do Parser SQL no AI.
*   **Semana 2 (Performance):** Migração do Módulo Identity para Async.
*   **Semana 3 (Arquitetura):** Refatoração do Container de DI e Limpeza de Código no AI.

---

## 4. Métricas de Sucesso

*   **Segurança:** Zero vulnerabilidades críticas de IDOR detectadas em scan.
*   **Performance:** Redução de latência média (p95) no webhook do Twilio em 30% após migração Async.
*   **Código:** Redução da Complexidade Ciclomática média do módulo AI em 20%.
