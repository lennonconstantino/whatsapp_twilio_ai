# Plano de Aumento de Cobertura de Testes Globais

**Data:** 05/02/2026
**Autor:** Assistant
**Status Atual:** 76%
**Meta:** 83%

## 1. Diagnóstico da Cobertura Atual

A análise da execução de testes (`make test`) revelou lacunas significativas, principalmente nas implementações de repositórios PostgreSQL (recentemente adicionados) e em algumas ferramentas de funcionalidades específicas (Finance).

### Principais Ofensores (Baixa Cobertura)

| Arquivo | Linhas | Miss | Cobertura | Impacto |
|---------|--------|------|-----------|---------|
| `src/modules/conversation/repositories/impl/postgres/conversation_repository.py` | 181 | 72 | 60% | **Alto** (Core) |
| `src/modules/conversation/api/v2/conversations.py` | 100 | 46 | 54% | **Alto** (API) |
| `src/modules/channels/twilio/repositories/impl/postgres/account_repository.py` | 57 | 38 | 33% | **Médio** (Infra) |
| `src/modules/conversation/repositories/impl/supabase/message_repository.py` | 56 | 38 | 32% | **Médio** (Core) |
| `src/modules/ai/engines/lchain/feature/finance/tools/query.py` | 212 | 59 | 72% | **Médio** (Feature) |
| `src/modules/ai/engines/lchain/feature/finance/tools/add.py` | 70 | 33 | 53% | **Médio** (Feature) |
| `src/modules/channels/twilio/utils/helpers.py` | 35 | 27 | 23% | **Baixo** (Util) |

## 2. Estratégia de Execução

Para atingir a meta de 83% (ganho de ~7%), focaremos em 4 frentes principais, priorizando componentes Core e Infraestrutura.

### Fase 1: Repositórios Core (Postgres & Supabase)
**Objetivo:** Elevar cobertura dos repositórios de conversação e mensagens.
- **Ação 1.1:** Criar/Estender testes para `PostgresConversationRepository`. Focar em métodos de busca e persistência que diferem da implementação Supabase.
- **Ação 1.2:** Implementar testes unitários para `SupabaseMessageRepository`, cobrindo casos de erro e fluxos alternativos que estão descobertos (32% atual).
- **Ação 1.3:** Adicionar testes para `PostgresAccountRepository` (Twilio), garantindo paridade com a implementação Supabase.

### Fase 2: API de Conversação V2
**Objetivo:** Garantir robustez nos endpoints de listagem e detalhes de conversas.
- **Ação 2.1:** Criar testes de integração para endpoints em `src/modules/conversation/api/v2/conversations.py`.
- **Ação 2.2:** Simular cenários de erro (404, 500) e validação de payloads nos testes da API.

### Fase 3: Funcionalidades de IA (Finance)
**Objetivo:** Cobrir ferramentas complexas de adição e consulta financeira.
- **Ação 3.1:** Criar testes unitários para `FinanceAddTool` (`add.py`), mockando as chamadas de repositório.
- **Ação 3.2:** Reforçar testes de `FinanceQueryTool` (`query.py`), cobrindo os diferentes ramos lógicos de construção de query.

### Fase 4: Utilitários e Helpers
**Objetivo:** "Quick wins" em arquivos pequenos com baixa cobertura.
- **Ação 4.1:** Adicionar testes unitários para `src/modules/channels/twilio/utils/helpers.py`.

## 3. Estimativa de Ganho

| Área | Ganho Estimado (Linhas) | Impacto na % Global |
|------|-------------------------|---------------------|
| Repositórios (Fase 1) | ~120 linhas | +1.6% |
| API V2 (Fase 2) | ~40 linhas | +0.5% |
| Finance Tools (Fase 3) | ~80 linhas | +1.1% |
| Outros (Fase 4 + Dispersos) | ~60 linhas | +0.8% |
| **Total Estimado** | **~300 linhas recuperadas** | **Meta 83% Atingível** |

## 4. Próximos Passos

1.  Aprovar este plano.
2.  Executar Fase 1 (Repositórios).
3.  Executar Fase 2 (API).
4.  Rodar `make test` para aferir progresso.
5.  Executar Fases 3 e 4 se necessário para atingir o target.
