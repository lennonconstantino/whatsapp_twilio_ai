# Análise de Acoplamento e Coesão dos Módulos Principais

**Data:** 2026-02-03
**Escopo:** Módulos `conversation`, `ai`, `channels/twilio`, `identity`.
**Base:** Análises de conformidade individuais realizadas previamente.

---

## 1. Visão Geral Comparativa

A arquitetura geral do projeto segue um modelo modular com camadas bem definidas (API, Services, Repositories), facilitado pelo uso de Injeção de Dependência (DI Container). No entanto, observam-se variações significativas na maturidade de acoplamento e coesão entre os módulos.

| Módulo | Coesão | Acoplamento | Nível de Conformidade (Ref.) |
| :--- | :--- | :--- | :--- |
| **Conversation** | **Média/Alta** (na V2) | **Médio** | ~70% (Parcial) |
| **AI** | **Média** | **Médio/Alto** | ~75% (Parcial) |
| **Channels (Twilio)** | **Média** | **Alto** | ~80% (Parcial) |
| **Identity** | **Média** | **Médio** | ~65% (Parcial) |

---

## 2. Análise Detalhada por Módulo

### 2.1. Módulo `conversation`

#### Coesão (Responsabilidade Única e Agrupamento)
*   **Nível:** **Média/Alta** (V2), **Baixa** (Legacy V1).
*   **Pontos Fortes:**
    *   A refatoração para V2 introduziu componentes especializados (`ConversationFinder`, `Lifecycle`, `Closer`), removendo a lógica "god class" do serviço antigo.
    *   Separação clara entre definição de dados (Models/DTOs) e comportamento.
*   **Pontos Fracos:**
    *   **Vazamento de Regras:** A máquina de estados (transições válidas) está duplicada entre o `Lifecycle` (domínio) e o `Repository` (persistência), violando a fonte única de verdade.
    *   **Infra no Domínio:** Componentes de domínio (`Lifecycle`) conhecem detalhes de infraestrutura (tabelas do Supabase) para gravar histórico, misturando responsabilidades.

#### Acoplamento (Dependências e Interações)
*   **Nível:** **Médio**.
*   **Pontos Fortes:**
    *   Uso de Interfaces/Protocolos para repositórios permite mocking e inversão de controle.
*   **Pontos de Atenção:**
    *   **Acoplamento Temporal/Lógico:** A V1 e V2 compartilham a mesma base de dados e repositórios, mas expõem contratos diferentes. Mudanças na V2 podem quebrar a V1 silenciosamente.
    *   **Dependência de Infra:** O módulo é fortemente acoplado ao `SupabaseRepository` e suas idiossincrasias (query builder), dificultando a troca de backend se necessário.

---

### 2.2. Módulo `ai`

#### Coesão
*   **Nível:** **Média**.
*   **Pontos Fortes:**
    *   Separação clara entre o "Core" (infraestrutura de agentes, tools genéricas) e "Features" (regras de negócio específicas como Finance, Relationships).
    *   Conceito de Memória Híbrida (L1/L2/L3) bem encapsulado no `HybridMemoryService`.
*   **Pontos Fracos:**
    *   **Contratos Frágeis:** Inconsistência na implementação de `Tools` entre features (algumas retornam objetos estruturados, outras strings), exigindo conhecimento interno por parte do chamador.
    *   **Side Effects na Inicialização:** O arquivo `llm.py` realiza inicialização eager de modelos e carrega variáveis de ambiente no import, o que é uma baixa coesão temporal (mistura definição com execução).

#### Acoplamento
*   **Nível:** **Médio/Alto**.
*   **Pontos Fortes:**
    *   Uso de filas (`QueueService`) para desacoplar o processamento pesado do ciclo de vida da requisição HTTP.
*   **Pontos de Atenção:**
    *   **Dependência Cruzada:** Features de IA (ex: Finance) acessam repositórios de outros módulos ou tabelas diretamente, criando um acoplamento implícito com o esquema de dados de outros domínios.
    *   **Dependência de Infra:** Alto acoplamento com provedores específicos (OpenAI, Twilio) e Supabase (pgvector), vazando detalhes de implementação para as camadas superiores.

---

### 2.3. Módulo `channels/twilio`

#### Coesão
*   **Nível:** **Média**.
*   **Pontos Fortes:**
    *   Atua corretamente como uma *Anti-Corruption Layer* (ACL), traduzindo payloads externos (Twilio) para comandos internos.
    *   Orquestração centralizada no `TwilioWebhookService`.
