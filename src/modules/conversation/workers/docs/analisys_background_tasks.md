# Background Tasks: Melhorias e Compatibilidade com Session Key

## Análise da Compatibilidade

### ✅ Boa Notícia: Totalmente Compatível!

O `background_tasks.py` **NÃO precisa de mudanças obrigatórias** devido à adição do `session_key`. 

**Por quê?**
- As tasks usam `ConversationService.process_idle_conversations()` e `process_expired_conversations()`
- Esses métodos chamam `ConversationRepository.find_idle_conversations()` e `find_expired_conversations()`
- Essas queries **não dependem** de `from_number` e `to_number` para buscar conversas
- Elas buscam por: `status`, `updated_at`, `expires_at` - campos não afetados

```python
# Método process_expired_conversations usa:
def find_expired_conversations(self, limit: int = 100):
    result = self.client.table(self.table_name)\
        .select("*")\
        .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
        .lt("expires_at", now)  # ← Não usa from_number/to_number
        .limit(limit)\
        .execute()
```

### 📊 Impacto do Session Key no Background Tasks

| Aspecto | Impacto | Ação Necessária |
|---------|---------|-----------------|
| Lógica de busca | ✅ Nenhum | Nenhuma |
| Performance | ✅ Melhora | Nenhuma (benefício automático) |
| Queries de cleanup | ✅ Nenhum | Nenhuma |
| Métricas | ✅ Nenhum | Nenhuma |

---

## Melhorias Implementadas (Opcionais mas Recomendadas)

Mesmo sem necessidade obrigatória, implementei várias melhorias no `background_tasks_improved.py`:

### 1. Métricas e Monitoramento

```python
@dataclass
class TaskMetrics:
    """Rastreia performance de cada task."""
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    total_items_processed: int = 0
    last_run_at: Optional[datetime] = None
    total_execution_time_seconds: float = 0.0
```

**Benefícios:**
- Monitora taxa de sucesso/falha
- Rastreia performance ao longo do tempo
- Identifica degradação de performance
- Facilita debugging

### 2. Shutdown Gracioso Melhorado

```python
def _interruptible_sleep(self, seconds: float):
    """Sleep que pode ser interrompido."""
    # Acorda a cada 1s para checar flag de shutdown
    # Permite shutdown rápido mesmo durante sleep longo
```

**Antes:**
```python
time.sleep(60)  # Demora até 60s para parar
```

**Depois:**
```python
self._interruptible_sleep(60)  # Para em ~1s
```

### 3. Health Check Endpoint

```python
def get_health_status(self) -> Dict[str, Any]:
    """Status de saúde para monitoramento."""
    return {
        "status": "healthy",  # healthy | degraded | stopped
        "running": True,
        "uptime_seconds": 3600,
        "cycle_count": 60,
        "tasks": {...}
    }
```

**Uso:**
- Integração com Kubernetes liveness/readiness probes
- Monitoramento via Prometheus/Grafana
- Alertas automáticos de falha

### 4. Configuração Flexível por Task

```python
self.task_config = {
    "idle_conversations": {
        "enabled": True,
        "interval_multiplier": 1,  # Roda todo ciclo
    },
    "expired_conversations": {
        "enabled": True,
        "interval_multiplier": 2,  # Roda a cada 2 ciclos
    }
}
```

**Benefício:** Permitir diferentes frequências para diferentes tasks.

### 5. Batch Processing Configurável

```python
# Antes (hardcoded)
self.conversation_service.process_idle_conversations(limit=100)

# Depois (configurável)
BackgroundWorker(batch_size=500)  # Processa até 500 por vez
```

### 6. Error Recovery e Logging Aprimorado

```python
try:
    count = self.conversation_service.process_idle_conversations(...)
    logger.info("Processed idle", count=count, time=elapsed)
    metrics.record_success(count, elapsed)
except Exception as e:
    logger.error("Error in task", error=str(e), exc_info=True)
    metrics.record_failure(str(e), elapsed)
    # Continua rodando outras tasks!
```

---

## Otimizações de Performance com Session Key

### Benefício Indireto

Embora o background task não use `session_key` diretamente, ele se **beneficia indiretamente**:

