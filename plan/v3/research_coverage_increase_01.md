# Análise e Plano de Aumento de Cobertura de Testes

## 1. Contexto e Objetivo

A cobertura atual de testes do projeto é de **52%**, com o objetivo de elevar para **90%**. A análise identificou áreas críticas com baixa cobertura que representam risco para a estabilidade e manutenibilidade do sistema.

## 2. Diagnóstico de Cobertura

As seguintes áreas foram identificadas como prioritárias devido à sua criticidade e baixa cobertura:

| Componente | Cobertura Atual | Criticidade | Risco |
| :--- | :--- | :--- | :--- |
| `src/modules/ai/engines/lchain/core/agents/agent.py` | 13% | Alta | Falhas na lógica do agente podem quebrar todo o fluxo de IA. |
| `src/core/database/base_repository.py` | 32% | Alta | Base de todas as operações de banco; bugs aqui afetam tudo. |
| `src/modules/channels/twilio/services/twilio_service.py` | 24% | Média/Alta | Integração externa; falhas impedem comunicação com usuários. |
| `src/modules/conversation/repositories/conversation_repository.py` | 27% | Alta | Gerenciamento de estado complexo; risco de inconsistência de dados. |
| `src/modules/ai/engines/lchain/feature/finance/tools/query.py` | 37% | Média | Lógica complexa de ferramentas; erros geram respostas incorretas. |

## 3. Estratégia de Testes

Seguiremos os princípios de simplicidade e uso do stack atual (`pytest`, `unittest.mock`), evitando a introdução de novas ferramentas complexas.

### 3.1. Abordagem
*   **Unit Tests (Isolados)**: Foco na lógica de negócios e fluxos de controle. Uso extensivo de `Mock` para isolar dependências (DB, APIs externas).
*   **Integration Tests (Simulados)**: Testar a integração entre componentes usando mocks controlados para serviços externos (Supabase, Twilio).

### 3.2. Ferramentas
*   **Pytest**: Runner e framework de asserção.
*   **Unittest.Mock**: Para simular objetos e comportamentos.
*   **Coverage.py**: Para monitorar o progresso.

## 4. Plano de Ação

O plano será executado em etapas sequenciais para garantir estabilidade e progresso incremental.

### Etapa 1: Fundação (BaseRepository)
*   **Alvo**: `src/core/database/base_repository.py`
*   **Ação**: Criar `tests/core/database/test_base_repository.py`.
*   **Cenários**: CRUD básico (create, find, update, delete), validação de ULID, tratamento de erros de conexão, queries dinâmicas.

### Etapa 2: Core de IA (Agent)
*   **Alvo**: `src/modules/ai/engines/lchain/core/agents/agent.py`
*   **Ação**: Criar `tests/modules/ai/engines/lchain/core/agents/test_agent.py`.
*   **Cenários**: Execução de steps, seleção de tools, tratamento de erros de tools, loop de conversação, parse de respostas do LLM.

### Etapa 3: Integração Externa (TwilioService)
*   **Alvo**: `src/modules/channels/twilio/services/twilio_service.py`
*   **Ação**: Criar `tests/modules/channels/twilio/services/test_twilio_service.py`.
*   **Cenários**: Envio de mensagens (sucesso/falha), webhook validation, fallback para fake sender em dev, tratamento de exceções da API Twilio.

### Etapa 4: Camada de Dados Complexa (ConversationRepository)
*   **Alvo**: `src/modules/conversation/repositories/conversation_repository.py`
*   **Ação**: Expandir testes existentes ou criar novos focados em queries complexas.
*   **Cenários**: Queries com múltiplos filtros, paginação, transições de estado, integridade de dados.

### Etapa 5: Ferramentas de IA (Query Tool)
*   **Alvo**: `src/modules/ai/engines/lchain/feature/finance/tools/query.py`
*   **Ação**: Criar testes específicos para a lógica de parsing e execução de queries financeiras.

## 5. Perguntas para Alinhamento

1.  Existem cenários de borda específicos no fluxo do Agente que causaram problemas recentemente e devem ser priorizados?
2.  Para o `BaseRepository`, devemos simular erros de rede do Supabase para garantir resiliência?
3.  O `TwilioService` tem comportamentos específicos de retentativa que precisam ser validados?

## 6. Próximos Passos Imediatos

1.  Criar estrutura de diretórios para os novos testes.
2.  Iniciar implementação dos testes do `BaseRepository`.
