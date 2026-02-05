# Análise de Impacto: Remoção do X-Auth-ID

## Contexto Atual

O sistema possui **dois mecanismos de autenticação paralelos**:
1. **JWT (Bearer Token)**: Autenticação segura padrão
2. **X-Auth-ID**: Header customizado inseguro e "spoofable"

Esta duplicidade cria:
- ✅ **Vetor de ataque ativo** (IDOR confirmado em subscriptions)
- ✅ **Inconsistência arquitetural** (dois padrões coexistindo)
- ✅ **Violação de coesão** (lógica de segurança fragmentada)

---

## 🎯 Impacto da Remoção

### 1. **Impacto em Endpoints** 

#### 1.1 Endpoints Afetados (uso confirmado)
```python
# src/modules/identity/api/v1/subscriptions.py
# ⚠️ ALTO RISCO - IDOR ATIVO
POST   /api/v1/subscriptions/cancel
- Atualmente: X-Auth-ID (vulnerável)
- Necessário: Validação JWT + owner_id do token
```

#### 1.2 Análise de Vulnerabilidade Atual
```python
# CÓDIGO VULNERÁVEL ATUAL (subscriptions.py)
@router.post("/cancel")
async def cancel_subscription(request: Request):
    auth_id = request.headers.get("X-Auth-ID")  # ❌ Spoofable!
    # Falta validação de ownership
    # Qualquer auth_id pode cancelar qualquer subscription
```

**Exploração possível:**
```bash
# Atacante pode cancelar assinatura de outro usuário
curl -X POST /api/v1/subscriptions/cancel \
  -H "X-Auth-ID: victim_user_id" \
  -H "Content-Type: application/json"
```

### 2. **Impacto em Autenticação & Autorização**

#### 2.1 Fluxo Atual (Problemático)
```
User Request → X-Auth-ID Header → DB Query → Response
                     ↑
                 Sem validação!
```

#### 2.2 Fluxo Correto (Pós-remoção)
```
User Request → JWT Token → Validate & Decode → Extract owner_id → DB Query (filtered by owner) → Response
                              ↑
                     auth.uid() do Supabase
```

#### 2.3 Mudanças na Camada de Segurança

**Antes (Inseguro):**
```python
# Qualquer valor pode ser injetado
auth_id = request.headers.get("X-Auth-ID")
user = get_user_by_auth_id(auth_id)  # ❌ Confia no cliente
```

**Depois (Seguro):**
```python
# Token JWT validado pelo Supabase/Auth middleware
token = await get_current_user(request)  # ✅ Validado
owner_id = token.owner_id  # ✅ Extraído de fonte confiável
```

---

## 📊 Impacto por Camada

### **API Layer**
| Componente | Status Atual | Impacto | Ação Requerida |
|------------|--------------|---------|----------------|
| `subscriptions.py` | 🔴 Vulnerável | **CRÍTICO** | Refatorar para JWT + validação owner |
| `users.py` | 🟡 Misto | **MÉDIO** | Verificar e padronizar |
| `owners.py` | 🟡 Misto | **MÉDIO** | Verificar e padronizar |
| `plans.py` | 🟢 JWT? | **BAIXO** | Apenas verificação |

### **Service Layer**
| Serviço | Dependência X-Auth-ID | Impacto |
|---------|----------------------|---------|
| `SubscriptionService` | **SIM** | Adicionar parâmetro `owner_id` em métodos |
| `UserService` | Provável | Verificar `find_by_auth_id()` |
| `OwnerService` | Não | Sem impacto |
| `PlanService` | Não | Sem impacto |

### **Repository Layer**
| Repositório | Mudança Necessária |
|-------------|-------------------|
| `SubscriptionRepository` | Adicionar filtro `owner_id` em queries críticas |
| `UserRepository` | Manter `auth_id` (vem do JWT agora) |
| `OwnerRepository` | Sem mudança |

### **Database (RLS - Row Level Security)**
| Tabela | Status RLS | Compatibilidade JWT |
|--------|-----------|-------------------|
| `subscriptions` | ✅ Habilitado | ✅ Pronto (via `get_current_owner_id()`) |
| `users` | ✅ Habilitado | ✅ Pronto |
| `owners` | ✅ Habilitado | ✅ Pronto |
| `features` | ✅ Habilitado | ✅ Pronto |