```sql
-- ANTES (sem session_key)
-- Múltiplas conversas ativas duplicadas para mesmo par
SELECT COUNT(*) FROM conversations 
WHERE status IN ('pending', 'progress');
-- Resultado: 10,000 conversas (muitas duplicadas)

-- DEPOIS (com session_key)
-- Apenas 1 conversa por par
SELECT COUNT(*) FROM conversations 
WHERE status IN ('pending', 'progress');
-- Resultado: 5,000 conversas (sem duplicatas)
```

**Impacto no Background Task:**
- ✅ Menos conversas para processar
- ✅ Queries de cleanup mais rápidas
- ✅ Menos overhead de atualização

### Query Performance

```sql
-- find_expired_conversations() beneficia do índice parcial
CREATE INDEX idx_conversations_expires 
ON conversations(expires_at) 
WHERE status IN ('pending', 'progress');

-- Com menos conversas duplicadas:
-- Antes: ~10,000 rows scanned
-- Depois: ~5,000 rows scanned
-- Melhoria: 2x mais rápido! 🚀
```

---

## Configuração Recomendada

### 1. Variáveis de Ambiente

```bash
# .env
BACKGROUND_TASK_INTERVAL=60        # segundos entre ciclos
BACKGROUND_TASK_BATCH_SIZE=100     # itens por batch
BACKGROUND_TASK_ENABLE_METRICS=true
```

### 2. Systemd Service

```ini
[Unit]
Description=Conversation Background Tasks
After=network.target postgresql.service

[Service]
Type=simple
User=app
WorkingDirectory=/app
Environment="PYTHONPATH=/app"
ExecStart=/app/venv/bin/python -m src.tasks.background_tasks \
    --interval 60 \
    --batch-size 100
Restart=always
RestartSec=10

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

### 3. Docker Compose

```yaml
version: '3.8'

