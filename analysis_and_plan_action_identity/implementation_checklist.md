# 📋 CHECKLIST DE IMPLEMENTAÇÃO - SaaS Multi-Tenant Architecture

## 🎯 Objetivo
Refatorar o módulo Identity para uma arquitetura SaaS Multi-Tenant moderna com:
- Feature catalog centralizado
- Usage tracking em tempo real
- Plan versioning (grandfathering)
- Subscription lifecycle completo
- Separação de responsabilidades (módulos Identity e Billing)

---

## ✅ FASE 1: PREPARAÇÃO (1-2 dias)

### 1.1 Backup e Documentação
- [ ] Fazer backup completo do banco de dados
- [ ] Documentar esquema atual (tabelas, relacionamentos)
- [ ] Documentar APIs atuais que serão afetadas
- [ ] Criar ambiente de staging para testes
- [ ] Definir estratégia de rollback

### 1.2 Code Freeze
- [ ] Comunicar time sobre refatoração
- [ ] Criar branch de desenvolvimento: `feature/saas-multitenant-refactor`
- [ ] Pausar novos desenvolvimentos no módulo Identity
- [ ] Criar feature flag para dual-mode (novo/antigo sistema)

---

## ✅ FASE 2: DATABASE MIGRATION (2-3 dias)

### 2.1 Criar Novas Tabelas
- [ ] Executar script: `migration_saas_multitenant.sql`
  - [ ] `features_catalog` ✓
  - [ ] `plan_features` (nova versão com FKs corretos) ✓
  - [ ] `feature_usage` ✓
  - [ ] `plan_versions` ✓
  - [ ] `subscription_events` ✓

### 2.2 Atualizar Tabelas Existentes
- [ ] Adicionar campos em `subscriptions`:
  - [ ] `current_period_start`
  - [ ] `current_period_end`
  - [ ] `cancel_at`
  - [ ] `canceled_at`
  - [ ] `cancellation_reason`
  - [ ] `trial_start`
  - [ ] `trial_end`
  - [ ] `plan_version_id`
  - [ ] `metadata`

- [ ] Atualizar constraint de `status` em `subscriptions`
- [ ] Criar índices para novos campos

### 2.3 Criar Funções Helper
- [ ] `initialize_feature_usage_for_subscription()`
- [ ] `check_feature_access()`
- [ ] `increment_feature_usage()`

### 2.4 Migrar Dados Existentes
- [ ] Migrar features antigas para `features_catalog`
- [ ] Popular `plan_features` com FKs corretos
- [ ] Criar `plan_versions` iniciais (versão 1 para cada plano)
- [ ] Inicializar `feature_usage` para subscriptions ativas

### 2.5 Validar Migração
- [ ] Executar queries de validação:
```sql
-- Verificar integridade
SELECT COUNT(*) FROM features_catalog;
SELECT COUNT(*) FROM plan_features WHERE feature_id NOT IN (SELECT feature_id FROM features_catalog);
SELECT COUNT(*) FROM feature_usage WHERE owner_id NOT IN (SELECT owner_id FROM owners);

-- Verificar dados migrados
SELECT p.name, COUNT(pf.*) as feature_count 
FROM plans p 
LEFT JOIN plan_features pf ON p.plan_id = pf.plan_id 
GROUP BY p.name;
```

---

## ✅ FASE 3: IMPLEMENTAR REPOSITORIES (2-3 dias)

### 3.1 Criar Novos Repositories

#### `IFeaturesCatalogRepository`
- [ ] Interface/Protocol definido
- [ ] Implementação Supabase
- [ ] Implementação Postgres
- [ ] Métodos:
  - [ ] `create(feature_data)`
  - [ ] `find_by_key(feature_key)`
  - [ ] `find_by_id(feature_id)`
  - [ ] `find_all(filters)`
  - [ ] `update(feature_id, data)`
  - [ ] `delete(feature_id)` (soft delete)

