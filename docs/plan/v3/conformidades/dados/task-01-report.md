# Dados: Relatório de Padronização de Arquitetura de Dados

## 1. Contexto e Problema
Foi identificada uma inconsistência arquitetural no projeto relacionada à estratégia de acesso a dados:
- **Ambiguidade de Dependências**: O arquivo `requirements.txt` listava `sqlalchemy` (comentado) e `psycopg2`, sugerindo um uso misto ou legado de ORM.
- **Implementação Real**: O código operava 100% via **Supabase Client (REST)** e modelos **Pydantic**, sem uso real de SQLAlchemy.
- **Vazamento de Abstração**: A ferramenta de IA `query.py` (Módulo Finance) acessava diretamente `repository.client.table(...)`, violando o encapsulamento do padrão Repository e expondo a lógica de banco para a camada de aplicação/IA.

## 2. Decisão Arquitetural
Optou-se pelo **Caminho A**: Oficializar o **Supabase Client** como padrão único.
- **Motivo**: Manter a simplicidade (KISS), aproveitar a estrutura existente baseada em Pydantic e evitar a complexidade de gerenciar sessões/pools de um ORM SQL tradicional num projeto serverless-friendly.

## 3. Ações Realizadas

### 3.1. Padronização do Repositório (`BaseRepository`)
O `BaseRepository` foi evoluído para suportar consultas flexíveis sem expor o cliente HTTP.

- **Novo Método**: `query_dynamic(select_columns, filters)`
- **Funcionalidade**: Permite que serviços e ferramentas solicitem dados com filtros dinâmicos (eq, gt, lt, like, etc.) e seleção de campos específicos, mantendo a construção da query encapsulada.

### 3.2. Refatoração de Tools (`query.py`)
A ferramenta de consulta de dados financeiros (`QueryDataTool`) foi reescrita para obedecer à arquitetura.

- **Antes**: Construía queries manuais acessando `repository.client`.
- **Depois**: Prepara os parâmetros de filtro e delega a execução para `repository.query_dynamic()`.
- **Benefício**: Segurança (validação de colunas feita no Repositório) e Desacoplamento (Tool não sabe que o banco é Supabase).

### 3.3. Limpeza de Dependências
- Removida a referência comentada ao `sqlalchemy` no `requirements.txt`.
- Mantido `psycopg2-binary` apenas para suporte ao script de migração direta (`scripts/migrate.py`).

### 3.4. Validação e Testes
- Foi criada uma suíte de testes unitários (`tests/test_query_dynamic_refactor.py`) para validar:
    1. A construção correta das queries dinâmicas no Repositório.
    2. A integração da Tool com o novo método.
    3. O tratamento de erros (ex: solicitação de colunas inexistentes).
- **Resultado**: Todos os testes passaram com sucesso.

## 4. Estado Atual
A arquitetura de dados agora é consistente:
- **Camada de Dados**: Repositórios + Supabase Client.
- **Modelagem**: Pydantic (Unificado para API e Banco).
- **Acesso Externo (IA/API)**: Sempre via métodos do Repositório, sem acesso direto ao cliente de banco.

---
*Gerado em: 22/01/2026*
