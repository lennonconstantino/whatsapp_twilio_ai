# Análise Aprofundada: Mecanismo RAG Híbrido

Esta análise detalha a arquitetura atual de Recuperação Aumentada por Geração (RAG) do projeto, com foco específico nos mecanismos de ingestão, armazenamento e, principalmente, recuperação híbrida de informações.

## 1. Visão Geral da Arquitetura

O sistema implementa um pipeline RAG modular baseado em **PostgreSQL** (com `pgvector` para vetores e `tsvector` para texto), orquestrado via Python/LangChain.

### Componentes Principais:
1.  **Ingestão (`app/rag/ingest.py`):**
    *   **Staging:** Arquivos `.md` são carregados "crus" para a tabela `public.kb_docs`. Isso garante idempotência e permite reprocessamento futuro com diferentes estratégias.
    *   **Materialization:** O conteúdo de staging é processado (chunking + embedding) e persistido em `public.kb_chunks`.
    *   **Estratégias de Chunking:** Suporta `semantic` (via embeddings), `markdown` (por cabeçalhos) e `fixed` (tamanho fixo).

2.  **Armazenamento (`sql/kb/`):**
    *   Tabela `kb_chunks` armazena tanto o vetor (`embedding`) quanto o vetor de busca textual (`fts` - Full Text Search).
    *   Metadados cruciais: `client_id`, `empresa` e `meta` (JSONB).

3.  **Recuperação (`app/rag/tools.py` & `sql/kb/03_functions.sql`):**
    *   Exposta via ferramenta `kb_search_client`.
    *   Suporta modos: `vector`, `text`, `hybrid` (RRF) e `hybrid_union`.
    *   Inclui funcionalidades avançadas opcionais: **HyDE** (Hypothetical Document Embeddings) e **Reranking** (via Cohere).

## 2. Detalhe do Mecanismo de Recuperação (Hybrid Retrieval)

A recuperação híbrida é o núcleo da inteligência do sistema, combinando a precisão semântica (vetores) com a exatidão lexical (palavras-chave).

### A. Busca Híbrida com RRF (`kb_hybrid_search`)
Esta é a estratégia padrão e mais robusta.
*   **Implementação:** Realizada inteiramente no banco de dados (SQL) para máxima performance.
*   **Fluxo:**
    1.  Executa `kb_vector_search` (Similaridade de Cosseno) e retorna os Top-K.
    2.  Executa `kb_text_search` (Postgres Full Text Search `ts_rank_cd`) e retorna os Top-K.
    3.  Combina os resultados usando **Reciprocal Rank Fusion (RRF)**.
*   **Fórmula RRF:**
    ```sql
    score = coalesce(1.5 / (60 + rnk_v), 0) + coalesce(1.0 / (60 + rnk_t), 0)
    ```
    *   **Pesos:** A busca vetorial tem um peso ligeiramente maior (`1.5`) que a textual (`1.0`).
    *   **Constante K:** Fixada em `60`, padrão comum na literatura para estabilizar rankings.
    *   **Vantagem:** O RRF normaliza as escalas de pontuação totalmente diferentes (distância de cosseno vs. frequência de termos), tornando a fusão justa.

### B. Busca Híbrida via União (`kb_hybrid_union`)
Estratégia alternativa, mais simples, geralmente usada para comparações.
*   **Fluxo:** Executa Vector Search e Text Search independentemente e faz um `UNION` dos resultados.
*   **Problema Identificado:** O `UNION` no SQL, ao combinar resultados com scores diferentes (cosseno vs rank textual), pode resultar em **duplicatas do mesmo chunk** se ele aparecer em ambas as buscas. Isso polui a janela de contexto do LLM com informações repetidas.

## 3. Análise de Pontos Fortes e Fracos

### ✅ Pontos Fortes
1.  **Arquitetura "DB-First":** A lógica pesada de busca e fusão reside no PostgreSQL, reduzindo latência de rede e complexidade na aplicação Python.
2.  **Pipeline de Ingestão Robusto:** A separação entre *Staging* e *Chunks* é excelente. Permite testar novas estratégias de chunking (ex: mudar de `fixed` para `semantic`) sem precisar recarregar os arquivos originais do disco.
3.  **Filtros de Segurança:** Todas as queries exigem/suportam `client_id` e `empresa`, garantindo isolamento multi-tenant (data leakage prevention).
4.  **Suporte a Reranking:** A arquitetura já prevê um passo final de Reranking (ex: Cohere), que é o "estado da arte" para refinar resultados híbridos.

### ⚠️ Pontos de Atenção e Riscos (Para Conserto)

1.  **Duplicatas na Busca Híbrida (Union):**
    *   **Risco:** O método `kb_hybrid_union` não deduplica chunks que aparecem nas duas listas (vetor e texto).
    *   **Impacto:** O LLM recebe o mesmo parágrafo duas vezes, desperdiçando tokens e podendo alucinar por "viés de repetição".
    *   **Solução:** Implementar deduplicação (ex: `GROUP BY doc_path, chunk_ix` escolhendo o `MAX(score)`).

2.  **Parâmetros RRF Hardcoded:**
    *   **Risco:** Os pesos `1.5` (vetor) e `1.0` (texto) e a constante `60` estão fixos no SQL (`sql/kb/03_functions.sql`).
    *   **Impacto:** Impossível ajustar a importância do texto vs vetor sem migração de banco. Em domínios com muitos termos técnicos (códigos, IDs), a busca textual deveria ter peso maior.
    *   **Solução:** Transformar pesos em parâmetros da função SQL.

3.  **Chunking Markdown sem Fallback:**
    *   **Risco:** O `split_markdown` (`app/rag/loaders.py`) divide apenas por cabeçalhos (`#`). Se houver uma seção com 5.000 palavras sem subtítulos, ela será um único chunk gigante.
    *   **Impacto:** Estouro de janela de contexto ou perda de precisão no embedding (vetores perdem significado em textos muito longos).
    *   **Solução:** Implementar um chunking recursivo secundário dentro dos blocos markdown.

4.  **Falta de "Time-decay" ou Recência:**
    *   **Risco:** Não há mecanismo óbvio para priorizar documentos mais recentes.
    *   **Impacto:** O sistema pode recuperar políticas antigas/obsoletas se elas tiverem alta similaridade semântica.

## 4. Recomendações Imediatas para o "Conserto"

Se o objetivo é estabilizar e corrigir o projeto, recomendo a seguinte ordem de ação:

1.  **Corrigir `kb_hybrid_union`:** Alterar a query SQL para garantir deduplicação de resultados.
2.  **Parametrizar RRF:** Alterar a função `kb_hybrid_search` para aceitar pesos como argumentos opcionais, permitindo tuning via código Python.
3.  **Refinar Chunking Markdown:** Adicionar um `RecursiveCharacterTextSplitter` como fallback para seções markdown muito longas.
4.  **Validar Testes:** Executar `tests/rag/test_rrf_vs_union.py` após as correções para garantir que a deduplicação está funcionando.