#### `IFeatureUsageRepository`
- [ ] Interface/Protocol definido
- [ ] Implementação Supabase
- [ ] Implementação Postgres
- [ ] Métodos:
  - [ ] `create(usage_data)`
  - [ ] `upsert(usage_data)`
  - [ ] `find_by_owner_and_feature(owner_id, feature_id)`
  - [ ] `find_all_by_owner(owner_id)`
  - [ ] `increment(owner_id, feature_id, amount)`
  - [ ] `decrement(owner_id, feature_id, amount)`
  - [ ] `update(usage_id, data)`
  - [ ] `reset_for_period(owner_id)`

#### `IPlanVersionRepository`
- [ ] Interface/Protocol definido
- [ ] Implementação Supabase
- [ ] Implementação Postgres
- [ ] Métodos:
  - [ ] `create(version_data)`
  - [ ] `find_by_plan(plan_id)`
  - [ ] `find_active_version(plan_id)`
  - [ ] `find_by_id(version_id)`
  - [ ] `deactivate_version(version_id)`

#### `ISubscriptionEventRepository`
- [ ] Interface/Protocol definido
- [ ] Implementação Supabase
- [ ] Implementação Postgres
- [ ] Métodos:
  - [ ] `create(event_data)`
  - [ ] `find_by_subscription(subscription_id)`
  - [ ] `find_by_type(event_type)`
  - [ ] `find_recent(limit)`

### 3.2 Atualizar Repository Existente

#### `IPlanRepository` (atualizar)
- [ ] Adicionar método `get_features(plan_id)` (retorna plan_features com joins)

#### `ISubscriptionRepository` (atualizar)
- [ ] Suporte para novos campos
- [ ] Métodos para lifecycle:
  - [ ] `find_pending_cancellations()`
  - [ ] `find_expiring_trials(days_before)`
  - [ ] `find_past_due()`

### 3.3 Unit Tests para Repositories
- [ ] Tests para `FeaturesCatalogRepository`
- [ ] Tests para `FeatureUsageRepository`
- [ ] Tests para `PlanVersionRepository`
- [ ] Tests para `SubscriptionEventRepository`

---

## ✅ FASE 4: IMPLEMENTAR SERVICES (4-5 dias)

### 4.1 `FeaturesCatalogService`
- [ ] Implementar classe base
- [ ] Métodos:
  - [ ] `create_feature()`
  - [ ] `get_feature_by_key()`
  - [ ] `get_all_features()`
  - [ ] `deprecate_feature()`
- [ ] Unit tests
- [ ] Integration tests

### 4.2 `FeatureUsageService`
- [ ] Implementar classe base
- [ ] Métodos:
  - [ ] `initialize_features_for_tenant()`
  - [ ] `check_feature_access()` ⭐ CRÍTICO
  - [ ] `increment_usage()` ⭐ CRÍTICO
  - [ ] `decrement_usage()`
  - [ ] `get_usage_summary()`
  - [ ] `reset_usage_for_period()`
  - [ ] `override_quota()`
- [ ] Integrar cache (Redis/Memcached)
- [ ] Unit tests
- [ ] Integration tests
- [ ] Load tests (simular 10k+ checks/incrementos por segundo)

### 4.3 Refatorar `PlanService`
- [ ] Adicionar `plan_versions` support
- [ ] Método `create_plan_version()`
- [ ] Método `get_active_version()`
- [ ] Atualizar `add_feature_to_plan()` para usar `features_catalog`
- [ ] Atualizar testes existentes

### 4.4 Refatorar `SubscriptionService`
- [ ] Integrar `FeatureUsageService`
- [ ] Integrar event logging
- [ ] Atualizar método `create_subscription()`:
  - [ ] Inicializar feature_usage
  - [ ] Logar evento
- [ ] Implementar `upgrade_subscription()`:
  - [ ] Validação de upgrade path
  - [ ] Atualizar feature quotas
  - [ ] Logar evento
- [ ] Implementar `downgrade_subscription()`:
  - [ ] Schedule para period end
  - [ ] Logar evento
- [ ] Melhorar `cancel_subscription()`:
  - [ ] Suporte para immediate vs scheduled
  - [ ] Logar evento
