# ADR: Desacoplamento da Camada de Dados via Repository Pattern

**Data:** 26/01/2026
**Status:** Aceito e Implementado
**Atividade:** Vazamento de Abstração do Banco de Dados

## Contexto
O projeto utilizava uma implementação direta do padrão Repository (`BaseRepository`) que estava fortemente acoplada à biblioteca `supabase-py`. Os serviços de domínio (ex: `UserService`, `OwnerService`) dependiam diretamente de classes concretas que herdavam desse repositório base.

Isso gerava os seguintes problemas:
1.  **Violação de DIP (Dependency Inversion Principle):** Módulos de alto nível (regras de negócio) dependiam de detalhes de implementação (driver do Supabase).
2.  **Dificuldade de Testes:** Para testar um serviço, era necessário mockar o cliente HTTP do Supabase ou usar uma instância real, tornando os testes lentos e frágeis.
3.  **Vendor Lock-in:** Migrar para outro banco de dados (ex: PostgreSQL com SQLAlchemy) exigiria refatoração massiva em todas as camadas do sistema.

## Decisão
Decidimos refatorar a camada de persistência para adotar estritamente o **Repository Pattern** com **Injeção de Dependência** baseada em interfaces (Protocols).

As principais mudanças arquiteturais são:

1.  **Interface Genérica (`IRepository`):**
    Criamos um Protocolo genérico (`src/core/database/interface.py`) que define as operações CRUD básicas (`create`, `update`, `delete`, `find_by_id`), independente da tecnologia de banco.

2.  **Interfaces de Domínio (`I{Entity}Repository`):**
    Para cada entidade, definimos uma interface específica (ex: `IUserRepository` em `src/modules/identity/repositories/interfaces.py`) que herda de `IRepository` e adiciona métodos de consulta específicos do domínio (ex: `find_by_email`).

3.  **Implementação Base (`SupabaseRepository`):**
    A lógica específica do Supabase foi encapsulada em uma classe base concreta (`src/core/database/supabase_repository.py`) que implementa `IRepository`. Os repositórios concretos (ex: `UserRepository`) herdam desta classe mas são tipados como implementações da interface de domínio.

4.  **Injeção de Dependência:**
    Os serviços agora declaram dependência apenas das interfaces (ex: `IUserRepository`), desconhecendo a implementação concreta. O container de injeção (`src/core/di/container.py`) é responsável por instanciar a classe concreta e injetá-la como a interface requerida.

## Consequências

### Positivas
*   **Desacoplamento Total:** A camada de negócio não conhece mais o Supabase; ela interage apenas com abstrações Python puras.
*   **Testabilidade:** Testes unitários podem usar mocks simples que implementam a interface `IUserRepository`, sem complexidade de rede ou banco de dados. Isso foi validado pela correção e execução bem-sucedida dos testes de `identity_service`.
*   **Flexibilidade:** Adicionar suporte a um novo banco de dados (ex: PostgreSQL local) exige apenas criar uma nova implementação da interface e alterar a configuração do container.
*   **Manutenibilidade:** O contrato de acesso a dados está explícito nas interfaces.

### Negativas
*   **Complexidade:** Aumento no número de arquivos e abstrações (interfaces + implementações).
*   **Boilerplate:** Necessidade de declarar métodos na interface e na implementação.

## Histórico de Implementação
A implementação foi realizada em duas fases para garantir segurança e consistência:

*   **Fase 1 (Estrutural):** Criação das abstrações base (`IRepository`) e refatoração da classe base (`SupabaseRepository`).
*   **Fase 2 (Desacoplamento):** Criação das interfaces de domínio e atualização dos construtores dos Serviços para dependerem das interfaces, validado via testes.

## Referências
*   Clean Architecture (Robert C. Martin)
*   Repository Pattern (Martin Fowler)
*   Python Protocols (PEP 544)
