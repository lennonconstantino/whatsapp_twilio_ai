# Análise de Conformidade - Estados e Transições de Conversas

## Resumo Executivo

Após análise detalhada do código fornecido, identifiquei que **a implementação está parcialmente conforme** com o mapeamento de transições idealizado, mas existem **lacunas importantes** e **oportunidades de melhoria**.

---

## ✅ Pontos Positivos - O que está implementado corretamente

### 1. Estados Definidos Corretamente
**Arquivo**: `enums.py`

```python
class ConversationStatus(Enum):
    PENDING = "pending"
    PROGRESS = "progress"
    AGENT_CLOSED = "agent_closed"
    SUPPORT_CLOSED = "support_closed"
    USER_CLOSED = "user_closed"
    EXPIRED = "expired"
    FAILED = "failed"
    IDLE_TIMEOUT = "idle_timeout"
```

✅ **Conforme**: Todos os 8 estados estão definidos exatamente como no mapeamento.

✅ **Métodos auxiliares implementados**:
- `active_statuses()`: Retorna PENDING e PROGRESS
- `closed_statuses()`: Retorna todos os estados finais

### 2. Transições Básicas Implementadas

#### PENDING → PROGRESS
**Arquivo**: `conversation_service.py` (linhas 143-148)
```python
if conversation.status == ConversationStatus.PENDING.value:
    self.conversation_repo.update_status(
        conversation.conv_id,
        ConversationStatus.PROGRESS
    )
```
✅ **Implementado**: Quando primeira mensagem é adicionada à conversa

#### PENDING/PROGRESS → EXPIRED
**Arquivo**: `conversation_repository.py` (método `cleanup_expired_conversations`)
```python
def cleanup_expired_conversations(self, ...):
    # Busca conversas ativas com expires_at < now
    # Atualiza status para IDLE_TIMEOUT
```
✅ **Implementado**: Mas há um **problema** - está usando `IDLE_TIMEOUT` em vez de `EXPIRED`

#### PROGRESS → IDLE_TIMEOUT
**Arquivo**: `conversation_service.py` (método `process_idle_conversations`)
```python
def process_idle_conversations(self, idle_minutes, limit):
    idle = self.conversation_repo.find_idle_conversations(idle_minutes, limit)
    for conversation in idle:
        self.close_conversation(
            conversation,
            ConversationStatus.IDLE_TIMEOUT,
            reason=f"Idle timeout after {idle_minutes} minutes"
        )
```
✅ **Implementado**: Detecta inatividade e fecha com status IDLE_TIMEOUT

#### PROGRESS → USER_CLOSED / AGENT_CLOSED / SUPPORT_CLOSED
**Arquivo**: `conversation_service.py` + `conversation_repository.py`
```python
# Via detecção de intent de fechamento
def _check_closure_intent(self, conversation, message):
    result = self.closure_detector.detect_closure_intent(...)
    if result['should_close']:
        status = ConversationStatus(result['suggested_status'])
        self.close_conversation(conversation, status, ...)

# Via política de mensagem
def close_by_message_policy(self, conversation, should_close, message_owner, ...):
    # Determina closer_status baseado em message_owner
    if message_owner == MessageOwner.SUPPORT:
        closer_status = ConversationStatus.SUPPORT_CLOSED
    elif message_owner == MessageOwner.AGENT:
        closer_status = ConversationStatus.AGENT_CLOSED
```
✅ **Implementado**: Lógica inteligente para determinar o tipo de fechamento

### 3. Detecção de Intenção de Fechamento
**Arquivo**: `closure_detector.py`

✅ **Muito bem implementado**: Sistema sofisticado com:
- Análise de keywords
- Análise de padrões de mensagem
- Verificação de duração mínima
- Análise de contexto
- Score de confiança (0-1)
- Threshold de 60% para decidir fechamento

### 4. Gestão de Expiração
**Arquivo**: `domain.py` + repositórios

✅ **Bem implementado**:
- Campo `expires_at` no modelo
- Método `is_expired()` na entidade
- Lógica de cleanup de conversas expiradas
- Extensão de expiração

---

## ⚠️ Problemas e Não Conformidades

### 1. **CRÍTICO**: Confusão entre EXPIRED e IDLE_TIMEOUT

