# Contexto da Conversa: Migração e Refatoração de Repositórios (Supabase vs Postgres)

## 1. Objetivo Principal
Validar e garantir a paridade funcional entre as implementações de repositórios do Supabase (legado/padrão) e Postgres (novo backend), visando um chaveamento seguro do banco de dados.

## 2. Diagnóstico Inicial
- **Duplicação de Código**: Os repositórios foram duplicados para suportar o backend Postgres puro.
- **Inconsistências Encontradas**:
    - `PostgresConversationRepository` faltava implementação de métodos críticos de ciclo de vida (`find_expired_candidates`, `cleanup_expired_conversations`, etc.) que existiam no Supabase.
    - `PostgresMessageRepository` faltava o método `count_by_conversation`.
    - Diferenças nos construtores (`__init__`) foram analisadas e consideradas corretas devido às estratégias diferentes das classes base.

## 3. Ações Corretivas
- **Implementação de Métodos Faltantes**: Todos os métodos ausentes nos repositórios Postgres foram implementados utilizando SQL puro (`psycopg2`), garantindo paridade com a lógica do Supabase.

## 4. Refatoração Arquitetural (Clean Architecture)
Para resolver a complexidade de gestão de dependências e garantir contratos firmes, foi adotada uma abordagem baseada em interfaces:

- **Interfaces (ABCs)**: Criadas na raiz do módulo `conversation/repositories/` para definir o contrato obrigatório.
    - `ConversationRepository` (ABC)
    - `MessageRepository` (ABC)
- **Segregação de Implementações**:
    - **Supabase**: Movido para `impl/supabase/`, renomeado para `SupabaseConversationRepository` e `SupabaseMessageRepository`.
    - **Postgres**: Mantido em `impl/postgres/`, classes `PostgresConversationRepository` e `PostgresMessageRepository`.
- **Herança**: Ambas as implementações agora herdam explicitamente de suas respectivas ABCs, garantindo que qualquer desvio de contrato gere erro em tempo de desenvolvimento.

## 5. Injeção de Dependência
- O container `src/core/di/container.py` foi atualizado para utilizar o padrão `Selector`.
- A escolha da implementação concreta é feita dinamicamente baseada na configuração `settings.database.backend`.

## 6. Status Atual
- Container DI validado e funcional.
- Repositórios padronizados e desacoplados.
- Risco de incompatibilidade mitigado através da imposição de interfaces.

---
*Gerado automaticamente para contexto de janela de análise.*