- [ ] Novo método `reactivate_subscription()`
- [ ] Atualizar testes existentes
- [ ] Adicionar novos testes

### 4.5 Background Jobs/Cron
- [ ] Job para reset de usage mensal:
```python
def reset_monthly_usage_job():
    """Run this daily to reset usage for expired periods."""
    # Get all active subscriptions
    # For each, check if period has ended
    # Reset usage if needed
```

- [ ] Job para expirar trials:
```python
def expire_trials_job():
    """Run this daily to expire trials."""
    # Find trials ending today
    # Update status to 'expired' or 'active' (if paid)
```

- [ ] Job para cancelamentos pendentes:
```python
def process_pending_cancellations_job():
    """Run this daily to process scheduled cancellations."""
    # Find subscriptions with cancel_at <= today
    # Update status to 'canceled'
    # Log event
```

---

## ✅ FASE 5: SEGREGAÇÃO DE MÓDULOS (2-3 dias)

### 5.1 Criar Novo Módulo: `src/modules/billing/`
- [ ] Estrutura de diretórios:
```
src/modules/billing/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── plan.py
│   ├── plan_feature.py
│   ├── plan_version.py
│   ├── subscription.py
│   ├── subscription_event.py
│   ├── feature.py (feature catalog)
│   └── feature_usage.py
├── repositories/
│   ├── __init__.py
│   ├── interfaces.py
│   ├── supabase/
│   │   └── ...
│   └── postgres/
│       └── ...
├── services/
│   ├── __init__.py
│   ├── plan_service.py
│   ├── subscription_service.py
│   ├── feature_usage_service.py
│   └── features_catalog_service.py
├── enums/
│   ├── __init__.py
│   ├── subscription_status.py
│   ├── billing_period.py
│   └── feature_type.py
└── schemas/
    └── ...
```

### 5.2 Mover Código de Identity para Billing
- [ ] Mover modelos:
  - [ ] `Plan` → `billing/models/plan.py`
  - [ ] `Subscription` → `billing/models/subscription.py`
  - [ ] `Feature` → `billing/models/feature.py`
- [ ] Mover serviços:
  - [ ] `PlanService` → `billing/services/`
  - [ ] `SubscriptionService` → `billing/services/`
- [ ] Mover repositories
- [ ] Mover enums
- [ ] Atualizar imports em todo o projeto

### 5.3 Limpar Módulo Identity
- [ ] Manter apenas:
  - [ ] `Owner` (modelo)
  - [ ] `User` (modelo)
  - [ ] `OwnerService`
  - [ ] `UserService`
  - [ ] `AuthService` (se existir)

### 5.4 Atualizar Dependency Injection
- [ ] Atualizar `Container` para registrar novos serviços
- [ ] Registrar `FeaturesCatalogService`
- [ ] Registrar `FeatureUsageService`
- [ ] Atualizar dependências de `SubscriptionService`

---

## ✅ FASE 6: ATUALIZAR APIs/ENDPOINTS (2-3 dias)

### 6.1 Novos Endpoints de Feature Usage
```python
# GET /api/v1/features/usage
# Get usage summary for current tenant
- [ ] Implementar endpoint
- [ ] Testes

# GET /api/v1/features/{feature_key}/check
# Check if feature is available
- [ ] Implementar endpoint
- [ ] Testes

# POST /api/v1/admin/features/{feature_key}/override
# Admin override quota
- [ ] Implementar endpoint
- [ ] Testes (admin only)
```

### 6.2 Atualizar Endpoints Existentes

#### Subscriptions
```python
# POST /api/v1/subscriptions
# Atualizar para inicializar feature_usage
- [ ] Atualizar lógica
- [ ] Atualizar testes

# PUT /api/v1/subscriptions/{id}/upgrade
# Novo endpoint
- [ ] Implementar
- [ ] Testes

# PUT /api/v1/subscriptions/{id}/downgrade
# Novo endpoint
- [ ] Implementar
- [ ] Testes

# DELETE /api/v1/subscriptions/{id}
# Atualizar para suportar immediate vs scheduled
- [ ] Atualizar lógica
- [ ] Atualizar testes
```

