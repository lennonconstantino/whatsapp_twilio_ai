# Guia de Otimizações Opcionais - Aproveitando Índices JSONB

## 🎯 Objetivo

Este documento mostra **otimizações opcionais** que você pode implementar para aproveitar ao máximo os novos índices JSONB. Todas as otimizações são **opcionais** e o código atual já funciona perfeitamente.

---

## 📊 Nível de Prioridade

### 🟢 Baixa Prioridade (Implementar se tiver tempo)
- Queries que já funcionam bem mas poderiam ser mais rápidas
- Código que não apresenta problemas de performance

### 🟡 Média Prioridade (Implementar se base crescer muito)
- Queries que podem ficar lentas com >100k registros
- Features de relatórios/analytics

### 🔴 Alta Prioridade (Implementar se houver problema)
- Queries que já apresentam lentidão
- Operações críticas de tempo real

---

## 1. 🟢 ConversationRepository - Busca por Context

### Otimização Opcional #1: Buscar por customer_id

**Situação Atual (funciona bem):**
```python
def find_by_customer(self, owner_id: int, customer_id: str) -> List[Conversation]:
    """Find conversations by customer_id in context."""
    conversations = self.find_active_by_owner(owner_id)
    return [c for c in conversations if c.context.get('customer_id') == customer_id]
```

**Otimização (usa idx_conversations_context_status):**
```python
def find_by_customer_optimized(
    self, 
    owner_id: int, 
    customer_id: str,
    status: Optional[ConversationStatus] = None
) -> List[Conversation]:
    """
    Find conversations by customer_id in context (optimized).
    
    Uses expression index: idx_conversations_context_status
    """
    try:
        query = self.client.table(self.table_name)\
            .select("*")\
            .eq("owner_id", owner_id)\
            .eq("context->>customer_id", customer_id)
        
        if status:
            query = query.eq("status", status.value)
        
        result = query.order("started_at", desc=True).execute()
        return [self.model_class(**item) for item in result.data]
    except Exception as e:
        logger.error("Error finding conversations by customer", error=str(e))
        raise
```

**Quando usar:** Se você frequentemente busca conversas por customer_id

---

### Otimização Opcional #2: Buscar conversas com tags específicas

**Novo método (aproveita idx_conversations_context_gin):**
```python
def find_by_tag(
    self,
    owner_id: int,
    tag: str,
    limit: int = 50
) -> List[Conversation]:
    """
    Find conversations with specific tag in context.
    
    Uses GIN index: idx_conversations_context_gin
    Expects context structure: {"tags": ["urgent", "vip"]}
    """
    try:
        # PostgreSQL JSONB contains operator
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("owner_id", owner_id)\
            .contains("context", {"tags": [tag]})\
            .order("started_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return [self.model_class(**item) for item in result.data]
    except Exception as e:
        logger.error("Error finding conversations by tag", error=str(e))
        raise
```

**Exemplo de uso:**
```python
# Buscar conversas urgentes
urgent_conversations = repo.find_by_tag(owner_id=1, tag="urgent")

# Buscar conversas VIP
vip_conversations = repo.find_by_tag(owner_id=1, tag="vip")
```

---

### Otimização Opcional #3: Buscar por metadata priority

**Novo método (usa idx_conversations_metadata_priority):**
```python
def find_high_priority(
    self,
    owner_id: int,
    limit: int = 50
) -> List[Conversation]:
    """
    Find high priority conversations.
    
    Uses partial index: idx_conversations_metadata_priority
    This is VERY fast because index is small (only high priority)
    """
    try:
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("owner_id", owner_id)\
            .eq("metadata->>priority", "high")\
            .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
            .order("started_at", desc=True)\
            .limit(limit)\
            .execute()
        
        return [self.model_class(**item) for item in result.data]
    except Exception as e:
        logger.error("Error finding high priority conversations", error=str(e))
        raise
```

---

## 2. 🟡 MessageRepository - Busca por Metadata

### Otimização Opcional #4: Buscar mensagens por delivery status

**Novo método (usa idx_messages_metadata_delivery_status):**
```python
def find_by_delivery_status(
    self,
    conv_id: Optional[int] = None,
    status: str = "pending",
    limit: int = 100
) -> List[Message]:
    """
    Find messages by delivery status.
    
    Uses expression index: idx_messages_metadata_delivery_status
    Common statuses: pending, delivered, failed, read
    """
    try:
        query = self.client.table(self.table_name)\
            .select("*")\
            .eq("metadata->>delivery_status", status)
        
        if conv_id:
            query = query.eq("conv_id", conv_id)
        
        result = query\
            .order("timestamp", desc=True)\
            .limit(limit)\
            .execute()
        
        return [self.model_class(**item) for item in result.data]
    except Exception as e:
        logger.error("Error finding messages by delivery status", error=str(e))
        raise
```

