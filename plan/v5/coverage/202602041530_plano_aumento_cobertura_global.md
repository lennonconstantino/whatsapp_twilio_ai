# Plano de Aumento de Cobertura de Testes (71% -> 90%)

Este plano detalha a estratégia para elevar a cobertura de testes globais do projeto, focando em áreas críticas de infraestrutura, segurança e paridade de backend de banco de dados.

## 1. Diagnóstico Atual (Deep Dive)
A análise da cobertura atual (aprox. 72%) revela lacunas estruturais importantes:

1.  **Disparidade de Backend (Postgres vs Supabase)**:
    *   O projeto suporta múltiplos backends, mas os testes parecem rodar predominantemente simulando ou usando o Supabase.
    *   **Evidência**: `conversation/repositories/impl/postgres` tem **18%** de cobertura, enquanto `impl/supabase` tem **80%**.
    *   **Risco**: O código do Postgres está "morto" nos testes, podendo esconder bugs críticos de SQL ou mapeamento.

2.  **Core & Segurança Desprotegidos**:
    *   Arquivos fundamentais como `custom_ulid.py` (IDs únicos) e `security.py` (Hashing) não aparecem nos relatórios ou têm cobertura nula.
    *   **Risco**: Falhas aqui corrompem dados silenciosamente.

3.  **Orquestração de IA (Agent Factory)**:
    *   A lógica que decide qual agente ativar (`AgentFactory`) não possui testes dedicados.
    *   **Risco**: Erros de roteamento de intenção em produção.

4.  **Workers Assíncronos**:
    *   O `OutboundWorker` (envio de mensagens) não está sendo exercitado.

## 2. Estratégia de Execução

A abordagem será dividida em 3 ondas para maximizar o impacto na cobertura e na segurança.

### 🌊 Onda 1: Infraestrutura e Core (Quick Wins)
Foco em testar utilitários isolados e garantir a base do sistema.
- **Ação 1.1**: Criar `tests/core/utils/test_custom_ulid.py`.
- **Ação 1.2**: Criar `tests/core/test_security.py`.
- **Ação 1.3**: Criar `tests/core/di/test_container.py` (básico de resolução).

### 🌊 Onda 2: Paridade de Repositórios (O Grande Salto)
Resolver a falta de testes nas implementações Postgres.
- **Ação 2.1**: Criar testes parametrizados para Repositórios. Em vez de testar apenas a implementação ativa, vamos instanciar explicitamente as versões Postgres e Supabase nos testes de repositório, garantindo que ambas cumpram a interface.
- **Alvos**:
    - `ConversationRepository` (Postgres)
    - `MessageRepository` (Postgres)
    - `UserRepository` (Postgres)

### 🌊 Onda 3: Inteligência e Workers
Testar a lógica de negócio complexa.
- **Ação 3.1**: Testar `AgentFactory` com mocks dos agentes.
- **Ação 3.2**: Testar `OutboundWorker` mockando o cliente Twilio.

## 3. Metas de Cobertura por Módulo

| Módulo | Cobertura Atual | Meta | Estratégia |
| :--- | :---: | :---: | :--- |
| **Core (Utils/Security)** | ~0% | 100% | Testes Unitários |
| **Repos Postgres** | ~25% | 85% | Testes de Contrato (Interface) |
| **AI Engine** | ~50% | 80% | Testes de Factory e Agentes |
| **Conversation** | 54% | 80% | Cobrir fluxos de borda da API |

## 4. Entregável
- Arquivo de plano: `plan/v5/coverage/202602041530_plano_aumento_cobertura_global.md`
- Pull Requests incrementais ou commits seguindo a ordem das Ondas.