**Problema**: O método `cleanup_expired_conversations` está usando `IDLE_TIMEOUT` para conversas que expiraram por tempo:

```python
# conversation_repository.py - linha ~230
updated = self.update_status(
    conv.conv_id,
    ConversationStatus.IDLE_TIMEOUT,  # ❌ ERRADO!
    ended_at=datetime.now(timezone.utc)
)
```

**Deveria ser**:
```python
updated = self.update_status(
    conv.conv_id,
    ConversationStatus.EXPIRED,  # ✅ CORRETO!
    ended_at=datetime.now(timezone.utc)
)
```

**Impacto**: Conversas que atingem `expires_at` são marcadas como IDLE_TIMEOUT, quebrando a semântica dos estados.

---

### 2. **FALTANDO**: Transição IDLE_TIMEOUT → PROGRESS (Reativação)

**Mapeamento esperado**:
```
IDLE_TIMEOUT → PROGRESS (usuário ou agente envia nova mensagem)
```

**O que falta**: Não há lógica para reativar uma conversa que está em IDLE_TIMEOUT.

**Sugestão de implementação**:
```python
# No conversation_service.py, no método add_message:
def add_message(self, conversation, message_create):
    # Se conversa está em IDLE_TIMEOUT, reativar
    if conversation.status == ConversationStatus.IDLE_TIMEOUT.value:
        self.conversation_repo.update_status(
            conversation.conv_id,
            ConversationStatus.PROGRESS
        )
        conversation.status = ConversationStatus.PROGRESS
        logger.info(
            "Conversation reactivated from idle timeout",
            conv_id=conversation.conv_id
        )
    
    # Resto da lógica...
```

---

### 3. **FALTANDO**: Estado FAILED não tem implementação

**Observação**: O estado `FAILED` está definido no enum, mas não há:
- Lógica para transicionar para FAILED
- Tratamento de erros críticos que levam a FAILED
- Rollback ou recovery de conversas FAILED

**Quando usar FAILED**:
- Erro ao enviar mensagem via Twilio (após retries)
- Perda de conexão com banco de dados
- Falha crítica no processamento de mensagem
- Erro na API do WhatsApp

**Sugestão de implementação**:
```python
# No conversation_service.py
def _handle_critical_error(self, conversation, error, context):
    """Marca conversa como FAILED quando erro crítico ocorre."""
    logger.error(
        "Critical error in conversation",
        conv_id=conversation.conv_id,
        error=str(error),
        context=context
    )
    
    # Atualizar contexto com detalhes do erro
    ctx = conversation.context or {}
    ctx['failure_details'] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'error': str(error),
        'context': context
    }
    self.conversation_repo.update_context(conversation.conv_id, ctx)
    
    # Marcar como FAILED
    self.close_conversation(
        conversation,
        ConversationStatus.FAILED,
        reason=f"System failure: {str(error)[:100]}"
    )
```

---

### 4. **FALTANDO**: Validação de Transições

**Problema**: Não há validação se uma transição é válida.

Exemplo de transição inválida que poderia acontecer:
```python
# Isso não deveria ser permitido:
conversation.status = ConversationStatus.AGENT_CLOSED  # Estado final
# ... depois ...
conversation.status = ConversationStatus.PROGRESS  # ❌ Não pode voltar!
```

**Sugestão de implementação**:
```python
# No domain.py, adicionar ao modelo Conversation:
VALID_TRANSITIONS = {
    ConversationStatus.PENDING: [
        ConversationStatus.PROGRESS,
        ConversationStatus.EXPIRED,
        ConversationStatus.SUPPORT_CLOSED,
        ConversationStatus.USER_CLOSED,
        ConversationStatus.FAILED
    ],
    ConversationStatus.PROGRESS: [
        ConversationStatus.AGENT_CLOSED,
        ConversationStatus.SUPPORT_CLOSED,
        ConversationStatus.USER_CLOSED,
        ConversationStatus.IDLE_TIMEOUT,
        ConversationStatus.EXPIRED,
        ConversationStatus.FAILED
    ],
    ConversationStatus.IDLE_TIMEOUT: [
        ConversationStatus.PROGRESS,
        ConversationStatus.EXPIRED,
        ConversationStatus.AGENT_CLOSED,
        ConversationStatus.USER_CLOSED,
        ConversationStatus.FAILED
    ],
    # Estados finais não têm transições
    ConversationStatus.AGENT_CLOSED: [],
    ConversationStatus.SUPPORT_CLOSED: [],
    ConversationStatus.USER_CLOSED: [],
    ConversationStatus.EXPIRED: [],
    ConversationStatus.FAILED: []
}

def can_transition_to(self, new_status: ConversationStatus) -> bool:
    """Verifica se pode fazer transição para novo status."""
    current = ConversationStatus(self.status)
    valid = self.VALID_TRANSITIONS.get(current, [])
    return new_status in valid

def transition_to(self, new_status: ConversationStatus):
    """Faz transição validada para novo status."""
    if not self.can_transition_to(new_status):
        raise ValueError(
            f"Invalid transition from {self.status} to {new_status.value}"
        )
    self.status = new_status
```