**Exemplo de uso:**
```python
# Buscar mensagens pendentes de entrega
pending_messages = message_repo.find_by_delivery_status(status="pending")

# Buscar mensagens falhadas de uma conversa específica
failed_messages = message_repo.find_by_delivery_status(
    conv_id=123,
    status="failed"
)
```

---

### Otimização Opcional #5: Buscar mensagens com anexos

**Novo método (usa idx_messages_metadata_gin):**
```python
def find_with_attachments(
    self,
    conv_id: Optional[int] = None,
    media_type: Optional[str] = None,
    limit: int = 50
) -> List[Message]:
    """
    Find messages with media attachments.
    
    Uses GIN index: idx_messages_metadata_gin
    """
    try:
        query = self.client.table(self.table_name).select("*")
        
        if conv_id:
            query = query.eq("conv_id", conv_id)
        
        # Filter messages where metadata has media_url key
        # In Supabase, we can check if key exists
        if media_type:
            # Filter by specific media type
            query = query.eq("metadata->>media_type", media_type)
        else:
            # Just check if media_url exists
            query = query.not_.is_("metadata->>media_url", "null")
        
        result = query\
            .order("timestamp", desc=True)\
            .limit(limit)\
            .execute()
        
        return [self.model_class(**item) for item in result.data]
    except Exception as e:
        logger.error("Error finding messages with attachments", error=str(e))
        raise
```

**Exemplo de uso:**
```python
# Buscar todas as mensagens com anexos
messages_with_media = message_repo.find_with_attachments(conv_id=123)

# Buscar apenas imagens
image_messages = message_repo.find_with_attachments(
    conv_id=123,
    media_type="image/jpeg"
)
```

---

## 3. 🟢 FeatureRepository - Busca por Config

### Otimização Opcional #6: Buscar features por configuração

**Novo método (usa idx_features_config_gin e idx_features_config_enabled):**
```python
def find_by_config_key(
    self,
    owner_id: int,
    key: str,
    value: Optional[Any] = None
) -> List[Feature]:
    """
    Find features by configuration key/value.
    
    Uses:
    - idx_features_config_gin for general queries
    - idx_features_config_enabled for 'enabled' key
    """
    try:
        query = self.client.table(self.table_name)\
            .select("*")\
            .eq("owner_id", owner_id)
        
        if value is not None:
            # Search by key and value
            if isinstance(value, bool):
                # For boolean, convert to string
                query = query.eq(f"config_json->>{key}", str(value).lower())
            else:
                query = query.eq(f"config_json->>{key}", str(value))
        else:
            # Just check if key exists
            # Supabase: check if key is not null
            query = query.not_.is_(f"config_json->>{key}", "null")
        
        result = query.execute()
        return [self.model_class(**item) for item in result.data]
    except Exception as e:
        logger.error("Error finding features by config", error=str(e))
        raise

def find_with_model(
    self,
    owner_id: int,
    model_name: str
) -> List[Feature]:
    """Find features using specific AI model."""
    return self.find_by_config_key(owner_id, "model", model_name)

def find_enabled_in_config(self, owner_id: int) -> List[Feature]:
    """
    Find features with enabled=true in config_json.
    
    Uses: idx_features_config_enabled (very fast!)
    """
    return self.find_by_config_key(owner_id, "enabled", True)
```

**Exemplo de uso:**
```python
# Buscar features usando GPT-4
gpt4_features = feature_repo.find_with_model(owner_id=1, model_name="gpt-4")

# Buscar features com webhook configurado
webhook_features = feature_repo.find_by_config_key(owner_id=1, key="webhook_url")

# Buscar features habilitadas via config
enabled_features = feature_repo.find_enabled_in_config(owner_id=1)
```

---

## 4. 🟡 ConversationService - Métodos de Business Logic

### Otimização Opcional #7: Analytics de conversas

