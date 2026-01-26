# Análise do Módulo Identity e Alinhamento Arquitetural

## 1. Visão Geral
O módulo `src/modules/identity/` é responsável pelo gerenciamento de entidades principais do sistema multi-tenant: `Owner` (Organização/Tenant), `User` (Usuários do sistema) e `Feature` (Flags de funcionalidade). Ele segue uma arquitetura em camadas (Models, Repositories, Services, DTOs) e utiliza `IdentityService` como fachada orquestradora.

## 2. Estrutura Interna
O módulo está bem estruturado, seguindo os padrões do projeto:
*   **Models**: Utilizam Pydantic com validação de ULID (`src/core/utils/custom_ulid`).
*   **Repositories**: Herdam de `SupabaseRepository`, garantindo consistência no acesso a dados.
*   **Services**:
    *   `OwnerService`, `UserService`, `FeatureService`: Serviços de domínio focados.
    *   `IdentityService`: Serviço de aplicação que orquestra a criação complexa (ex: `register_organization` que cria Owner + Admin + Features atomicamente com rollback manual).

## 3. Conexões e Dependências
*   **Injeção de Dependência**: O módulo é totalmente integrado via `src/core/di/container.py`.
*   **Acoplamento**:
    *   `TwilioWebhookService` depende de `IdentityService`, provavelmente para validação de features ou contexto de usuário.
    *   Outros módulos (ex: `Conversation`, `Queue`) referenciam `owner_id` apenas como string (ULID), mantendo um baixo acoplamento (Loose Coupling).
*   **Uso Identificado**:
    *   A função `register_organization` no `IdentityService` **não possui chamadas no código fonte rastreado** (ex: não há rotas de API expostas para cadastro). Isso indica que o onboarding é feito manualmente ou é código morto/futuro.

## 4. Alinhamento Arquitetural (Diagrama vs. Código)

Baseado na visão arquitetural proposta, identificamos os seguintes pontos de convergência e divergência:

### 4.1. Convergências (O que já existe)
*   **Identity como Fundação**: O diagrama reforça `Identity` como módulo central (`Channels Uses Identity`), o que já é refletido no código via injeção de dependência (`TwilioWebhookService` -> `IdentityService`).
*   **Authentication Externa**: O diagrama separa `Authentication` de `Identity`. No código atual, `Identity` não lida com login (senhas/tokens), apenas perfis (`User`), validando essa separação. A autenticação (provavelmente Supabase Auth) deve ser a porta de entrada que resolve o `user_id` para o `Identity`.
*   **Conversation Behavior**: O fluxo `Channels -> Conversation` existe e é robusto.

### 4.2. Divergências e Lacunas (O que falta)
*   **Plans (Planos)**: O diagrama menciona explicitamente `Plans` no módulo Identity. **Não existe código para "Plans", "Subscriptions" ou "Quotas"** no módulo atual. Existe apenas `Features`, que são flags binárias (enable/disable).
*   **Materialized View (Conversations+Results)**: O diagrama propõe uma visão materializada para analíticos. Não existe tal view no banco ou definições no código (`migrations/`). Existe apenas uma tabela `conversation_state_history` para auditoria básica.
*   **API de Onboarding**: A seta `Authentication -> Identity` implica que após o login/registro, o `Identity` é consultado ou populado. Sem uma API (`api/` no módulo Identity), esse fluxo está quebrado ou é puramente manual (banco de dados).

## 5. Pontos Fortes
*   **Isolamento**: O módulo é independente e não "vaza" lógica interna para outros módulos.
*   **Consistência**: Uso de DTOs para entrada e Models para persistência.
*   **Resiliência**: Implementação de Rollback manual no `IdentityService` para mitigar a falta de transações distribuídas.

## 6. Fraquezas e Riscos
1.  **Ausência de API (Headless)**: Não existe um pacote `api/` dentro do módulo.
2.  **Autenticação vs. Identidade**: Desconexão entre o `auth.users` (Supabase) e `public.users` (Identity).
3.  **Código "Fantasma"**: Lógica de `register_organization` robusta mas não utilizada.

## 7. Plano de Ação Sugerido

### Fase 1: Fundação Identity (Imediato)
1.  **Criar Camada de API**: Implementar `src/modules/identity/api/` expondo endpoints para gestão de Owners e Users.
2.  **Modelagem de Planos**: Criar entidade `Plan` e `Subscription` no módulo Identity para suportar limites (ex: mensagens/mês) conforme o diagrama.

### Fase 2: Integração e Analytics
3.  **Link Auth-Identity**: Adicionar campo `auth_id` em `User` para mapeamento direto com Supabase Auth.
4.  **Materialized View**: Criar migração para `view_conversation_analytics` unindo `conversations`, `messages` e `ai_results` para alimentar o dashboard proposto.

---
**Reflexão do Arquiteto**: O diagrama é um excelente guia de evolução. Ele revela que o módulo Identity precisa crescer de um simples "dicionário de usuários" para um "motor de assinaturas e permissões" (Plans + Features). A ausência da Materialized View também explica a dificuldade atual em gerar relatórios consolidados.
