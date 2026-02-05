# Análise de Convergência de Riscos e Plano de Ação

**Data:** 05/02/2026
**Responsável:** Trae AI Architect

Com base na revisão transversal dos relatórios de conformidade dos módulos `Core`, `Conversation`, `AI`, `Twilio` e `Identity`, identificamos **4 pilares críticos de preocupação** que devem nortear o plano de ação imediato. Estas não são apenas melhorias, mas correções estruturais necessárias para garantir a segurança, escalabilidade e operabilidade do sistema.

---

## 🚨 1. Segurança Crítica e Controle de Acesso (Prioridade Máxima)

A maior vulnerabilidade do sistema reside na inconsistência dos padrões de autenticação e autorização, especialmente em módulos sensíveis como `Identity` e `AI`.

*   **O Problema:**
    *   **IDOR (Identity):** O endpoint de cancelamento de assinatura não valida a propriedade do recurso, permitindo ataques destrutivos.
    *   **Auth Fraca:** Coexistência de JWT (seguro) e `X-Auth-ID` (inseguro/spoofable) cria vetores de ataque.
    *   **Vazamento de Dados (AI):** A busca vetorial (RAG) não isola rigidamente os dados por Tenant/Owner, e os logs vazam PII (dados pessoais).
    *   **Safety Settings (AI):** Modelos configurados como `BLOCK_NONE` expõem a aplicação a geração de conteúdo nocivo.

*   **Ação Necessária:**
    1.  **Hardening Imediato:** Aplicar `Depends(get_current_owner_id)` em todas as rotas críticas de `Identity`.
    2.  **Unificação de Auth:** Remover suporte ao header `X-Auth-ID` e padronizar 100% via JWT Bearer Token.
    3.  **Privacidade:** Ativar mascaramento de PII nos logs do módulo de AI e impor filtro de `owner_id` mandatório nas buscas vetoriais.

---

## 🐌 2. Performance e Bloqueio do Event Loop (Risco de Escalabilidade)

Existe um erro arquitetural recorrente na implementação de endpoints assíncronos (`async def`) que invocam repositórios síncronos (`SQLAlchemy` com `psycopg2` ou `requests`), anulando a capacidade de concorrência do FastAPI.

*   **O Problema:**
    *   **Mistura Async/Sync:** Em `Conversation` e `Identity`, controladores `async` executam operações de I/O bloqueante na thread principal do *Event Loop*. Sob carga, isso fará a API parar de responder a novas requisições (Health Checks falharão), mesmo com CPU baixa.
    *   **Redis N+1 (AI):** Inserção de mensagens no cache feita em loop, gerando latência de rede desnecessária.

*   **Ação Necessária:**
    1.  **Correção de Rotas:** Remover a keyword `async` dos controladores que usam repositórios síncronos (permitindo que o FastAPI os execute em *Threadpool*) **OU** migrar os repositórios para `asyncpg`.
    2.  **Otimização de Cache:** Implementar *Bulk Inserts/Pipelines* no Redis.

---

## 🔭 3. Observabilidade e Tratamento de Erros (Operabilidade)

A capacidade de diagnosticar problemas em produção está comprometida pelo tratamento genérico de exceções.

*   **O Problema:**
    *   **Erros Mascarados:** Módulos `Conversation` e `Identity` capturam `Exception` genérico e retornam 500 ou 400 com a mensagem bruta (`str(e)`). Isso dificulta diferenciar erros de cliente (validação) de erros de servidor (infra), além de vazar detalhes internos.
    *   **Lixo Digital:** O módulo `AI` não possui política de retenção para logs de pensamento (`ai_thoughts`), o que degradará a performance do banco de dados ao longo do tempo.

*   **Ação Necessária:**
    1.  **Exception Handlers:** Implementar manipuladores globais que mapeiem exceções de domínio (ex: `SubscriptionNotFound`) para códigos HTTP corretos (404), sem vazar stack traces.
    2.  **Limpeza de Dados:** Criar *Background Worker* para expurgo de logs antigos de IA.

---

## 🧪 4. Confiabilidade e Testes (Qualidade)

Embora a cobertura de testes unitários seja boa em áreas como `Twilio`, há lacunas perigosas na validação de integração.

*   **O Problema:**
    *   **Falta de Testes E2E (Twilio):** A lógica crítica de recebimento de webhooks depende fortemente de mocks, sem validar se a integração real com o banco (constraints, triggers) funciona.
    *   **Complexidade de DI (Core):** O container de injeção de dependência (`container.py`) está se tornando um "God Object", dificultando a manutenção e testes isolados.

*   **Ação Necessária:**
    1.  **Testes de Integração:** Adicionar testes com *Testcontainers* (Postgres) para fluxos críticos de Webhook e Assinatura.
    2.  **Refatoração Modular:** Dividir o `Container` principal em módulos menores (`DbContainer`, `ServiceContainer`).

---

## Resumo do Plano de Ação

| Prioridade | Área | Ação Chave |
| :---: | :--- | :--- |
| 🔥 **P0** | **Segurança** | Corrigir IDOR em `cancel_subscription` e remover `X-Auth-ID`. |
| 🔥 **P0** | **Performance** | Corrigir controladores `async` que bloqueiam o Event Loop. |
| 🚀 **P1** | **Privacidade** | Mascarar PII nos logs de IA e impor filtro de Tenant no Vector DB. |
| 🚀 **P1** | **Qualidade** | Padronizar Exception Handlers (fim dos erros 500 genéricos). |
| 📅 **P2** | **Manutenção** | Implementar limpeza de logs antigos e refatorar DI Container. |
