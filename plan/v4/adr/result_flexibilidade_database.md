# ADR: Arquitetura Híbrida de Persistência (Supabase + SQLAlchemy)

**Data:** 26/01/2026
**Status:** Aceito
**Relacionado a:** [Relatório Fase 1](../report/result_vazamento_abstracao_db_fase1.md)

## Contexto
O sistema dependia exclusivamente do SDK `supabase-py`, o que criava um acoplamento forte com o fornecedor (Vendor Lock-in). Embora o Supabase seja a solução padrão atual, existe o requisito estratégico de permitir o uso de bancos de dados SQL tradicionais (PostgreSQL, MySQL, SQLite) no futuro, seja para ambientes de desenvolvimento local, testes ou migração de infraestrutura.

A implementação anterior (`BaseRepository`) misturava lógica de conexão HTTP do Supabase com regras de negócio, impossibilitando o uso de um ORM padrão como SQLAlchemy sem reescrever toda a camada de acesso a dados.

## Decisão
Decidimos implementar uma arquitetura de **Repositório Polimórfico**, onde o sistema interage apenas com interfaces abstratas, permitindo a coexistência de múltiplas implementações de backend.


### 1. Contrato Unificado (`IRepository`)
Todo acesso a dados deve obedecer ao protocolo definido em `src/core/database/interface.py`. Este contrato impõe métodos CRUD padrão (`create`, `find_by_id`, `update`, `delete`) que devem ser respeitados por qualquer driver de banco.

### 2. Implementação Dual
Foram desenvolvidas duas implementações base que aderem ao contrato:

*   **[SupabaseRepository](file:///Users/lennon/projects/ai_engineering/whatsapp_twilio_ai/src/core/database/supabase_repository.py):** Implementação baseada em REST API via SDK do Supabase. É a implementação ativa padrão. Mantém validações específicas como ULID.
*   **[SQLAlchemyRepository](file:///Users/lennon/projects/ai_engineering/whatsapp_twilio_ai/src/core/database/sqlalchemy_repository.py):** Implementação genérica baseada em ORM (SQLAlchemy). Permite conexão com qualquer banco SQL (Postgres, SQLite, etc). Realiza a conversão automática entre Modelos ORM e Modelos Pydantic.

### Comparativo Rápido

| Característica | SupabaseRepository | SqlAlchemyRepository (ORM) | PostgresRepository (Puro) |
| :--- | :--- | :--- | :--- |
| **Tecnologia** | API HTTP (supabase-py) | SQLAlchemy ORM | psycopg2 (Driver Nativo) |
| **Protocolo** | HTTPS (REST) | TCP/IP (Socket) | TCP/IP (Socket) |
| **Abstração** | Alta (Tabela como Objeto) | Média (Classes Python) | Baixa (SQL Puro) |
| **Performance** | Média (Overhead HTTP) | Boa (Overhead Python) | Excelente (Direto no socket) |
| **Testes** | Requer Mock HTTP / Container | Suporta SQLite em Memória | Requer Container Postgres |
| **Transações** | Limitada (RPC / Cliente) | Completa (ACID / Session) | Completa (Manual BEGIN/COMMIT) |
| **Latência** | Média (Overhead HTTP + SSL) | Baixa (Pool de Conexões) | Mínima (Socket Direto) |
| **Uso Ideal** | Prototipagem / Serverless | Aplicações Complexas | Performance Crítica / Queries Manuais |


### 3. Estratégia de Troca (Strategy Pattern)
A escolha entre usar Supabase ou SQLAlchemy é determinada no momento da injeção de dependência (Container DI), sem alterar o código dos Serviços de Domínio.

## Consequências

### Positivas
*   **Independência de Fornecedor:** O sistema não está mais preso ao Supabase. Podemos mudar para um PostgreSQL self-hosted apenas alterando a configuração de injeção.
*   **Testabilidade:** O `SQLAlchemyRepository` permite usar SQLite em memória para testes de integração ultra-rápidos, sem necessidade de mocks de rede ou containers Docker pesados.
*   **Padronização:** Força o uso de Pydantic Models como a "língua franca" do sistema, impedindo que objetos específicos de ORM ou JSONs crus vazem para a camada de negócio.

### Negativas
*   **Duplicidade de Modelos (Futuro):** Ao ativar o uso do SQLAlchemy, será necessário manter classes de Modelo ORM (SQLAlchemy Base) em paralelo aos Schemas Pydantic.
*   **Complexidade de Configuração:** O container de injeção de dependência precisa ser capaz de instanciar o repositório correto baseado em variáveis de ambiente (`DB_DRIVER=supabase` vs `DB_DRIVER=postgres`).

## Próximos Passos
*   Definir Modelos SQLAlchemy correspondentes às tabelas existentes (User, Conversation, etc) quando for decidido ativar o suporte a SQL nativo.
*   Criar testes de integração que rodam contra SQLite para validar o `SQLAlchemyRepository`.
