# Pesquisa e Plano de Melhoria do Módulo Identity (Fase 2)

## 1. Análise do Estado Atual
Com base na verificação do código fonte (`src/modules/identity/`), confirmamos que a **Fase 1** (Fundação Identity) foi parcialmente concluída, mas com desconexões críticas entre a camada de API e a lógica de negócio orquestrada.

### 1.1. O que foi entregue
*   **Estrutura de API**: Routers para `owners`, `users`, `plans` e `subscriptions` estão configurados e expostos.
*   **Modelagem**: `User` possui o campo `auth_id` para vínculo externo. Entidades de Plano e Assinatura existem.
*   **Serviços**: `IdentityService` possui a lógica robusta de `register_organization` (com rollback manual), mas ela **permanece inacessível** via API.

### 1.2. O Problema da "Lógica Órfã"
A API atual expõe `POST /owners` que chama diretamente `OwnerService.create_owner`.
*   **Risco**: Isso cria uma Organização (Owner) sem usuários e sem features iniciais.
*   **Solução Necessária**: O endpoint de cadastro deve utilizar `IdentityService.register_organization`, que garante a criação atômica de:
    1.  Owner (Tenant)
    2.  User Admin (Vinculado ao Owner)
    3.  Features Iniciais (Flags padrão)

### 1.3. Lacunas Identificadas
1.  **Endpoint de Onboarding Ausente**: Não existe uma rota pública (ex: `/register`) que chame a lógica orquestrada.
2.  **Autenticação**: O campo `auth_id` existe no modelo, mas não há middleware ou fluxo claro que garanta que o ID do Supabase Auth seja propagado corretamente durante a criação do usuário.
3.  **Segurança**: As rotas de criação de planos e owners estão abertas, sem validação de permissões (embora a autenticação seja responsabilidade de uma camada superior, a autorização básica por role faz falta).

---

## 2. Plano de Ação (Continuação)

O objetivo desta fase é conectar as pontas soltas, tornando o módulo `Identity` funcional para um fluxo real de cadastro de usuários (SaaS).

### Passo 1: Unificar Fluxo de Onboarding
**Objetivo**: Garantir que todo novo cadastro gere um ambiente completo (Owner + User + Features).

1.  **Criar Endpoint `POST /identity/register`**:
    *   **Input**: `RegisterOrganizationDTO` (Nome da empresa, Dados do usuário admin, ID de Auth externo).
    *   **Processamento**: Chamar `IdentityService.register_organization`.
    *   **Output**: Dados do Owner e do User criado.
2.  **Restringir/Remover `POST /owners`**:
    *   A criação isolada de Owners deve ser desencorajada ou restrita a super-admins.

### Passo 2: Integração com Autenticação
**Objetivo**: Validar o vínculo entre o login externo e o perfil interno.

1.  **Atualizar DTOs**: Garantir que o `RegisterOrganizationDTO` aceite o `auth_id` (vindo do frontend após login no Supabase) e o persista no `User`.
2.  **Endpoint `GET /identity/me`**:
    *   Criar rota que, dado um `auth_id` (ou token decodificado), retorne o perfil do `User` completo (com Owner e Features). Isso é essencial para o frontend carregar o contexto do usuário.

### Passo 3: Refinamento de Assinaturas
**Objetivo**: Garantir que o sistema de planos esteja pronto para uso.

1.  **Seed de Planos**: Criar um script ou migração que popule os planos padrão (ex: Free, Pro) no banco de dados, para que o sistema não inicie vazio.
2.  **Validação**: Garantir que um Owner não possa ter duas assinaturas ativas simultaneamente (já coberto pelo Service, mas verificar testes).

---

## 3. Roteiro de Implementação Sugerido

1.  [ ] **Refatorar API de Owners**:
    *   Implementar `POST /identity/register` em um novo router ou no `owners.py`.
    *   Deprecar a rota de criação simples de owner.
2.  [ ] **Implementar `GET /identity/me`**:
    *   Busca de usuário por `auth_id`.
3.  [ ] **Criar Seed de Planos**:
    *   Script SQL ou Python para inserir planos básicos.
4.  [ ] **Testes de Integração**:
    *   Testar o fluxo completo: Register -> Get Me -> Create Subscription.

## 4. Conclusão
O módulo Identity tem "os ossos e os músculos" (Models e Services), mas falta o "sistema nervoso" (API correta) para coordenar os movimentos. A prioridade máxima é expor o `IdentityService` via API para viabilizar o onboarding real de clientes.
