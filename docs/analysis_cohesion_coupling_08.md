# Análise de Acoplamento e Coesão (v0.8)

**Data:** 05/02/2026
**Responsável:** Trae AI (Agent Architecture)
**Contexto:** Análise pós-refatoração de Logs/Exceptions em Billing e investigação de sobreposição Identity/Billing.

---

## 1. Sumário Executivo: O Problema do "Split Brain"

A versão 0.8 traz uma descoberta crítica que supera os problemas de acoplamento anteriores: o sistema sofre de **"Split Brain" (Cérebro Dividido)** entre os módulos `Identity` e `Billing`.

Enquanto a arquitetura evoluiu para criar um módulo `Billing` robusto (com controle de quotas, eventos e logs estruturados), o módulo `Identity` manteve uma implementação legada e simplificada de Planos e Assinaturas. O fluxo crítico de registro de organizações (`IdentityService.register_organization`) utiliza a versão legada interna, **ignorando completamente o módulo de Billing**.

**Consequência Imediata:** Novas organizações são criadas sem a inicialização correta de quotas (`FeatureUsage`), tornando o controle de limites inoperante para novos usuários.

---

## 2. Análise Detalhada por Módulo

### 2.1. Core (`src/core`)
*   **Coesão:** 🟢 **Muito Alta**
    *   Mantém-se como referência. A separação de configurações, interfaces de banco e utilitários é clara.
*   **Acoplamento:** 🟢 **Baixo**
    *   Atua como provedor de serviços transversais (Logger, DI Container Base, Exceptions) sem depender de módulos de negócio.
*   **Evolução v0.8:** Estável.

### 2.2. Identity (`src/modules/identity`)
*   **Coesão:** 🔴 **Baixa (Degradada)**
    *   **Diagnóstico:** O módulo sofre de crise de identidade. Além de gerenciar Autenticação e Usuários (seu core), ele mantém uma gestão paralela e anêmica de Planos e Assinaturas.
    *   **Evidência:** Presença de `services/subscription_service.py` e `models/plan.py` duplicados em relação ao módulo `billing`.
*   **Acoplamento:** 🟡 **Médio (Enganoso)**
    *   Parece desacoplado de `Billing` apenas porque **reimplementa** a lógica internamente em vez de consumir o módulo correto. Esse é o pior tipo de desacoplamento (isolamento por duplicação).
*   **Ação Crítica:** Remover toda lógica de planos/assinaturas e delegar para o módulo `Billing`.

### 2.3. Billing (`src/modules/billing`)
*   **Coesão:** 🟢 **Muito Alta (Melhorada)**
    *   **Melhoria v0.8:** A introdução de exceções de domínio (`BillingRepositoryError`, `SubscriptionNotFoundError`) e logs estruturados nos repositórios blindou o módulo. Ele agora é autossuficiente e robusto.
*   **Acoplamento:** 🟢 **Baixo (Isolado)**
    *   O módulo é bem desenhado e independente, mas atualmente está "órfão" no fluxo principal de cadastro. Ele está pronto para ser usado, mas não é chamado.
*   **Status:** ✅ Pronto para assumir a responsabilidade total.

### 2.4. Channels / Twilio (`src/modules/channels/twilio`)
*   **Coesão:** 🟡 **Média**
    *   Responsabilidades bem definidas internamente (Webhook -> Fila -> Handler).
*   **Acoplamento:** 🔴 **Crítico**
    *   **Cadeia de Dependência:** `MessageHandler` -> `AIProcessor` -> `IdentityService`.
    *   **Risco:** O `AIProcessor` toma decisões de roteamento baseadas nas "Features Ativas" consultadas no `IdentityService`. Como o Identity usa dados legados/incompletos de assinatura, o Twilio pode rotear mensagens incorretamente (ex: permitir uso de IA para quem não tem quota, pois a quota nem foi inicializada).

### 2.5. AI (`src/modules/ai`)
*   **Coesão:** 🟡 **Média**
    *   Agrupa agentes, memória e ferramentas. A estrutura interna é complexa mas necessária.
*   **Acoplamento:** 🔴 **Alto**
    *   Depende fortemente de `Identity` para preferências e contexto do usuário. Sofre do mesmo risco do Twilio: se o Identity informar dados inconsistentes, a IA opera com contexto falho.
*   **Segurança:** Filtros de memória L3 (`owner_id`) mitigam vazamento de dados, ponto positivo mantido.

### 2.6. Conversation (`src/modules/conversation`)
*   **Coesão:** 🟢 **Alta**
    *   Focada puramente no ciclo de vida da conversa.
*   **Acoplamento:** 🟢 **Baixo**
    *   Dependências mínimas.
*   **Risco Técnico:** Persiste o uso de I/O síncrono (`psycopg2`) em rotas assíncronas, um gargalo de performance latente.

---

## 3. Matriz de Acoplamento vs. Coesão (v0.8)

| Módulo | Coesão | Acoplamento | Tendência | Observação |
| :--- | :---: | :---: | :---: | :--- |
| **Billing** | ⭐ Alta | Baixo | ⬆️ Melhorou | Log/Exceptions robustos. Pronto para produção. |
| **Core** | Alta | Baixo | ➡️ Estável | Fundação sólida. |
| **Conversation** | Alta | Baixo | ➡️ Estável | Risco de performance (Sync I/O). |
| **Identity** | 🔴 Baixa | Médio | ⬇️ Piorou | **Split Brain**. Duplicação de lógica de negócio. |
| **Twilio** | Média | 🔴 Crítico | ➡️ Estável | Depende de dados inconsistentes do Identity. |
| **AI** | Média | Alto | ➡️ Estável | Depende de dados inconsistentes do Identity. |

---

## 4. Plano de Convergência Arquitetural

Para resolver o estado de "Split Brain" e elevar a nota do sistema para produção, as seguintes ações são mandatórias:

### Fase 1: Unificação da Verdade (Imediato)
1.  **Identity "Magro":**
    *   Remover `models/plan.py`, `models/subscription.py`, `models/feature.py` de `src/modules/identity`.
    *   Remover `services/plan_service.py`, `services/subscription_service.py`, `services/feature_service.py` de `src/modules/identity`.
2.  **Ponte Identity -> Billing:**
    *   No `IdentityService.register_organization`, injetar e utilizar `BillingService.create_subscription`.
    *   Garantir que a criação da organização seja atômica com a criação da assinatura (Unit of Work ou Saga simples).

### Fase 2: Saneamento de Dependências
1.  **Twilio & AI:**
    *   Atualizar `AIProcessor` (Twilio) e Agentes (AI) para consultarem quotas e permissões através do módulo `Billing` (ou uma fachada de "Policy"), e não mais via `Identity`. O `Identity` deve servir apenas para *Quem é você?*, e o `Billing` para *O que você pode fazer?*.

### Fase 3: Performance
1.  **Migração Async:** Iniciar migração gradual dos repositórios de `Conversation` e `Twilio` para `SQLAlchemy Async` ou `asyncpg` direto, resolvendo o gargalo de I/O.

---

**Conclusão:** O sistema possui componentes individuais excelentes (especialmente o novo Billing e o Core), mas a integração entre eles está quebrada na camada de Identidade. A correção dessa duplicação é o passo mais importante para a estabilidade da plataforma.