---

### 5. **FALTANDO**: Transição PENDING → USER_CLOSED

**Cenário**: Usuário cancela/desiste antes do atendimento começar.

**O que falta**: No método `get_or_create_conversation`, não há tratamento para:
- Mensagem de cancelamento do usuário em PENDING
- Ação explícita de "cancelar solicitação"

**Sugestão**:
```python
# No closure_detector.py, adicionar detecção de cancelamento em PENDING
def detect_cancellation_in_pending(self, message, conversation):
    """Detecta se usuário quer cancelar conversa pendente."""
    if conversation.status != ConversationStatus.PENDING.value:
        return False
    
    cancel_keywords = ['cancelar', 'desistir', 'deixa pra lá', 'esquece']
    content = (message.body or message.content or "").lower()
    
    return any(kw in content for kw in cancel_keywords)
```

---

### 6. **INCONSISTÊNCIA**: Fechamento automático com alta confiança

**Arquivo**: `conversation_service.py` (linhas 176-184)

```python
# Se very high confidence (>= 0.8), close automatically
if result['confidence'] >= 0.8:
    status = ConversationStatus(result['suggested_status'])
    self.close_conversation(
        conversation,
        status,
        reason=f"Auto-closed: {', '.join(result['reasons'])}"
    )
```

**Problema**: Isso fecha a conversa **durante** `add_message`, mas depois chama `close_by_message_policy` novamente (linha após return True).

**Resultado**: Duplicação de lógica e possível confusão.

**Sugestão**: Unificar a lógica de fechamento em um único ponto.

---

### 7. **FALTANDO**: Notificações nas Transições

**Observação**: Não há sistema de notificações quando transições acontecem.

**O que falta**:
- Notificar agentes quando conversa entra em PENDING
- Alertar usuário quando conversa vai para IDLE_TIMEOUT
- Confirmar fechamento para usuário
- Alertar equipe técnica em caso de FAILED

**Sugestão**: Criar um `NotificationService` ou usar um sistema de eventos.

---

### 8. **MELHORIA**: Timers não são configuráveis por owner

**Observação**: Todos os timers vêm de `settings`:
- `expiration_minutes`
- `idle_timeout_minutes`
- `min_conversation_duration`

**Melhoria sugerida**: Permitir configuração por owner na tabela `features` ou em configurações específicas.

---

## 📋 Checklist de Conformidade

### Estados
- [x] PENDING definido
- [x] PROGRESS definido
- [x] AGENT_CLOSED definido
- [x] SUPPORT_CLOSED definido
- [x] USER_CLOSED definido
- [x] EXPIRED definido
- [x] FAILED definido
- [x] IDLE_TIMEOUT definido

### Transições Críticas
- [x] PENDING → PROGRESS
- [⚠️] PENDING → EXPIRED (implementado, mas usando IDLE_TIMEOUT)
- [ ] PENDING → SUPPORT_CLOSED (não implementado explicitamente)
- [ ] PENDING → USER_CLOSED (não implementado)
- [ ] PENDING → FAILED (não implementado)

- [x] PROGRESS → AGENT_CLOSED
- [x] PROGRESS → SUPPORT_CLOSED
- [x] PROGRESS → USER_CLOSED
- [x] PROGRESS → IDLE_TIMEOUT
- [⚠️] PROGRESS → EXPIRED (implementado, mas usando IDLE_TIMEOUT)
- [ ] PROGRESS → FAILED (não implementado)