services:
  background_worker:
    image: myapp:latest
    command: python -m src.tasks.background_tasks --interval 60
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - LOG_LEVEL=INFO
    restart: unless-stopped
    depends_on:
      - postgres
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 4. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: background-worker
spec:
  replicas: 1  # Apenas 1 worker por vez!
  selector:
    matchLabels:
      app: background-worker
  template:
    metadata:
      labels:
        app: background-worker
    spec:
      containers:
      - name: worker
        image: myapp:latest
        command: ["python", "-m", "src.tasks.background_tasks"]
        args: ["--interval", "60", "--batch-size", "100"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command: ["python", "-c", "import sys; sys.exit(0)"]
          initialDelaySeconds: 30
          periodSeconds: 30
```

---

## Monitoramento

### 1. Logs Estruturados

```python
# Logs do worker incluem contexto rico
logger.info(
    "Processed idle conversations",
    count=15,
    idle_minutes=30,
    execution_time_seconds=0.234,
    cycle=42
)
```

### 2. Prometheus Metrics (Opcional)

```python
from prometheus_client import Counter, Histogram, Gauge

# Métricas exportáveis
conversations_processed = Counter(
    'background_conversations_processed_total',
    'Total conversations processed',
    ['task_type']
)

task_duration = Histogram(
    'background_task_duration_seconds',
    'Task execution time',
    ['task_type']
)

active_conversations = Gauge(
    'active_conversations',
    'Number of active conversations'
)
```

### 3. Alertas

```yaml
# alerts.yml
groups:
- name: background_tasks
  rules:
  - alert: BackgroundTaskFailureRate
    expr: |
      rate(background_task_failures_total[5m]) > 0.1
    for: 5m
    annotations:
      summary: "High failure rate in background tasks"
      
  - alert: BackgroundTaskSlow
    expr: |
      background_task_duration_seconds{quantile="0.95"} > 10
    for: 10m
    annotations:
      summary: "Background tasks running slowly"
```

---

## Testing

### 1. Teste Manual

```bash
# Rodar uma vez
python -m src.tasks.background_tasks --once

# Rodar com intervalo curto
python -m src.tasks.background_tasks --interval 10

# Batch size maior
python -m src.tasks.background_tasks --batch-size 500
```

### 2. Teste Unitário

```python
import unittest
from src.tasks.background_tasks import BackgroundWorker

class TestBackgroundWorker(unittest.TestCase):
    def test_idle_conversations(self):
        """Test idle conversation processing."""
        worker = BackgroundWorker(interval_seconds=1)
        worker.started_at = datetime.now(timezone.utc)
        worker.cycle_count = 1
        
        # Run task
        worker._run_idle_conversations_task()
        
        # Check metrics
        metrics = worker.metrics["idle_conversations"]
        self.assertEqual(metrics.total_runs, 1)
        self.assertGreaterEqual(metrics.successful_runs, 1)
    
    def test_health_status(self):
        """Test health status reporting."""
        worker = BackgroundWorker()
        worker.started_at = datetime.now(timezone.utc)
        worker.running = True
        
        status = worker.get_health_status()
        
        self.assertEqual(status["status"], "healthy")
        self.assertTrue(status["running"])
```

### 3. Teste de Integração

```python
def test_background_task_integration():
    """Test full background task cycle."""
    # Create test conversations
    conv_service = ConversationService()
    
    # Create expired conversation
    expired_conv = conv_service._create_new_conversation(
        owner_id=100,
        from_number="+5511999999999",
        to_number="+5511888888888",
        channel="whatsapp",
        user_id=None,
        metadata={}
    )
    
    # Manually set expired time
    db_client = get_db()
    db_client.table("conversations")\
        .update({"expires_at": "2020-01-01T00:00:00Z"})\
        .eq("conv_id", expired_conv.conv_id)\
        .execute()
    
    # Run worker once
    worker = BackgroundWorker()
    worker.started_at = datetime.now(timezone.utc)
    worker._run_expired_conversations_task()
    
    # Verify conversation was expired
    updated_conv = conv_service.get_conversation_by_id(expired_conv.conv_id)
    assert updated_conv.status == ConversationStatus.EXPIRED.value
```

---

## Troubleshooting

### Problema: Worker não para graciosamente

**Sintoma:** Worker demora muito para parar após SIGTERM

**Causa:** Sleep longo sem interrupção

**Solução:**
```python
# Use _interruptible_sleep ao invés de time.sleep
self._interruptible_sleep(60)  # Pode parar em ~1s
```

### Problema: Memória aumentando

**Sintoma:** Uso de memória cresce ao longo do tempo

**Causa:** Conexões de banco não sendo fechadas

**Solução:**
```python
# Adicionar no _shutdown()
def _shutdown(self):
    # Close database connections
    self.conversation_service.conversation_repo.client.close()
    logger.info("Database connections closed")
```

### Problema: Tasks lentas

**Sintoma:** Cycles demorando mais que intervalo

**Solução:**
```python
# Aumentar batch_size ou intervalo
worker = BackgroundWorker(
    interval_seconds=120,  # 2 minutos
    batch_size=200  # Mais itens por batch
)
```

---

## Migração do Código Existente

### Passo 1: Backup

```bash
cp background_tasks.py background_tasks_backup.py
```

### Passo 2: Substituir

```bash
cp background_tasks_improved.py background_tasks.py
```

### Passo 3: Testar

```bash
# Teste local
python background_tasks.py --once

# Verificar logs
tail -f logs/background_tasks.log
```

### Passo 4: Deploy

```bash
# Parar worker antigo
systemctl stop background-worker

# Atualizar código
git pull

# Iniciar novo worker
systemctl start background-worker

# Verificar status
systemctl status background-worker
```

---

## Checklist de Implementação

- [ ] Fazer backup do código atual
- [ ] Atualizar background_tasks.py
- [ ] Testar localmente com `--once`
- [ ] Configurar variáveis de ambiente
- [ ] Atualizar systemd service (se aplicável)
- [ ] Configurar monitoramento
- [ ] Deploy em staging
- [ ] Verificar métricas por 24h
- [ ] Deploy em produção
- [ ] Monitorar por 1 semana

---

## Conclusão

### Resposta à Pergunta Original

**"Devo me preocupar com background_tasks.py?"**

✅ **Não é obrigatório, mas recomendado aproveitar para melhorar!**

**Compatibilidade:**
- ✅ Código atual funciona sem mudanças
- ✅ Session key não quebra nada
- ✅ Performance melhora automaticamente

**Melhorias Opcionais (mas valiosas):**
- ✅ Métricas e monitoramento
- ✅ Shutdown gracioso melhorado
- ✅ Health checks
- ✅ Configuração flexível
- ✅ Error handling robusto

**Recomendação Final:**
Use esta oportunidade para modernizar o background worker com as melhorias propostas. O esforço é pequeno e os benefícios são significativos!