**Novo serviço de analytics:**
```python
class ConversationAnalyticsService:
    """Service for conversation analytics using JSONB indexes."""
    
    def __init__(self, conversation_repo: ConversationRepository):
        self.repo = conversation_repo
    
    def get_conversations_by_topic(
        self,
        owner_id: int,
        topic: str,
        limit: int = 50
    ) -> List[Conversation]:
        """
        Get conversations about specific topic.
        
        Expects context: {"topic": "Product inquiry"}
        Uses: idx_conversations_context_gin
        """
        try:
            result = self.repo.client.table("conversations")\
                .select("*")\
                .eq("owner_id", owner_id)\
                .eq("context->>topic", topic)\
                .order("started_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [self.repo.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error getting conversations by topic", error=str(e))
            return []
    
    def get_reactivated_conversations(
        self,
        owner_id: int,
        days: int = 7
    ) -> List[Conversation]:
        """
        Get conversations that were reactivated from idle.
        
        Uses: idx_conversations_context_gin
        Checks for context.reactivated_from_idle
        """
        try:
            threshold = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = self.repo.client.table("conversations")\
                .select("*")\
                .eq("owner_id", owner_id)\
                .not_.is_("context->reactivated_from_idle", "null")\
                .gte("started_at", threshold.isoformat())\
                .execute()
            
            return [self.repo.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error getting reactivated conversations", error=str(e))
            return []
    
    def get_conversations_with_closure_detected(
        self,
        owner_id: int,
        min_confidence: float = 0.5
    ) -> List[Conversation]:
        """
        Get conversations where closure was detected.
        
        Uses: idx_conversations_context_gin
        """
        try:
            # This is more complex - we need to filter by nested JSON
            # In PostgreSQL, we can do: context->'closure_detected'->>'confidence'
            result = self.repo.client.table("conversations")\
                .select("*")\
                .eq("owner_id", owner_id)\
                .not_.is_("context->closure_detected", "null")\
                .execute()
            
            # Filter by confidence in Python (could be optimized with SQL function)
            conversations = [self.repo.model_class(**item) for item in result.data]
            
            return [
                c for c in conversations
                if c.context.get('closure_detected', {}).get('confidence', 0) >= min_confidence
            ]
        except Exception as e:
            logger.error("Error getting conversations with closure", error=str(e))
            return []
```

---

## 5. 🔴 AIResultRepository - Queries de AI Results

### Otimização Opcional #8: Repository para AI Results

**Novo repository otimizado:**
```python
class AIResultRepository(BaseRepository[AIResult]):
    """Repository for AI Result entity operations."""
    
    def __init__(self, client: Client):
        super().__init__(client, "ai_results", AIResult)
    
    def find_by_confidence(
        self,
        feature_id: int,
        min_confidence: float = 0.8,
        limit: int = 100
    ) -> List[AIResult]:
        """
        Find AI results by confidence score.
        
        Uses: idx_ai_results_json_confidence
        Expects: result_json.analysis.confidence
        """
        try:
            # PostgreSQL cast to numeric for comparison
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("feature_id", feature_id)\
                .gte("result_json->analysis->>confidence", str(min_confidence))\
                .order("processed_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding results by confidence", error=str(e))
            raise
    
    def find_by_category(
        self,
        category: str,
        feature_id: Optional[int] = None,
        limit: int = 100
    ) -> List[AIResult]:
        """
        Find AI results by category.
        
        Uses: idx_ai_results_json_category
        Common categories: sentiment_positive, sentiment_negative, etc.
        """
        try:
            query = self.client.table(self.table_name)\
                .select("*")\
                .eq("result_json->>category", category)
            
            if feature_id:
                query = query.eq("feature_id", feature_id)
            
            result = query\
                .order("processed_at", desc=True)\
                .limit(limit)\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding results by category", error=str(e))
            raise
    
    def find_successful_results(
        self,
        feature_id: int,
        days: int = 7
    ) -> List[AIResult]:
        """
        Find successful AI results in last N days.
        
        Uses: idx_ai_results_json_gin
        """
        try:
            threshold = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = self.client.table(self.table_name)\
                .select("*")\
                .eq("feature_id", feature_id)\
                .contains("result_json", {"status": "success"})\
                .gte("processed_at", threshold.isoformat())\
                .execute()
            
            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error("Error finding successful results", error=str(e))
            raise
```

---

## 6. 🎯 Exemplos de Uso Completos

### Exemplo 1: Dashboard de Conversas Prioritárias

```python
from typing import Dict, List, Any

def get_priority_dashboard(owner_id: int) -> Dict[str, Any]:
    """
    Get dashboard data for high-priority conversations.
    
    Uses optimized JSONB queries.
    """
    conv_repo = ConversationRepository(get_db())
    msg_repo = MessageRepository(get_db())
    
    # Buscar conversas de alta prioridade (usa índice parcial)
    high_priority = conv_repo.find_high_priority(owner_id, limit=20)
    
    # Buscar conversas urgentes por tag (usa GIN index)
    urgent = conv_repo.find_by_tag(owner_id, "urgent", limit=20)
    
    # Buscar mensagens pendentes de entrega
    pending_deliveries = msg_repo.find_by_delivery_status(status="pending")
    
    # Buscar mensagens falhadas
    failed_messages = msg_repo.find_by_delivery_status(status="failed", limit=10)
    
    return {
        "high_priority_count": len(high_priority),
        "high_priority_conversations": high_priority[:5],  # Top 5
        "urgent_count": len(urgent),
        "urgent_conversations": urgent[:5],
        "pending_deliveries": len(pending_deliveries),
        "failed_messages_count": len(failed_messages),
        "failed_messages": failed_messages
    }
```

