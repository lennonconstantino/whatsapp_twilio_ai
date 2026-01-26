# ADR: Refatoração de Testes BullMQ e Limpeza de Scripts

## 1. Contexto e Motivação

Durante a análise do projeto, foi identificado um script descartável `scripts/test_bullmq.py` que continha lógica de teste manual para o backend de fila `BullMQ`. Este arquivo violava as regras de arquitetura do projeto ("Evite scripts descartáveis" e "Use dados falsos apenas em testes isolados") e apresentava riscos de manutenção, como:

*   **Credenciais Hardcoded**: Utilização de `localhost` diretamente no código.
*   **Falta de CI/CD**: O script não era executado automaticamente na suíte de testes.
*   **Dependências Implícitas**: O script dependia de bibliotecas (`bullmq`, `redis`) que não estavam listadas no `requirements.txt`.

Além disso, ao tentar formalizar o teste, descobriu-se um bug latente na implementação da classe `BullMQBackend`.

## 2. Decisões e Mudanças

### 2.1. Migração para Testes Unitários
O script foi removido e substituído por um teste unitário formal em `tests/core/queue/test_bullmq_backend.py`.
*   **Framework**: Utilizado `pytest` e `pytest-asyncio`.
*   **Isolamento**: Utilizado `unittest.mock` para simular as classes `Queue`, `Worker` e a conexão `aioredis`, eliminando a necessidade de um servidor Redis real durante os testes unitários.

### 2.2. Correção de Bug (Bugfix)
Foi identificado que o método `start_consuming` da classe `BullMQBackend` utilizava `asyncio.Event` sem importar o módulo `asyncio`.
*   **Ação**: Adicionado `import asyncio` em `src/core/queue/backends/bullmq.py`.
*   **Impacto**: Prevenção de `NameError` em tempo de execução ao iniciar workers.

### 2.3. Gestão de Dependências
As bibliotecas necessárias para o funcionamento do BullMQ foram explicitamente adicionadas ao `requirements.txt`:
```text
bullmq>=0.6.0
redis>=5.0.0
```

### 2.4. Limpeza
*   **Remoção**: O arquivo `scripts/test_bullmq.py` foi excluído do repositório.

## 3. Consequências

### Positivas
*   **Conformidade**: O projeto agora adere melhor às diretrizes de código limpo e testes.
*   **Confiabilidade**: O bug de importação foi corrigido antes de causar falhas em produção.
*   **Manutenibilidade**: As dependências estão claras e o teste é parte integrante da suíte automatizada.
*   **Segurança**: Remoção de código com configurações de ambiente hardcoded.

### Negativas / Riscos
*   Nenhum risco significativo identificado. Apenas o esforço pontual de refatoração.

## 4. Status
**Concluído** e verificado via execução de testes (`pytest tests/core/queue/test_bullmq_backend.py`).