**Observação importante:** O RLS do Supabase **JÁ ESTÁ CONFIGURADO** para usar `auth.uid()` que vem do JWT!

```sql
-- De 007_security_policies.sql
CREATE OR REPLACE FUNCTION app.get_current_owner_id()
RETURNS text AS $$
BEGIN
    RETURN (SELECT owner_id FROM app.users WHERE auth_id = auth.uid()::text LIMIT 1);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- As policies já usam JWT implicitamente via auth.uid()
CREATE POLICY "Users can view their subscription"
ON app.subscriptions FOR SELECT
USING (owner_id = get_current_owner_id());  -- ✅ Usa JWT!
```

---

## 🔧 Plano de Migração

### **Fase 1: Preparação (Sem Breaking Changes)**
```python
# Criar decorator unificado de autenticação
from functools import wraps
from fastapi import HTTPException, Request

async def get_authenticated_owner(request: Request) -> str:
    """
    Extrai owner_id do JWT token.
    Substitui X-Auth-ID de forma segura.
    """
    # Supabase já valida o JWT no middleware
    user = request.state.user  # Injetado pelo auth middleware
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # auth_id vem do JWT validado (auth.uid())
    auth_id = user.id
    
    # Buscar owner_id associado
    from src.modules.identity.services import UserService
    user_data = await user_service.get_user_by_auth_id(auth_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_data.owner_id
```

### **Fase 2: Refatoração de Endpoints**

#### Exemplo: Subscriptions
```python
# ANTES (Vulnerável)
@router.post("/cancel")
async def cancel_subscription(request: Request):
    auth_id = request.headers.get("X-Auth-ID")  # ❌
    # ...

# DEPOIS (Seguro)
@router.post("/cancel")
async def cancel_subscription(
    request: Request,
    owner_id: str = Depends(get_authenticated_owner)  # ✅ JWT validado
):
    # owner_id já vem validado do token
    result = await subscription_service.cancel_subscription(owner_id)
    # ...
```

### **Fase 3: Atualização de Services**

```python
# SubscriptionService - ANTES
class SubscriptionService:
    def cancel_subscription(self, auth_id: str):
        # ❌ auth_id vem do header não confiável
        user = self.user_repo.find_by_auth_id(auth_id)
        # ...

# SubscriptionService - DEPOIS
class SubscriptionService:
    def cancel_subscription(self, owner_id: str):
        # ✅ owner_id vem do JWT validado
        subscription = self.repo.find_by_owner(owner_id)
        # ...
```

### **Fase 4: Testes de Segurança**
```python
# test_subscription_security.py
def test_cannot_cancel_other_user_subscription():
    """IDOR prevention test"""
    # User A tenta cancelar subscription do User B
    token_user_a = create_jwt(user_id="user_a", owner_id="owner_a")
    
    response = client.post(
        "/api/v1/subscriptions/cancel",
        headers={"Authorization": f"Bearer {token_user_a}"}
    )
    
    # Deve falhar se tentar acessar owner_b
    assert response.status_code == 403  # ✅ Bloqueado
```

---

## 📈 Benefícios da Remoção

### **Segurança**
- ✅ **Elimina IDOR crítico** em subscriptions
- ✅ **Remove vetor de spoofing** via header manipulation
- ✅ **Uniformiza autenticação** (100% JWT)
- ✅ **Compatível com RLS do Supabase** (já configurado)

### **Arquitetura**
- ✅ **Coesão alta**: Um único padrão de autenticação
- ✅ **Código limpo**: Remove lógica duplicada
- ✅ **Manutenibilidade**: Menos pontos de falha
- ✅ **Conformidade**: Alinha com boas práticas (OWASP)

### **Operacional**
- ✅ **Auditoria**: JWT logs são rastreáveis
- ✅ **Conformidade LGPD/GDPR**: auth_id confiável para logs
- ✅ **Escalabilidade**: Stateless (JWT nativo)

---

## ⚠️ Riscos e Mitigações

### **Risco 1: Breaking Changes em Clientes**
**Impacto:** Clientes que usam X-Auth-ID vão quebrar