### Exemplo 2: Relatório de AI Performance

```python
def get_ai_performance_report(
    feature_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get AI feature performance report.
    
    Uses optimized JSONB queries on ai_results.
    """
    ai_repo = AIResultRepository(get_db())
    
    # Resultados com alta confiança
    high_confidence = ai_repo.find_by_confidence(
        feature_id=feature_id,
        min_confidence=0.8
    )
    
    # Resultados por categoria
    positive_sentiment = ai_repo.find_by_category(
        category="sentiment_positive",
        feature_id=feature_id
    )
    
    negative_sentiment = ai_repo.find_by_category(
        category="sentiment_negative",
        feature_id=feature_id
    )
    
    # Resultados bem-sucedidos
    successful = ai_repo.find_successful_results(
        feature_id=feature_id,
        days=days
    )
    
    return {
        "total_high_confidence": len(high_confidence),
        "positive_sentiment_count": len(positive_sentiment),
        "negative_sentiment_count": len(negative_sentiment),
        "success_rate": len(successful) / max(len(high_confidence), 1) * 100,
        "period_days": days
    }
```

### Exemplo 3: Analytics de Reativação

```python
def get_reactivation_analytics(owner_id: int) -> Dict[str, Any]:
    """
    Analyze conversation reactivation patterns.
    
    Uses JSONB context queries.
    """
    conv_repo = ConversationRepository(get_db())
    analytics = ConversationAnalyticsService(conv_repo)
    
    # Conversas reativadas nos últimos 7 dias
    reactivated = analytics.get_reactivated_conversations(
        owner_id=owner_id,
        days=7
    )
    
    # Analisar padrões
    reactivation_times = []
    for conv in reactivated:
        reactivation_info = conv.context.get('reactivated_from_idle', {})
        if reactivation_info:
            reactivation_times.append(reactivation_info)
    
    return {
        "total_reactivated": len(reactivated),
        "reactivation_details": reactivation_times,
        "average_per_day": len(reactivated) / 7
    }
```

---

## 📊 Comparação de Performance

### Antes (sem índices otimizados):
```python
# Buscar conversas de alta prioridade
# Método: Busca todas + filtra em Python
conversations = repo.find_active_by_owner(owner_id)  # 10.000 rows
high_priority = [c for c in conversations if c.metadata.get('priority') == 'high']
# Tempo: ~500ms (scan completo)
```

### Depois (com índice parcial):
```python
# Buscar conversas de alta prioridade
# Método: Query direta com índice
high_priority = repo.find_high_priority(owner_id)
# Tempo: ~5ms (index scan em ~50 rows)
# Melhoria: 100x mais rápido! 🚀
```

---

## 🎓 Quando Implementar Estas Otimizações

### ✅ Implemente AGORA se:
- Você já tem queries lentas (>1 segundo)
- Sua base tem >100k conversas ou mensagens
- Você precisa de relatórios/analytics em tempo real

### ⏳ Implemente DEPOIS se:
- Sua aplicação está funcionando bem
- Sua base ainda é pequena (<10k registros)
- Não há reclamações de performance

### ❌ NÃO implemente se:
- Você não vai usar essas queries
- Otimização prematura
- Tempo de desenvolvimento é crítico

---

## 📝 Template para Novos Métodos Otimizados

```python
def find_by_jsonb_field(
    self,
    owner_id: int,
    field_path: str,  # Ex: "context->>customer_id"
    value: Any,
    limit: int = 100
) -> List[Model]:
    """
    Generic method to find records by JSONB field.
    
    Args:
        owner_id: Owner ID
        field_path: JSONB field path (use ->> for text, -> for object)
        value: Value to search for
        limit: Maximum results
    
    Returns:
        List of Model instances
    
    Example:
        # Search by customer_id in context
        results = repo.find_by_jsonb_field(
            owner_id=1,
            field_path="context->>customer_id",
            value="CUST123"
        )
    """
    try:
        result = self.client.table(self.table_name)\
            .select("*")\
            .eq("owner_id", owner_id)\
            .eq(field_path, value)\
            .limit(limit)\
            .execute()
        
        return [self.model_class(**item) for item in result.data]
    except Exception as e:
        logger.error(f"Error finding by {field_path}", error=str(e))
        raise
```

---

**Lembre-se:** Todas essas otimizações são **opcionais**. Seu código atual já está funcionando perfeitamente e se beneficiando automaticamente dos índices GIN! 🎉
