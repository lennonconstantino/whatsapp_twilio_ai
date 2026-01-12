# Guia Completo de Indexação JSONB - Owner Project

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Estratégias de Indexação](#estratégias-de-indexação)
3. [Índices Implementados](#índices-implementados)
4. [Exemplos de Consultas](#exemplos-de-consultas)
5. [Análise de Performance](#análise-de-performance)
6. [Manutenção](#manutenção)
7. [Migração de Índices](#migração-de-índices)

---

## 🎯 Visão Geral

O PostgreSQL oferece suporte robusto para campos JSONB com diferentes estratégias de indexação. Este guia documenta as implementações e melhores práticas para o projeto Owner.

### Campos JSONB no Schema

| Tabela | Campo | Propósito | Estratégia de Índice |
|--------|-------|-----------|---------------------|
| `features` | `config_json` | Configurações de features | GIN + Expression |
| `twilio_accounts` | `phone_numbers` | Array de telefones | GIN |
| `conversations` | `context` | Contexto da conversa | GIN + Expression |
| `conversations` | `metadata` | Metadados adicionais | GIN + Partial |
| `messages` | `metadata` | Metadados de mensagens | GIN + Expression |
| `ai_results` | `result_json` | Resultados de processamento | GIN + Expression |

---

## 🔍 Estratégias de Indexação

### 1. **GIN Index (Generalized Inverted Index)**

**Quando usar:**
- Consultas de contenção (`@>`, `<@`)
- Verificação de existência de chaves (`?`, `?&`, `?|`)
- Queries flexíveis onde não se sabe quais chaves serão consultadas

**Vantagens:**
- Suporta múltiplos operadores JSONB
- Excelente para queries exploratórias
- Indexa todo o documento JSONB

**Desvantagens:**
- Maior tamanho de armazenamento
- Pode ser mais lento para updates
- Não otimiza ordenação por campos específicos

**Exemplo de criação:**
```sql
CREATE INDEX idx_conversations_context_gin 
ON conversations USING gin(context);
```

**Queries otimizadas:**
```sql
-- Buscar por chave-valor específica
SELECT * FROM conversations 
WHERE context @> '{"language": "pt-BR"}';

-- Verificar existência de chave
SELECT * FROM conversations 
WHERE context ? 'customer_id';

-- Múltiplas chaves
SELECT * FROM conversations 
WHERE context ?& ARRAY['customer_id', 'session_id'];

-- Qualquer uma das chaves
SELECT * FROM conversations 
WHERE context ?| ARRAY['email', 'phone'];
```

---

### 2. **Expression Index**

**Quando usar:**
- Acesso frequente a campos JSONB específicos
- Necessidade de ordenação por campos JSONB
- Queries repetitivas nos mesmos campos
- Comparações com valores escalares

**Vantagens:**
- Muito rápido para campos específicos
- Suporta ordenação (ORDER BY)
- Menor tamanho que GIN
- Ótimo para filtros WHERE em campos conhecidos

**Desvantagens:**
- Apenas para campos específicos
- Precisa de um índice por campo consultado
- Não funciona para queries exploratórias

**Exemplo de criação:**
```sql
-- Índice simples em campo específico
CREATE INDEX idx_conversations_context_customer 
ON conversations((context->>'customer_id'));

-- Índice composto com outro campo
CREATE INDEX idx_conversations_context_status 
ON conversations((context->>'customer_id'), status)
WHERE context->>'customer_id' IS NOT NULL;

-- Índice com cast para tipos numéricos
CREATE INDEX idx_ai_confidence 
ON ai_results(((result_json->'analysis'->>'confidence')::numeric));
```

**Queries otimizadas:**
```sql
-- Busca por campo específico
SELECT * FROM conversations 
WHERE context->>'customer_id' = '12345';

-- Ordenação por campo JSONB
SELECT * FROM conversations 
ORDER BY (context->>'created_at')::timestamp DESC;

-- Filtro numérico
SELECT * FROM ai_results 
WHERE (result_json->'analysis'->>'confidence')::numeric > 0.8;

-- Busca combinada
SELECT * FROM conversations 
WHERE context->>'customer_id' = '12345' 
AND status = 'progress';
```

---

### 3. **Partial Index**

**Quando usar:**
- Queries que sempre incluem condições WHERE específicas
- Subconjunto dos dados muito consultado
- Economia de espaço em disco
- Performance em writes (menos dados indexados)

**Vantagens:**
- Índice menor = mais rápido
- Melhora performance de writes
- Reduz uso de disco
- Ideal para dados com padrões previsíveis

**Desvantagens:**
- Só funciona para condições incluídas no índice
- Precisa ajustar se padrões de query mudarem

**Exemplo de criação:**
```sql
-- Índice apenas para conversas ativas
CREATE INDEX idx_conversations_context_active 
ON conversations((context->>'customer_id'))
WHERE status IN ('pending', 'progress');

-- Índice para prioridade alta
CREATE INDEX idx_conversations_metadata_priority 
ON conversations((metadata->>'priority'))
WHERE metadata->>'priority' = 'high';

-- Índice para mensagens não entregues
CREATE INDEX idx_messages_delivery_pending 
ON messages((metadata->>'delivery_status'))
WHERE metadata->>'delivery_status' = 'pending';
```

**Queries otimizadas:**
```sql
-- Query DEVE incluir a condição do índice parcial
SELECT * FROM conversations 
WHERE context->>'customer_id' = '12345' 
AND status IN ('pending', 'progress');

-- Mensagens com delivery pendente
SELECT * FROM messages 
WHERE metadata->>'delivery_status' = 'pending'
ORDER BY timestamp;
```

---

## 📊 Índices Implementados

### Features Table

```sql
-- GIN para queries gerais
CREATE INDEX idx_features_config_gin 
ON features USING gin(config_json);

-- Expression para flag enabled
CREATE INDEX idx_features_config_enabled 
ON features((config_json->>'enabled')) 
WHERE config_json->>'enabled' IS NOT NULL;
```

**Use cases:**
```sql
-- Buscar features com webhook configurado
SELECT * FROM features 
WHERE config_json ? 'webhook_url';

-- Buscar features com API habilitada
SELECT * FROM features 
WHERE config_json @> '{"api_enabled": true}';

-- Buscar features enabled
SELECT * FROM features 
WHERE config_json->>'enabled' = 'true';
```

---

### Twilio Accounts Table

```sql
-- GIN para busca em array de números
CREATE INDEX idx_twilio_phone_numbers_gin 
ON twilio_accounts USING gin(phone_numbers);
```

**Use cases:**
```sql
-- Verificar se número existe na conta
SELECT * FROM twilio_accounts 
WHERE phone_numbers @> '["+5511999999999"]';

-- Contar números por owner
SELECT owner_id, jsonb_array_length(phone_numbers) as total_numbers
FROM twilio_accounts;

-- Buscar conta que tem um número específico
SELECT * FROM twilio_accounts 
WHERE phone_numbers ? '+5511999999999';
```

---

### Conversations Table

```sql
-- GIN para context
CREATE INDEX idx_conversations_context_gin 
ON conversations USING gin(context);

-- Expression para customer_id com status
CREATE INDEX idx_conversations_context_status 
ON conversations((context->>'customer_id'), status)
WHERE context->>'customer_id' IS NOT NULL;

-- GIN para metadata
CREATE INDEX idx_conversations_metadata_gin 
ON conversations USING gin(metadata);

-- Partial para prioridade alta
CREATE INDEX idx_conversations_metadata_priority 
ON conversations((metadata->>'priority'))
WHERE metadata->>'priority' = 'high';
```

**Use cases:**
```sql
-- Buscar conversas por cliente
SELECT * FROM conversations 
WHERE context->>'customer_id' = 'CUST123'
AND status = 'progress';

-- Buscar conversas com tag específica
SELECT * FROM conversations 
WHERE context @> '{"tags": ["urgent"]}';

-- Conversas de alta prioridade
SELECT * FROM conversations 
WHERE metadata->>'priority' = 'high'
ORDER BY started_at DESC;

-- Buscar por múltiplos critérios no context
SELECT * FROM conversations 
WHERE context @> '{"language": "pt-BR", "source": "website"}';
```

---

### Messages Table

```sql
-- GIN para metadata
CREATE INDEX idx_messages_metadata_gin 
ON messages USING gin(metadata);

-- Expression para delivery status
CREATE INDEX idx_messages_metadata_delivery_status 
ON messages((metadata->>'delivery_status'))
WHERE metadata->>'delivery_status' IS NOT NULL;
```

**Use cases:**
```sql
-- Mensagens não entregues
SELECT m.* 
FROM messages m
WHERE metadata->>'delivery_status' IN ('pending', 'failed')
ORDER BY timestamp DESC;

-- Mensagens com anexos
SELECT * FROM messages 
WHERE metadata ? 'attachments';

-- Mensagens lidas
SELECT * FROM messages 
WHERE metadata @> '{"read": true}';

-- Buscar mensagens com erro específico
SELECT * FROM messages 
WHERE metadata->'error'->>'code' = 'E001';
```

---

### AI Results Table

```sql
-- GIN para result_json
CREATE INDEX idx_ai_results_json_gin 
ON ai_results USING gin(result_json);

-- Expression para confidence score
CREATE INDEX idx_ai_results_json_confidence 
ON ai_results(((result_json->'analysis'->>'confidence')::numeric))
WHERE result_json->'analysis'->>'confidence' IS NOT NULL;

-- Expression para category
CREATE INDEX idx_ai_results_json_category 
ON ai_results((result_json->>'category'))
WHERE result_json->>'category' IS NOT NULL;
```

**Use cases:**
```sql
-- Resultados com alta confiança
SELECT * FROM ai_results 
WHERE (result_json->'analysis'->>'confidence')::numeric > 0.8;

-- Filtrar por categoria
SELECT * FROM ai_results 
WHERE result_json->>'category' = 'sentiment_positive';

-- Buscar por múltiplos critérios
SELECT * FROM ai_results 
WHERE result_json @> '{"status": "success", "processed": true}';

-- Análise de sentimentos negativos com baixa confiança
SELECT 
    ar.ai_result_id,
    m.body,
    ar.result_json->>'category' as sentiment,
    (ar.result_json->'analysis'->>'confidence')::numeric as confidence
FROM ai_results ar
JOIN messages m ON ar.msg_id = m.msg_id
WHERE result_json->>'category' LIKE '%negative%'
AND (result_json->'analysis'->>'confidence')::numeric < 0.6;
```

---

## 📈 Análise de Performance

### Como verificar se índices estão sendo usados

```sql
-- Analisar plano de execução
EXPLAIN ANALYZE
SELECT * FROM conversations 
WHERE context @> '{"customer_id": "12345"}';

-- Estatísticas de uso de índices
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as vezes_usado,
    idx_tup_read as tuplas_lidas,
    idx_tup_fetch as tuplas_retornadas
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename IN ('conversations', 'messages', 'ai_results', 'features')
ORDER BY idx_scan DESC;

-- Índices não utilizados (candidatos para remoção)
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as tamanho
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexrelname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Tamanho dos índices

```sql
-- Ver tamanho de todos os índices JSONB
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as tamanho_indice,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as tamanho_tabela
FROM pg_stat_user_indexes
WHERE indexname LIKE '%_gin' OR indexname LIKE '%json%'
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Benchmark de queries

```sql
-- Criar função de timing
CREATE OR REPLACE FUNCTION benchmark_query(query_text TEXT, iterations INT DEFAULT 100)
RETURNS TABLE(avg_time NUMERIC, min_time NUMERIC, max_time NUMERIC) AS $$
DECLARE
    start_time TIMESTAMP;
    end_time TIMESTAMP;
    times NUMERIC[];
    i INT;
BEGIN
    times := ARRAY[]::NUMERIC[];
    
    FOR i IN 1..iterations LOOP
        start_time := clock_timestamp();
        EXECUTE query_text;
        end_time := clock_timestamp();
        times := array_append(times, EXTRACT(MILLISECONDS FROM (end_time - start_time)));
    END LOOP;
    
    RETURN QUERY SELECT 
        AVG(t)::NUMERIC(10,3) as avg_time,
        MIN(t)::NUMERIC(10,3) as min_time,
        MAX(t)::NUMERIC(10,3) as max_time
    FROM unnest(times) t;
END;
$$ LANGUAGE plpgsql;

-- Usar a função
SELECT * FROM benchmark_query(
    'SELECT * FROM conversations WHERE context @> ''{"customer_id": "12345"}'';',
    100
);
```

---

## 🔧 Manutenção

### Atualizar estatísticas

```sql
-- Atualizar estatísticas de uma tabela
ANALYZE conversations;
ANALYZE messages;
ANALYZE ai_results;

-- Atualizar todas as tabelas
ANALYZE;

-- Ver quando foi a última análise
SELECT 
    schemaname,
    relname,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY last_analyze DESC NULLS LAST;
```

### Reindexar

```sql
-- Reindexar uma tabela específica
REINDEX TABLE conversations;

-- Reindexar um índice específico
REINDEX INDEX idx_conversations_context_gin;

-- Reindexar todas as tabelas do schema
REINDEX SCHEMA public;

-- Reindexar de forma concorrente (sem bloquear)
-- Disponível apenas para índices individuais
REINDEX INDEX CONCURRENTLY idx_conversations_context_gin;
```

### Vacuum

```sql
-- Vacuum completo em uma tabela
VACUUM FULL conversations;

-- Vacuum e análise juntos
VACUUM ANALYZE conversations;

-- Ver estatísticas de bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as tamanho_total
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Monitoramento contínuo

```sql
-- Criar view para monitoramento
CREATE OR REPLACE VIEW v_jsonb_index_health AS
SELECT 
    t.schemaname,
    t.tablename,
    i.indexname,
    pg_size_pretty(pg_relation_size(i.indexrelid)) as index_size,
    i.idx_scan as scans,
    i.idx_tup_read as tuples_read,
    i.idx_tup_fetch as tuples_fetched,
    CASE 
        WHEN i.idx_scan = 0 THEN 'Nunca usado'
        WHEN i.idx_scan < 100 THEN 'Pouco usado'
        WHEN i.idx_scan < 1000 THEN 'Uso moderado'
        ELSE 'Muito usado'
    END as status_uso
FROM pg_stat_user_tables t
JOIN pg_stat_user_indexes i ON t.relid = i.relid
WHERE i.indexrelname LIKE '%json%' 
   OR i.indexrelname LIKE '%_gin';

-- Consultar a view
SELECT * FROM v_jsonb_index_health
ORDER BY scans DESC;
```

---

## 🚀 Migração de Índices

### Script para adicionar índices em produção

```sql
-- ============================================
-- Adicionar índices JSONB em ambiente vivo
-- ============================================

-- 1. Criar índices CONCURRENTLY (não bloqueia)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_context_gin 
ON conversations USING gin(context);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_metadata_gin 
ON conversations USING gin(metadata);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_metadata_gin 
ON messages USING gin(metadata);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_ai_results_json_gin 
ON ai_results USING gin(result_json);

-- 2. Aguardar conclusão e verificar
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE indexrelname LIKE '%_gin'
ORDER BY pg_relation_size(indexrelid) DESC;

-- 3. Atualizar estatísticas
ANALYZE conversations;
ANALYZE messages;
ANALYZE ai_results;

-- 4. Testar queries críticas
EXPLAIN ANALYZE
SELECT * FROM conversations 
WHERE context @> '{"customer_id": "test"}';
```

### Rollback de índices

```sql
-- Remover índices se necessário
DROP INDEX CONCURRENTLY IF EXISTS idx_conversations_context_gin;
DROP INDEX CONCURRENTLY IF EXISTS idx_conversations_metadata_gin;
DROP INDEX CONCURRENTLY IF EXISTS idx_messages_metadata_gin;
DROP INDEX CONCURRENTLY IF EXISTS idx_ai_results_json_gin;
```

---

## 💡 Dicas Finais

### ✅ Boas Práticas

1. **Sempre use JSONB** (não JSON) para dados indexados
2. **Comece com GIN** para flexibilidade, adicione Expression indexes conforme necessário
3. **Monitore o uso** dos índices regularmente
4. **Use EXPLAIN ANALYZE** antes de adicionar índices em produção
5. **Crie índices CONCURRENTLY** em produção para evitar locks
6. **Mantenha estatísticas atualizadas** com ANALYZE
7. **Documente o propósito** de cada índice JSONB

### ❌ Evite

1. Criar muitos índices antes de entender os padrões de query
2. Índices em campos JSONB raramente acessados
3. Expression indexes para todos os campos (use GIN primeiro)
4. Esquecer de atualizar índices quando o schema JSONB mudar
5. Ignorar índices não utilizados (ocupam espaço e afetam writes)

### 🎯 Quando adicionar novos índices

Adicione um índice JSONB quando:
- Uma query específica for lenta (> 1 segundo)
- O EXPLAIN ANALYZE mostrar Sequential Scan em campo JSONB
- Um campo JSONB for consultado frequentemente (> 100 vezes/dia)
- Você tiver dados suficientes para justificar (> 10.000 registros)

### 📊 Métricas para decisão

```sql
-- Query para ajudar na decisão de criar índices
WITH query_analysis AS (
    SELECT 
        'conversations.context' as campo,
        COUNT(*) as total_registros,
        pg_size_pretty(pg_relation_size('conversations')) as tamanho_tabela,
        (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'conversations' AND indexdef LIKE '%context%') as indices_existentes
    FROM conversations
    WHERE context IS NOT NULL
)
SELECT 
    campo,
    total_registros,
    tamanho_tabela,
    indices_existentes,
    CASE 
        WHEN total_registros < 1000 THEN 'Não precisa de índice ainda'
        WHEN total_registros < 10000 THEN 'Considere criar índice'
        WHEN total_registros < 100000 THEN 'Índice recomendado'
        ELSE 'Índice essencial'
    END as recomendacao
FROM query_analysis;
```

---

## 📚 Referências

- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html)
- [PostgreSQL Index Types](https://www.postgresql.org/docs/current/indexes-types.html)
- [GIN Indexes](https://www.postgresql.org/docs/current/gin.html)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)

---

**Última atualização:** Janeiro 2026  
**Versão do Schema:** 1.0  
**PostgreSQL Version:** 12+