**Mitigação:**
```python
# Período de transição: Suportar ambos (30 dias)
async def get_owner_id_transitional(request: Request) -> str:
    # Prioridade 1: JWT (novo padrão)
    try:
        return await get_authenticated_owner(request)
    except:
        # Fallback temporário: X-Auth-ID (com warning)
        auth_id = request.headers.get("X-Auth-ID")
        logger.warning(f"DEPRECATED: X-Auth-ID used by {auth_id}")
        # ... validação extra
        return resolve_owner_from_auth_id(auth_id)
```

### **Risco 2: Bugs em Produção**
**Impacto:** Erros durante migração podem afetar usuários

**Mitigação:**
1. **Deploy gradual**: Feature flag para nova auth
2. **Rollback plan**: Manter código antigo comentado por 1 sprint
3. **Monitoring**: Alertas de 401/403 incomuns

### **Risco 3: Performance do JWT Decode**
**Impacto:** Overhead de validação de token

**Mitigação:**
- Supabase já faz isso no middleware (sem impacto adicional)
- Cache de `owner_id` em Redis (se necessário)

---

## 📋 Checklist de Implementação

### **Pré-requisitos**
- [ ] Confirmar que Supabase Auth está 100% funcional
- [ ] Mapear TODOS os endpoints que usam X-Auth-ID
- [ ] Criar testes de segurança (IDOR, spoofing)

### **Desenvolvimento**
- [ ] Criar `get_authenticated_owner()` dependency
- [ ] Refatorar `subscriptions.py` (PRIORIDADE 1 - IDOR ativo)
- [ ] Refatorar demais endpoints identificados
- [ ] Atualizar services para receber `owner_id`
- [ ] Adicionar validação de ownership em queries críticas

### **Testes**
- [ ] Testes unitários de autenticação
- [ ] Testes de integração por endpoint
- [ ] Testes de segurança (IDOR, privilege escalation)
- [ ] Testes de performance (overhead JWT)

### **Deploy**
- [ ] Feature flag: `USE_JWT_ONLY=false` (default)
- [ ] Deploy em staging
- [ ] Testes E2E em staging
- [ ] Comunicar mudança para clientes (se houver API externa)
- [ ] Deploy em produção com flag ativada
- [ ] Monitorar por 7 dias
- [ ] Remover código legado de X-Auth-ID

### **Pós-Deploy**
- [ ] Remover feature flag
- [ ] Atualizar documentação da API
- [ ] Code review de segurança
- [ ] Penetration test (se possível)

---

## 🎯 Conclusão

### **Recomendação: REMOVER X-Auth-ID IMEDIATAMENTE**

**Justificativa:**
1. **IDOR crítico confirmado** em subscriptions (CVE potencial)
2. **Arquitetura comprometida** (dois padrões conflitantes)
3. **Risco baixo de migração** (RLS já usa JWT via `auth.uid()`)
4. **ROI alto**: Segurança + Código limpo + Conformidade

### **Timeline Sugerido**
| Fase | Duração | Objetivo |
|------|---------|----------|
| 1. Preparação | 2 dias | Criar utilitários JWT + testes |
| 2. Refatoração | 3 dias | Migrar endpoints (começar por subscriptions) |
| 3. Testes | 2 dias | Segurança + integração |
| 4. Deploy Staging | 1 dia | Validação E2E |
| 5. Deploy Produção | 1 dia | Com feature flag |
| 6. Monitoramento | 7 dias | Observar logs/alertas |
| **TOTAL** | **16 dias** | **IDOR eliminado** |

### **Próximos Passos Imediatos**

1. **URGENTE**: Desabilitar endpoint `POST /subscriptions/cancel` até correção
2. **Criar branch**: `security/remove-x-auth-id`
3. **Priorizar**: Subscriptions → Users → Owners → Features
4. **Comunicar**: Time de segurança + stakeholders

---

## 📚 Referências

- [OWASP API Security Top 10 - Broken Object Level Authorization](https://owasp.org/www-project-api-security/)
- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- Arquivo: `007_security_policies.sql` (RLS policies configuradas)
- Arquivo: `003_create_tables.sql` (Schema database)