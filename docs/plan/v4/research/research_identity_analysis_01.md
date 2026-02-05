# Análise do Módulo Identity

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

## 4. Pontos Fortes
*   **Isolamento**: O módulo é independente e não "vaza" lógica interna para outros módulos.
*   **Consistência**: Uso de DTOs para entrada e Models para persistência.
*   **Resiliência**: Implementação de Rollback manual no `IdentityService` para mitigar a falta de transações distribuídas (API REST do Supabase).

## 5. Fraquezas e Riscos
1.  **Ausência de API (Headless)**: Não existe um pacote `api/` dentro do módulo. As operações de criação de usuários e owners não estão expostas via HTTP, tornando o módulo inacessível externamente sem a criação de scripts ou intervenção manual no banco.
2.  **Autenticação vs. Identidade**: O modelo `User` utiliza ULID como ID primário. Se a autenticação for feita via Supabase Auth (que usa UUID), existe uma desconexão ou necessidade de mapeamento entre `auth.users` e `public.users` que não está explícita no código. Se `User` for apenas um perfil local, a autenticação real está "flutuando" fora deste módulo.
3.  **Código "Fantasma"**: A lógica robusta de `register_organization` existe mas não é usada, o que aumenta a dívida técnica (código mantido mas não exercitado).

## 6. Oportunidades e Plano Sugerido

### Oportunidades
*   **API de Onboarding**: Expor `register_organization` através de uma rota segura para permitir auto-cadastro ou cadastro via painel administrativo.
*   **Feature Flags**: O sistema de features já existe (`FeatureService`); pode ser expandido para controlar limites de planos (ex: número máximo de conversas) além de simples on/off.

### Plano de Ação Sugerido

1.  **Criar Camada de API**:
    *   Criar `src/modules/identity/api/` com routers para `owners`, `users` e `auth`.
    *   Expor endpoint `POST /identity/register` conectado ao `register_organization`.
    
2.  **Integração de Autenticação**:
    *   Documentar ou implementar o vínculo entre Supabase Auth (Login) e Identity User (Perfil).
    *   Adicionar campo `auth_id` (UUID) no modelo `User` se necessário para linkar com `auth.users`.

3.  **Testes de Integração**:
    *   Criar testes que exercitem o fluxo `register_organization` para garantir que o rollback manual e a criação em cascata funcionem conforme esperado.

4.  **Limpeza**:
    *   Se o cadastro for permanecer manual, mover a lógica de registro para um script de CLI (`src/scripts/create_tenant.py`) e simplificar o serviço.

---
**Reflexão do Arquiteto**: O módulo é sólido em design mas incompleto em "delivery". Ele é um motor potente sem volante (API). A prioridade deve ser conectá-lo ao mundo externo (API) ou assumir seu papel como biblioteca interna apenas.