### 6.3 Novos Endpoints Admin
```python
# GET /api/v1/admin/features/catalog
# List all features in catalog
- [ ] Implementar
- [ ] Testes

# POST /api/v1/admin/features/catalog
# Create new feature
- [ ] Implementar
- [ ] Testes

# GET /api/v1/admin/subscriptions/{id}/events
# Get event history
- [ ] Implementar
- [ ] Testes
```

---

## ✅ FASE 7: INTEGRAR COM CÓDIGO EXISTENTE (3-4 dias)

### 7.1 Pontos de Integração Críticos

#### WhatsApp Message Sending
```python
# Antes de enviar mensagem WhatsApp:
- [ ] Adicionar check de feature access
- [ ] Incrementar usage após envio bem-sucedido
- [ ] Tratar QuotaExceededError

Localização: src/modules/integrations/whatsapp/service.py (ou similar)
```

#### AI Response Generation
```python
# Antes de gerar resposta AI:
- [ ] Adicionar check de feature "ai_responses"
- [ ] Incrementar usage após geração
- [ ] Tratar QuotaExceededError

Localização: src/modules/ai/service.py (ou similar)
```

#### Project Creation
```python
# Antes de criar projeto:
- [ ] Adicionar check de feature "max_projects"
- [ ] Verificar se não excede o limite do plano

Localização: src/modules/projects/service.py (ou similar)
```

#### User Creation
```python
# Antes de criar usuário:
- [ ] Adicionar check de "max_users" do plano
- [ ] Bloquear se exceder

Localização: src/modules/identity/services/user_service.py
```

### 7.2 Adicionar Guards/Decorators
```python
# Criar decorator para automatic feature checking
- [ ] Implementar `@require_feature(feature_key, increment=True)`
- [ ] Exemplo:
@require_feature("whatsapp_messages", increment=True)
def send_whatsapp_message(owner_id: str, ...):
    ...
```

---

## ✅ FASE 8: TESTES (4-5 dias)

### 8.1 Unit Tests
- [ ] Todos os novos services (>80% coverage)
- [ ] Todos os novos repositories (>80% coverage)
- [ ] Funções helper SQL

### 8.2 Integration Tests
- [ ] Fluxo completo: subscription creation → feature initialization
- [ ] Fluxo completo: upgrade → quota increase
- [ ] Fluxo completo: downgrade → quota decrease → check overage
- [ ] Fluxo completo: cancellation → disable features
- [ ] Fluxo completo: usage increment → quota check → error

### 8.3 Load Tests
- [ ] `check_feature_access()` - 10k requests/second
- [ ] `increment_usage()` - 5k requests/second
- [ ] Concurrent increments (race conditions)

### 8.4 End-to-End Tests
- [ ] Usuário assina plano Free
- [ ] Usuário usa features até o limite
- [ ] Usuário tenta exceder limite (deve bloquear)
- [ ] Usuário faz upgrade para Pro
- [ ] Quota aumenta automaticamente
- [ ] Usuário pode usar novamente

---

## ✅ FASE 9: DOCUMENTAÇÃO (2-3 dias)

### 9.1 Documentação Técnica
- [ ] Architecture Decision Record (ADR) explicando refatoração
- [ ] Diagrama ER atualizado
- [ ] Diagrama de sequência para fluxos principais
- [ ] API documentation (Swagger/OpenAPI)

### 9.2 Documentação de Código
- [ ] Docstrings em todos os novos métodos
- [ ] Type hints completos
- [ ] Exemplos de uso em docstrings

### 9.3 Guias
- [ ] Guia para adicionar nova feature ao catálogo
- [ ] Guia para criar novo plano
- [ ] Guia para integrar feature checking em novos módulos
- [ ] Guia de troubleshooting

### 9.4 Changelog
- [ ] Documentar breaking changes
- [ ] Documentar novos recursos
- [ ] Migration guide para desenvolvedores

---

## ✅ FASE 10: DEPLOYMENT (2-3 dias)

### 10.1 Preparação
- [ ] Review final de código
- [ ] Merge de feature branch
- [ ] Tag de release: `v2.0.0-saas-multitenant`