- [ ] IDLE_TIMEOUT → PROGRESS (reativação não implementada)
- [ ] IDLE_TIMEOUT → EXPIRED (não implementado)
- [x] IDLE_TIMEOUT → AGENT_CLOSED
- [ ] IDLE_TIMEOUT → USER_CLOSED (não testado)
- [ ] IDLE_TIMEOUT → FAILED (não implementado)

### Funcionalidades
- [x] Detecção de intenção de fechamento
- [x] Gestão de expiração
- [x] Gestão de idle timeout
- [x] Atualização de timestamps
- [x] Extensão de expiração
- [ ] Validação de transições
- [ ] Notificações de transição
- [ ] Tratamento de erros críticos (FAILED)
- [ ] Reativação de conversas (IDLE_TIMEOUT → PROGRESS)
- [ ] Auditoria completa de transições

---

## 🎯 Recomendações Prioritárias

### Prioridade ALTA (Corrigir imediatamente)

1. **Corrigir uso de IDLE_TIMEOUT em cleanup_expired_conversations**
   - Usar `ConversationStatus.EXPIRED` quando `expires_at` é atingido
   - Reservar `IDLE_TIMEOUT` apenas para inatividade

2. **Implementar reativação de conversas**
   - Adicionar lógica IDLE_TIMEOUT → PROGRESS no `add_message`
   - Logar reativações para métricas

3. **Adicionar validação de transições**
   - Prevenir transições inválidas
   - Logar tentativas de transições inválidas

### Prioridade MÉDIA

4. **Implementar tratamento de FAILED**
   - Adicionar try/catch em operações críticas
   - Transicionar para FAILED em erros não recuperáveis

5. **Implementar cancelamento em PENDING**
   - Detectar intenção de cancelamento
   - Permitir PENDING → USER_CLOSED

6. **Adicionar auditoria de transições**
   - Criar tabela de histórico de transições
   - Registrar: timestamp, estado anterior, novo estado, usuário/sistema, motivo

### Prioridade BAIXA

7. **Sistema de notificações**
   - Notificar stakeholders em transições importantes

8. **Configuração por owner**
   - Permitir timers customizados por tenant

9. **Dashboard de métricas**
   - Visualizar distribuição de estados
   - Tempo médio em cada estado
   - Taxa de cada tipo de fechamento

---

## 📊 Métricas Sugeridas

Com a implementação correta, você poderá acompanhar:

```python
# Exemplo de queries para métricas
def get_conversation_metrics(owner_id, start_date, end_date):
    return {
        # Distribuição de estados finais
        'closure_distribution': {
            'agent_closed': count_by_status(AGENT_CLOSED),
            'support_closed': count_by_status(SUPPORT_CLOSED),
            'user_closed': count_by_status(USER_CLOSED),
            'expired': count_by_status(EXPIRED),
            'idle_timeout': count_by_status(IDLE_TIMEOUT),
            'failed': count_by_status(FAILED)
        },
        
        # Tempos médios
        'avg_time_pending': avg_duration(PENDING),
        'avg_time_progress': avg_duration(PROGRESS),
        'avg_total_duration': avg_total_duration(),
        
        # Taxas
        'first_response_time': avg_time_pending_to_progress(),
        'resolution_rate': percentage_closed_successfully(),
        'timeout_rate': percentage_timeouts(),
        'reactivation_rate': count_reactivations() / count_idle_timeouts()
    }
```

---

## 💡 Exemplo de Código Corrigido

### 1. Correção do cleanup_expired_conversations

```python
# conversation_repository.py
def cleanup_expired_conversations(self, owner_id=None, channel=None, phone=None):
    """Clean up conversations expired by timeout."""
    # ... validações ...
    
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        # ... query setup ...
        
        result = query.execute()
        
        expired_count = 0
        for item in result.data or []:
            conv = self.model_class(**item)
            if conv.conv_id and conv.is_expired():
                # ✅ CORRIGIDO: Usar EXPIRED em vez de IDLE_TIMEOUT
                updated = self.update_status(
                    conv.conv_id,
                    ConversationStatus.EXPIRED,  # ← CORRETO!
                    ended_at=datetime.now(timezone.utc)
                )
                if updated:
                    expired_count += 1
        
        if expired_count > 0:
            logger.info("Closed expired conversations", count=expired_count)
    except Exception as e:
        logger.error("Error during cleanup", error=str(e))
        raise
```