*   **Pontos Fracos:**
    *   **Duplicação Conceitual:** Endpoints de `inbound` e `outbound` realizam fluxos quase idênticos, sugerindo baixa coesão funcional (deveriam ser unificados ou melhor segregados).
    *   **Mistura de Níveis:** O serviço de webhook lida tanto com a validação HTTP (assinatura) quanto com regras de negócio complexas (resolução de owner, despacho para fila), sobrecarregando a classe.

#### Acoplamento
*   **Nível:** **Alto**.
*   **Motivo:** Por natureza, este módulo é um "Hub" de integração.
*   **Pontos de Atenção:**
    *   **Dependência de Múltiplos Contextos:** O caminho crítico do webhook depende de `ConversationService` (criar/buscar conversa), `IdentityService` (resolver owner/plano) e `QueueService` (IA). Falhas em qualquer um desses módulos impactam a recepção de mensagens.
    *   **Acoplamento Síncrono:** A resolução de `Owner` ocorre de forma síncrona dentro do processamento do webhook, acoplando a disponibilidade do banco de dados `Identity` à latência do webhook Twilio.

---

### 2.4. Módulo `identity`

#### Coesão
*   **Nível:** **Média**.
*   **Pontos Fortes:**
    *   Separação clara por agregados (Owner, User, Plan, Subscription).
    *   Modelagem de domínio rica (Features, Overrides) encapsulada em serviços específicos.
*   **Pontos Fracos:**
    *   **Vazamento de Limites:** `IdentityService` acessa diretamente repositórios de outros sub-domínios (ex: `PlanRepository`), pulando a camada de serviço correspondente.
    *   **Inconsistência de Modelos:** DTOs e Models de banco muitas vezes divergem ou se duplicam (ex: `models/response.py`), gerando confusão sobre qual é a representação canônica dos dados.

#### Acoplamento
*   **Nível:** **Médio**.
*   **Pontos Fortes:**
    *   Interfaces bem definidas e uso extensivo de injeção de dependência.
*   **Pontos de Atenção:**
    *   **Acoplamento de Dados:** Dependência direta do cliente Supabase nos repositórios, dificultando migrações futuras.
    *   **Dependência de "Magic Strings":** Autenticação baseada em headers (`X-Auth-ID`) sem um contrato forte ou validação centralizada cria um acoplamento frágil com o gateway/frontend.

---

## 3. Síntese e Riscos Arquiteturais

1.  **Vazamento de Infraestrutura (Supabase):** Todos os módulos apresentam acoplamento médio/alto com o `SupabaseRepository` e o cliente `PostgREST`. Embora prático, isso torna a lógica de negócio dependente de estruturas de dados relacionais e dificulta testes unitários puros.
2.  **Fronteiras de Módulo Permeáveis:** Há casos de serviços de um módulo acessando repositórios de outro (ex: `Identity` acessando `PlanRepo`, `Twilio` acessando `ConversationService`). O ideal seria comunicação apenas via Interfaces de Serviço (Public API do módulo).
3.  **Gestão de Estado Distribuída:** O estado da conversa é manipulado pelo `Conversation`, mas também influenciado pelo `AI` e `Twilio`, criando um acoplamento implícito onde mudanças em um módulo podem deixar o estado inconsistente em outro.

## 4. Recomendações de Melhoria

1.  **Reforçar Fronteiras (Boundaries):**
    *   Impor regra de arquitetura: Um módulo só pode acessar outro via sua **Service Interface**, nunca via Repository ou acesso direto a tabelas.
    *   Utilizar DTOs agnósticos para comunicação entre módulos, evitando passar objetos ORM/DB.

2.  **Inversão de Dependência em Infra:**
    *   Para módulos críticos (`conversation`, `ai`), abstrair completamente a persistência atrás de interfaces que não vazem detalhes do Supabase (ex: evitar retornar `postgrest.APIResponse` para a camada de serviço).

3.  **Padronização de Contratos (AI/Tools):**
    *   Definir uma interface rígida para `Tools` e `Agents` no módulo de IA para garantir que todas as Features se comportem de maneira previsível (alto coesão).

4.  **Desacoplamento de Webhook (Twilio):**
    *   Mover a resolução de `Owner` e outras lógicas de negócio para o processamento assíncrono (Worker), deixando o Webhook apenas como um "recebedor cego" que enfileira o payload bruto. Isso reduz drasticamente o acoplamento temporal e aumenta a resiliência.