### 10.2 Staging Deployment
- [ ] Deploy em staging
- [ ] Executar migration
- [ ] Smoke tests
- [ ] Performance tests
- [ ] Validar com dados de produção (anonimizados)

### 10.3 Production Deployment
- [ ] Maintenance window comunicado
- [ ] Backup final
- [ ] Deploy com feature flag (disabled)
- [ ] Executar migration
- [ ] Habilitar feature flag gradualmente (5% → 20% → 50% → 100%)
- [ ] Monitorar métricas:
  - [ ] Latência de `check_feature_access()`
  - [ ] Taxa de erro
  - [ ] CPU/Memory usage
  - [ ] Database connections

### 10.4 Rollback Plan
- [ ] Documentar passos de rollback
- [ ] Scripts de rollback prontos
- [ ] Definir critérios para rollback automático

---

## ✅ FASE 11: MONITORING & OBSERVABILITY (Contínuo)

### 11.1 Métricas
- [ ] Dashboard com:
  - [ ] Feature usage por tenant
  - [ ] Quota exceeded events
  - [ ] Subscription events (upgrades, cancellations)
  - [ ] API latency (check_feature_access, increment_usage)
  - [ ] Cache hit rate

### 11.2 Alertas
- [ ] Alert: Feature usage endpoint latency > 100ms
- [ ] Alert: Cache miss rate > 50%
- [ ] Alert: Spike in quota exceeded errors
- [ ] Alert: Database connection pool exhaustion

### 11.3 Logs
- [ ] Structured logging para todos os eventos importantes
- [ ] Log level configurável
- [ ] Correlation IDs para tracing

---

## 📊 PROGRESSO GERAL

### Resumo de Esforço
| Fase | Esforço | Status |
|------|---------|--------|
| 1. Preparação | 1-2 dias | ⬜ |
| 2. Database Migration | 2-3 dias | ⬜ |
| 3. Repositories | 2-3 dias | ⬜ |
| 4. Services | 4-5 dias | ⬜ |
| 5. Módulo Segregation | 2-3 dias | ⬜ |
| 6. APIs/Endpoints | 2-3 dias | ⬜ |
| 7. Integração | 3-4 dias | ⬜ |
| 8. Testes | 4-5 dias | ⬜ |
| 9. Documentação | 2-3 dias | ⬜ |
| 10. Deployment | 2-3 dias | ⬜ |
| 11. Monitoring | Contínuo | ⬜ |
| **TOTAL** | **24-34 dias** | **0%** |

### Prioridades
1. 🔴 **Crítico**: Fases 2, 4, 7 (Core functionality)
2. 🟡 **Importante**: Fases 3, 6, 8 (Quality & Integration)
3. 🟢 **Desejável**: Fases 5, 9, 10 (Organization & Docs)

### Riscos
| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Data loss durante migration | Baixa | Alto | Backups + dual-write + rollback plan |
| Performance degradation | Média | Médio | Load tests + caching + monitoring |
| Breaking changes em APIs | Alta | Médio | Feature flags + versioning + docs |
| Database deadlocks | Baixa | Alto | Transaction optimization + retry logic |

---

## 🎯 PRÓXIMOS PASSOS IMEDIATOS

1. **Revisar este checklist com o time** (30min)
2. **Aprovar arquitetura proposta** (1h)
3. **Criar tickets no board** (2h)
4. **Começar Fase 1: Preparação** (hoje)
5. **Executar Fase 2: Database Migration** (amanhã)

---

## 📝 NOTAS

- Use feature flags para deployments graduais
- Mantenha backward compatibility durante transição
- Priorize performance de `check_feature_access()` (cache agressivo)
- Considere usar Redis para feature access cache (TTL: 60s)
- Implemente circuit breakers para falhas de DB
- Adicione retries com exponential backoff
- Log tudo - você precisará para debugging

**Lembre-se**: Melhor fazer certo do que fazer rápido. Esta refatoração
estabelece a fundação para o crescimento do SaaS nos próximos anos.