### 2. Implementação de Reativação

```python
# conversation_service.py
def add_message(self, conversation, message_create):
    """Add a message to the conversation."""
    
    # ✅ NOVO: Reativar se estava em IDLE_TIMEOUT
    if conversation.status == ConversationStatus.IDLE_TIMEOUT.value:
        self.conversation_repo.update_status(
            conversation.conv_id,
            ConversationStatus.PROGRESS
        )
        conversation.status = ConversationStatus.PROGRESS
        
        # Adicionar ao contexto
        context = conversation.context or {}
        context['reactivated_from_idle'] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'triggered_by': message_create.message_owner
        }
        self.conversation_repo.update_context(conversation.conv_id, context)
        
        logger.info(
            "Conversation reactivated from idle timeout",
            conv_id=conversation.conv_id
        )
    
    # Update conversation status to PROGRESS if it was PENDING
    if conversation.status == ConversationStatus.PENDING.value:
        # ... código existente ...
    
    # ... resto da lógica ...
```

### 3. Validação de Transições

```python
# conversation_repository.py
def update_status(self, conv_id, status, ended_at=None):
    """Update conversation status with validation."""
    
    # ✅ NOVO: Buscar conversa atual
    current_conv = self.find_by_id(conv_id, id_column="conv_id")
    if not current_conv:
        logger.error("Conversation not found", conv_id=conv_id)
        return None
    
    # ✅ NOVO: Validar transição
    current_status = ConversationStatus(current_conv.status)
    if not self._is_valid_transition(current_status, status):
        logger.warning(
            "Invalid status transition",
            conv_id=conv_id,
            from_status=current_status.value,
            to_status=status.value
        )
        # Opção 1: Lançar exceção
        # raise ValueError(f"Invalid transition from {current_status} to {status}")
        
        # Opção 2: Ignorar silenciosamente
        return current_conv
    
    # Continuar com update normal
    data = {"status": status.value}
    if ended_at:
        data["ended_at"] = ended_at.isoformat()
    
    return self.update(conv_id, data, id_column="conv_id")

def _is_valid_transition(self, from_status, to_status):
    """Check if transition is valid."""
    VALID_TRANSITIONS = {
        ConversationStatus.PENDING: [
            ConversationStatus.PROGRESS,
            ConversationStatus.EXPIRED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.FAILED
        ],
        ConversationStatus.PROGRESS: [
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.SUPPORT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.IDLE_TIMEOUT,
            ConversationStatus.EXPIRED,
            ConversationStatus.FAILED
        ],
        ConversationStatus.IDLE_TIMEOUT: [
            ConversationStatus.PROGRESS,
            ConversationStatus.EXPIRED,
            ConversationStatus.AGENT_CLOSED,
            ConversationStatus.USER_CLOSED,
            ConversationStatus.FAILED
        ],
        # Estados finais não podem transicionar
        ConversationStatus.AGENT_CLOSED: [],
        ConversationStatus.SUPPORT_CLOSED: [],
        ConversationStatus.USER_CLOSED: [],
        ConversationStatus.EXPIRED: [],
        ConversationStatus.FAILED: []
    }
    
    valid = VALID_TRANSITIONS.get(from_status, [])
    return to_status in valid
```

---

## 🎓 Conclusão

Seu código tem uma **base sólida** com os estados corretos e várias transições implementadas. No entanto, há **questões críticas** que precisam ser corrigidas:

1. ❌ Confusão entre EXPIRED e IDLE_TIMEOUT
2. ❌ Falta de reativação de conversas
3. ❌ Estado FAILED não implementado
4. ❌ Falta de validação de transições

Com as correções sugeridas, você terá um sistema robusto e totalmente conforme com o mapeamento de transições idealizado.

**Pontuação de conformidade**: 65/100
- Estados: 100%
- Transições principais: 70%
- Funcionalidades avançadas: 40%

Depois de implementar as correções de ALTA prioridade, a conformidade subirá para ~85%.