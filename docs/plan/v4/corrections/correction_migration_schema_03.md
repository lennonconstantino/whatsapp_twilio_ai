# Relatório de Correção: Migração e Limpeza de Schema

**Data:** 26/01/2026
**Responsável:** Lennon (Assistant)
**Arquivo:** `plan/v4/corrections/correction_migration_schema_03.md`

## 1. Contexto e Problema

Durante a execução do comando `make migrate`, o processo falhou com um erro de duplicação de tabela (`psycopg2.errors.DuplicateTable: relation "idx_plans_active" already exists`).

Isso indicava que o script de limpeza (`000_drop_schema.sql`) não estava removendo corretamente todos os objetos do banco de dados antes de tentar recriá-los, deixando o ambiente em um estado inconsistente ("sujo").

### Erro Original

```text
Running 001_initial_schema.sql...
Traceback (most recent call last):
  ...
psycopg2.errors.DuplicateTable: relation "idx_plans_active" already exists
```

## 2. Análise da Causa Raiz

A análise do arquivo `migrations/000_drop_schema.sql` revelou dois problemas principais:

1.  **Tabelas Ausentes no Drop**: O script não incluía comandos para remover as tabelas recentemente adicionadas ao sistema: `plans`, `plan_features`, `subscriptions`.
2.  **Fragilidade na Remoção de Dependências**: O script tentava remover explicitamente objetos dependentes (como `DROP POLICY`, `DROP TRIGGER`, `DROP INDEX`) *antes* de remover as tabelas. Isso causava falhas se a tabela pai já tivesse sido removida em uma execução anterior parcial, gerando erros como `relation "owners" does not exist`.

## 3. Solução Implementada

Refatoramos o script `migrations/000_drop_schema.sql` para adotar uma abordagem mais robusta e idempotente.

### 3.1. Uso de `DROP TABLE ... CASCADE`

Em vez de remover manualmente cada trigger, policy e índice, passamos a confiar no mecanismo `CASCADE` do PostgreSQL. Ao remover uma tabela com `CASCADE`, o banco automaticamente remove todos os objetos que dependem dela.

Isso simplifica o script e elimina a necessidade de manutenção manual de drops para cada novo índice ou constraint criado.

### 3.2. Ordem Inversa de Dependência

Garantimos que as tabelas sejam removidas na ordem inversa de suas dependências (filhas antes das mães), embora o `CASCADE` também mitigasse problemas de ordem.

### Diagrama de Dependência e Cascata

O diagrama abaixo ilustra como a remoção da tabela raiz (ou tabelas pai) propaga a limpeza para os objetos dependentes.

```mermaid
graph TD
    subgraph "Database Schema Cleanup Strategy"
        direction BT
        
        %% Entidades Principais
        Owner[Owner Table]
        User[User Table]
        Sub[Subscription Table]
        Plan[Plan Table]
        Feat[Feature Table]
        Conv[Conversation Table]
        Msg[Message Table]
        
        %% Dependências (Setas indicam 'Depende De')
        User --> Owner
        Sub --> Owner
        Sub --> Plan
        Feat --> Owner
        Conv --> Owner
        Conv --> User
        Msg --> Conv
        
        %% Objetos Dependentes (implícitos no CASCADE)
        classDef dependent fill:#f9f,stroke:#333,stroke-dasharray: 5 5;
        classDef table fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
        
        Idx1(Indexes) ::: dependent
        Trig1(Triggers) ::: dependent
        Pol1(RLS Policies) ::: dependent
        
        Owner --- Idx1
        Owner --- Trig1
        Owner --- Pol1
    end

    subgraph "Action: DROP TABLE ... CASCADE"
        Step1[1. DROP subscriptions CASCADE] -->|Removes| Sub
        Step1 -->|Cascades to| SubIdx[Subscription Indexes]
        
        Step2[2. DROP plans CASCADE] -->|Removes| Plan
        
        Step3[3. DROP conversations CASCADE] -->|Removes| Conv
        Step3 -->|Cascades to| Msg
        Step3 -->|Cascades to| ConvIdx[Conversation Indexes]
        
        Step4[4. DROP owners CASCADE] -->|Removes| Owner
        Step4 -->|Cascades to| User
        Step4 -->|Cascades to| Feat
        Step4 -->|Cascades to| OwnerObjs[Policies, Triggers, Indexes]
    end
    
    style Step1 fill:#ffcdd2,stroke:#b71c1c
    style Step2 fill:#ffcdd2,stroke:#b71c1c
    style Step3 fill:#ffcdd2,stroke:#b71c1c
    style Step4 fill:#ffcdd2,stroke:#b71c1c
    
    class Owner,User,Sub,Plan,Feat,Conv,Msg table
```

## 4. Resultado

Após a aplicação das correções, o comando `make migrate` foi executado com sucesso:

1.  `000_drop_schema.sql` executou sem erros, limpando todo o banco.
2.  `001_initial_schema.sql` recriou a estrutura base.
3.  Todas as migrações subsequentes (`002` a `006`) foram aplicadas corretamente.

O ambiente de desenvolvimento agora está consistente e o processo de reset do banco (drop + migrate) é confiável.
