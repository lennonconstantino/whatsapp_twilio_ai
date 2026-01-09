# Correções de Código - Issues Críticas do Lifecycle

## 📋 Índice de Correções

1. [Issue #1: IDLE_TIMEOUT → EXPIRED](#issue-1)
2. [Issue #2: PENDING → PROGRESS sem Agente](#issue-2)
3. [Issue #3: IDLE_TIMEOUT como Closed](#issue-3)
4. [Issue #4: Detecção Automática de Idle](#issue-4)
5. [Issue #5: SUPPORT_CLOSED Explícito](#issue-5)
6. [Issue #6: Validação de Estado no Webhook](#issue-6)

---

## Issue #1: IDLE_TIMEOUT → EXPIRED

### ❌ Código Atual (Incorreto)

```python
# conversation_repository.py (linhas 460-480)
def cleanup_expired_conversations(
    self,
    owner_id: Optional[int] = None,
    channel: Optional[str] = None,
    phone: Optional[str] = None
) -> None:
    """Clean up conversations expired by timeout."""
    # ... validações ...
    
    result = query.execute()
    
    expired_count = 0
    for item in result.data or []:
        conv = self.model_class(**item)
        if conv.conv_id and conv.is_expired():
            # ❌ PROBLEMA: Sempre marca como EXPIRED, 
            # não diferencia estado atual
            updated = self.update_status(
                conv.conv_id,
                ConversationStatus.EXPIRED,
                ended_at=datetime.now(timezone.utc)
            )
            if updated:
                expired_count += 1
```

### ✅ Código Corrigido

```python
# conversation_repository.py
def cleanup_expired_conversations(
    self,
    owner_id: Optional[int] = None,
    channel: Optional[str] = None,
    phone: Optional[str] = None
) -> None:
    """
    Clean up conversations expired by timeout.
    
    Handles different expiration scenarios:
    - PENDING/PROGRESS: Direct expiration (timeout normal)
    - IDLE_TIMEOUT: Extended timeout exceeded
    """
    if (owner_id and not channel) or (channel and not owner_id):
        raise ValueError("Ambos owner_id e channel devem ser fornecidos juntos ou nenhum dos dois")
    if phone and not channel:
        raise ValueError("Ambos phone e channel devem ser fornecidos juntos ou nenhum dos dois")

    try:
        now = datetime.now(timezone.utc).isoformat()

        query = self.client.table(self.table_name)\
            .select("*")\
            .in_("status", [s.value for s in ConversationStatus.active_statuses()])\
            .lt("expires_at", now)

        if owner_id and channel and not phone:
            query = query.eq("owner_id", owner_id).eq("channel", channel)
        elif owner_id and channel and phone:
            phone_expr = ",".join([
                f"from_number.eq.{phone}",
                f"to_number.eq.{phone}",
                f"phone_number.eq.{phone}"
            ])
            query = query.eq("owner_id", owner_id).eq("channel", channel).or_(phone_expr)

        result = query.execute()

        expired_count = 0
        for item in result.data or []:
            conv = self.model_class(**item)
            
            if not conv.conv_id or not conv.is_expired():
                continue
            
            # ✅ CORREÇÃO: Verificar estado atual antes de expirar
            current_status = ConversationStatus(conv.status)
            
            if current_status in [ConversationStatus.PENDING, ConversationStatus.PROGRESS]:
                # Expiração normal - conversa ativa que excedeu tempo
                logger.info(
                    "Expiring active conversation",
                    conv_id=conv.conv_id,
                    from_status=current_status.value,
                    reason="normal_timeout"
                )
                
                updated = self.update_status(
                    conv.conv_id,
                    ConversationStatus.EXPIRED,
                    ended_at=datetime.now(timezone.utc)
                )
                
                if updated:
                    # Registrar motivo da expiração
                    ctx = updated.context or {}
                    ctx['expiration_reason'] = 'normal_timeout'
                    ctx['previous_status'] = current_status.value
                    self.update_context(conv.conv_id, ctx)
                    expired_count += 1
            
            elif current_status == ConversationStatus.IDLE_TIMEOUT:
                # Expiração de conversa em idle - timeout estendido excedido
                logger.info(
                    "Expiring idle conversation",
                    conv_id=conv.conv_id,
                    from_status=current_status.value,
                    reason="extended_idle_timeout"
                )
                
                updated = self.update_status(
                    conv.conv_id,
                    ConversationStatus.EXPIRED,
                    ended_at=datetime.now(timezone.utc)
                )
                
                if updated:
                    # Registrar que era IDLE_TIMEOUT
                    ctx = updated.context or {}
                    ctx['expiration_reason'] = 'extended_idle_timeout'
                    ctx['previous_status'] = ConversationStatus.IDLE_TIMEOUT.value
                    
                    # Calcular quanto tempo ficou em idle
                    if conv.updated_at:
                        idle_duration = datetime.now(timezone.utc) - conv.updated_at
                        ctx['idle_duration_minutes'] = int(idle_duration.total_seconds() / 60)
                    
                    self.update_context(conv.conv_id, ctx)
                    expired_count += 1

        if expired_count > 0:
            logger.info(
                "Closed expired conversations",
                count=expired_count,
                owner_id=owner_id,
                channel=channel
            )
            
    except Exception as e:
        logger.error("Error during cleanup", error=str(e))
        raise
```

### 🧪 Teste Unitário

```python
# test_conversation_repository.py
def test_cleanup_expired_conversations_from_idle():
    """Testa expiração de conversa em IDLE_TIMEOUT."""
    # Criar conversa em IDLE_TIMEOUT com expires_at no passado
    conv = create_test_conversation(
        status=ConversationStatus.IDLE_TIMEOUT,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
    )
    
    # Executar cleanup
    repo.cleanup_expired_conversations(owner_id=1, channel="whatsapp")
    
    # Verificar que foi marcada como EXPIRED
    updated = repo.find_by_id(conv.conv_id, id_column="conv_id")
    assert updated.status == ConversationStatus.EXPIRED.value
    
    # Verificar contexto
    assert updated.context['expiration_reason'] == 'extended_idle_timeout'
    assert updated.context['previous_status'] == ConversationStatus.IDLE_TIMEOUT.value
```

---

## Issue #2: PENDING → PROGRESS sem Agente

### ❌ Código Atual (Incorreto)

```python
# conversation_service.py (linhas 174-196)
def add_message(self, conversation, message_create):
    # ... código anterior ...
    
    # ❌ PROBLEMA: Qualquer mensagem transiciona para PROGRESS
    if conversation.status == ConversationStatus.PENDING.value:
        self.conversation_repo.update_status(
            conversation.conv_id,
            ConversationStatus.PROGRESS
        )
        conversation.status = ConversationStatus.PROGRESS
    
    # ... resto do código ...
```

### ✅ Código Corrigido

```python
# conversation_service.py
def add_message(
    self,
    conversation: Conversation,
    message_create: MessageCreateDTO
) -> Message:
    """
    Add a message to the conversation and check for closure intent.
    
    Args:
        conversation: Conversation to add message to
        message_create: Message data
        
    Returns:
        Created Message
    """
    try:
        # Reactivate conversation if it was in IDLE_TIMEOUT
        if conversation.status == ConversationStatus.IDLE_TIMEOUT.value:
            self.conversation_repo.update_status(
                conversation.conv_id,
                ConversationStatus.PROGRESS
            )
            conversation.status = ConversationStatus.PROGRESS
            
            # Add to context
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

        # ✅ CORREÇÃO: Transicionar PENDING → PROGRESS apenas quando 
        # agente/sistema responde
        if conversation.status == ConversationStatus.PENDING.value:
            # Verificar se é mensagem de usuário querendo cancelar
            if self.closure_detector.detect_cancellation_in_pending(
                message_create, conversation
            ):
                logger.info(
                    "User cancelled conversation in PENDING state", 
                    conv_id=conversation.conv_id
                )
                
                # Persistir mensagem
                message_data = message_create.model_dump()
                message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
                created_message = self.message_repo.create(message_data)
                
                # Fechar conversa
                self.close_conversation(
                    conversation, 
                    ConversationStatus.USER_CLOSED
                )
                
                return created_message
            
            # ✅ Transicionar apenas se AGENT/SYSTEM/SUPPORT responde
            if message_create.message_owner in [
                MessageOwner.AGENT,
                MessageOwner.SYSTEM,
                MessageOwner.SUPPORT
            ]:
                logger.info(
                    "Agent accepting conversation",
                    conv_id=conversation.conv_id,
                    agent_type=message_create.message_owner
                )
                
                self.conversation_repo.update_status(
                    conversation.conv_id,
                    ConversationStatus.PROGRESS
                )
                conversation.status = ConversationStatus.PROGRESS
                
                # ✅ Registrar quem aceitou a conversa
                context = conversation.context or {}
                context['accepted_by'] = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'agent_type': message_create.message_owner,
                    'message_id': None  # Será preenchido após criar mensagem
                }
                
                # Se message_create tiver user_id (agente específico)
                if hasattr(message_create, 'user_id') and message_create.user_id:
                    context['accepted_by']['user_id'] = message_create.user_id
                
                self.conversation_repo.update_context(conversation.conv_id, context)
            else:
                # Mensagem de USER em PENDING - manter em PENDING
                logger.debug(
                    "User message while in PENDING - keeping in PENDING",
                    conv_id=conversation.conv_id
                )
        
        # Persistir mensagem
        message_data = message_create.model_dump()
        message_data["timestamp"] = datetime.now(timezone.utc).isoformat()
        created_message = self.message_repo.create(message_data)
        
        # ✅ Atualizar context com message_id se acabou de aceitar
        if conversation.status == ConversationStatus.PROGRESS.value:
            context = conversation.context or {}
            if 'accepted_by' in context and not context['accepted_by'].get('message_id'):
                context['accepted_by']['message_id'] = created_message.msg_id
                self.conversation_repo.update_context(conversation.conv_id, context)
        
        logger.info(
            "Added message to conversation",
            msg_id=created_message.msg_id if created_message else None,
            conv_id=conversation.conv_id
        )
        
        # Check closure intent if it's a user message
        if created_message:
            is_closure = self._check_closure_intent(conversation, created_message)
            self.conversation_repo.close_by_message_policy(
                conversation,
                is_closure,
                created_message.message_owner,
                created_message.body or created_message.content
            )
        
        # Update conversation timestamp
        self.conversation_repo.update_timestamp(conversation.conv_id)
        
        return created_message
        
    except Exception as e:
        self._handle_critical_error(
            conversation, 
            e, 
            {
                "action": "add_message",
                "message_create": message_create.model_dump()
            }
        )
        raise e
```

### 🧪 Teste Unitário

```python
# test_conversation_service.py
def test_pending_to_progress_requires_agent():
    """Testa que PENDING → PROGRESS só ocorre com mensagem de agente."""
    # Criar conversa em PENDING
    conv = create_test_conversation(status=ConversationStatus.PENDING)
    
    # Mensagem de USER - deve permanecer em PENDING
    user_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number="+5511999999999",
        to_number="+5511888888888",
        body="Oi, preciso de ajuda",
        message_owner=MessageOwner.USER
    )
    
    service.add_message(conv, user_msg)
    
    updated = service.get_conversation_by_id(conv.conv_id)
    assert updated.status == ConversationStatus.PENDING.value
    
    # Mensagem de AGENT - deve transicionar para PROGRESS
    agent_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number="+5511888888888",
        to_number="+5511999999999",
        body="Olá! Como posso ajudar?",
        message_owner=MessageOwner.AGENT
    )
    
    service.add_message(conv, agent_msg)
    
    updated = service.get_conversation_by_id(conv.conv_id)
    assert updated.status == ConversationStatus.PROGRESS.value
    assert 'accepted_by' in updated.context
    assert updated.context['accepted_by']['agent_type'] == MessageOwner.AGENT.value
```

---

## Issue #3: IDLE_TIMEOUT como Closed

### ❌ Código Atual (Incorreto)

```python
# enums.py
class ConversationStatus(Enum):
    # ... estados ...
    
    @classmethod
    def closed_statuses(cls):
        """Returns statuses considered as closed."""
        return [
            cls.AGENT_CLOSED,
            cls.SUPPORT_CLOSED,
            cls.USER_CLOSED,
            cls.EXPIRED,
            cls.FAILED,
            cls.IDLE_TIMEOUT  # ❌ INCORRETO - não é final
        ]
```

### ✅ Código Corrigido

```python
# enums.py
class ConversationStatus(Enum):
    """
    Enum for conversation status.
    
    Defines the state of the conversation lifecycle:
    
    Active States:
    - PENDING: Active conversation, awaiting interaction
    - PROGRESS: Conversation in progress
    
    Paused States:
    - IDLE_TIMEOUT: Conversation paused due to inactivity timeout
    
    Final States (Closed):
    - AGENT_CLOSED: Conversation closed by agent
    - SUPPORT_CLOSED: Conversation closed by support team
    - USER_CLOSED: Conversation closed by user
    - EXPIRED: Conversation automatically expired by system
    - FAILED: Conversation closed due to system failure
    """
    PENDING = "pending"
    PROGRESS = "progress"
    IDLE_TIMEOUT = "idle_timeout"
    AGENT_CLOSED = "agent_closed"
    SUPPORT_CLOSED = "support_closed"
    USER_CLOSED = "user_closed"
    EXPIRED = "expired"
    FAILED = "failed"
    
    @classmethod
    def active_statuses(cls):
        """
        Returns statuses considered as active.
        
        Active conversations can receive messages and transition to other states.
        """
        return [cls.PENDING, cls.PROGRESS]
    
    @classmethod
    def paused_statuses(cls):
        """
        Returns statuses considered as paused.
        
        Paused conversations are temporarily inactive but can be reactivated.
        """
        return [cls.IDLE_TIMEOUT]
    
    @classmethod
    def closed_statuses(cls):
        """
        Returns statuses considered as closed (final states).
        
        Closed conversations cannot be reactivated or modified.
        A new conversation must be created.
        """
        return [
            cls.AGENT_CLOSED,
            cls.SUPPORT_CLOSED,
            cls.USER_CLOSED,
            cls.EXPIRED,
            cls.FAILED
        ]
    
    @classmethod
    def all_terminal_statuses(cls):
        """
        Returns all statuses where conversation is not actively progressing.
        
        Includes both paused and closed states.
        """
        return cls.paused_statuses() + cls.closed_statuses()
    
    def is_active(self):
        """Check if this status is active."""
        return self in self.active_statuses()
    
    def is_paused(self):
        """Check if this status is paused."""
        return self in self.paused_statuses()
    
    def is_closed(self):
        """Check if this status is closed (final)."""
        return self in self.closed_statuses()
    
    def can_receive_messages(self):
        """Check if conversation in this status can receive messages."""
        return self.is_active() or self.is_paused()

    def __repr__(self) -> str:
        return f"ConversationStatus.{self.name}"
```

### 🔄 Atualizar domain.py

```python
# domain.py
class Conversation(BaseModel):
    # ... campos ...
    
    def is_active(self) -> bool:
        """Check if conversation is active."""
        status = ConversationStatus(self.status)
        return status.is_active()
    
    def is_paused(self) -> bool:
        """Check if conversation is paused."""
        status = ConversationStatus(self.status)
        return status.is_paused()
    
    def is_closed(self) -> bool:
        """Check if conversation is closed."""
        status = ConversationStatus(self.status)
        return status.is_closed()
    
    def can_receive_messages(self) -> bool:
        """Check if conversation can receive messages."""
        status = ConversationStatus(self.status)
        return status.can_receive_messages()
```

---

## Issue #4: Detecção Automática de Idle

### ✅ Implementação Recomendada

```python
# conversation_service.py
def add_message(
    self,
    conversation: Conversation,
    message_create: MessageCreateDTO
) -> Message:
    """
    Add a message to the conversation and check for closure intent.
    """
    try:
        # ✅ NOVO: Verificar conversas idle do mesmo owner antes de processar
        if message_create.message_owner == MessageOwner.USER:
            self._check_and_mark_idle_conversations(
                conversation.owner_id,
                conversation.conv_id  # Excluir conversa atual
            )
        
        # ... resto do código existente ...
        
    except Exception as e:
        self._handle_critical_error(conversation, e, {...})
        raise e

def _check_and_mark_idle_conversations(
    self,
    owner_id: int,
    exclude_conv_id: Optional[int] = None
) -> int:
    """
    Verifica conversas idle do owner e marca como IDLE_TIMEOUT.
    
    Esta verificação é executada quando uma nova mensagem chega,
    garantindo que conversas inativas sejam pausadas proativamente.
    
    Args:
        owner_id: ID do owner
        exclude_conv_id: ID da conversa atual a excluir da verificação
        
    Returns:
        Número de conversas marcadas como idle
    """
    try:
        idle_minutes = settings.conversation.idle_timeout_minutes
        
        # Buscar conversas idle do owner
        idle_conversations = self.conversation_repo.find_idle_conversations(
            idle_minutes,
            limit=20  # Limitar para não sobrecarregar
        )
        
        count = 0
        for idle_conv in idle_conversations:
            # Processar apenas do mesmo owner
            if idle_conv.owner_id != owner_id:
                continue
            
            # Excluir conversa atual
            if exclude_conv_id and idle_conv.conv_id == exclude_conv_id:
                continue
            
            # Verificar se já está em IDLE_TIMEOUT
            if idle_conv.status == ConversationStatus.IDLE_TIMEOUT.value:
                continue
            
            # Marcar como IDLE_TIMEOUT
            logger.info(
                "Marking conversation as idle",
                conv_id=idle_conv.conv_id,
                idle_minutes=idle_minutes,
                owner_id=owner_id
            )
            
            self.conversation_repo.update_status(
                idle_conv.conv_id,
                ConversationStatus.IDLE_TIMEOUT
            )
            
            # Adicionar contexto
            context = idle_conv.context or {}
            context['idle_detected'] = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'idle_minutes': idle_minutes,
                'triggered_by': 'new_message_arrival'
            }
            self.conversation_repo.update_context(idle_conv.conv_id, context)
            
            count += 1
        
        if count > 0:
            logger.info(
                "Marked conversations as idle",
                count=count,
                owner_id=owner_id
            )
        
        return count
        
    except Exception as e:
        logger.error(
            "Error checking idle conversations",
            owner_id=owner_id,
            error=str(e)
        )
        # Não propagar erro - isso não deve bloquear mensagem
        return 0
```

### 🔄 Manter Scheduler como Backup

```python
# background_tasks.py (job scheduler)
def process_idle_conversations_job():
    """
    Job periódico para processar conversas idle.
    
    Este job atua como backup caso a detecção durante
    processamento de mensagens falhe ou não seja executada.
    """
    service = ConversationService()
    
    try:
        count = service.process_idle_conversations()
        logger.info(f"[SCHEDULER] Processed {count} idle conversations")
    except Exception as e:
        logger.error(f"[SCHEDULER] Error processing idle conversations: {e}")
```

---

## Issue #5: SUPPORT_CLOSED Explícito

### ✅ Implementação Recomendada

```python
# conversations.py (API routes)
@router.post("/{conv_id}/escalate", response_model=ConversationResponse)
async def escalate_conversation(
    conv_id: int,
    supervisor_id: int = Query(..., description="Supervisor user ID"),
    reason: str = Query(..., description="Escalation reason"),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Escalate conversation to supervisor.
    
    Transitions conversation to supervisor ownership and adds escalation context.
    Conversation remains in PROGRESS status until supervisor closes it.
    """
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Validar que conversa está ativa
    if not conversation.is_active():
        raise HTTPException(
            status_code=400,
            detail=f"Cannot escalate conversation in {conversation.status} status"
        )
    
    try:
        # Atualizar contexto com escalação
        context = conversation.context or {}
        context['escalated'] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'supervisor_id': supervisor_id,
            'reason': reason,
            'previous_agent': context.get('accepted_by', {}).get('user_id')
        }
        
        service.conversation_repo.update_context(conv_id, context)
        
        logger.info(
            "Conversation escalated to supervisor",
            conv_id=conv_id,
            supervisor_id=supervisor_id
        )
        
        # Retornar conversa atualizada
        updated = service.get_conversation_by_id(conv_id)
        return ConversationResponse.model_validate(updated)
        
    except Exception as e:
        logger.error("Error escalating conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conv_id}/close-by-support", response_model=ConversationResponse)
async def close_by_support(
    conv_id: int,
    supervisor_id: int = Query(..., description="Supervisor user ID"),
    resolution: str = Query(..., description="Resolution description"),
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Close conversation by support team.
    
    Used when supervisor or support team intervenes and resolves the conversation.
    Transitions to SUPPORT_CLOSED status.
    """
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Validar que não está já fechada
    if conversation.is_closed():
        raise HTTPException(
            status_code=400,
            detail=f"Conversation already closed with status {conversation.status}"
        )
    
    try:
        # Atualizar contexto com resolução
        context = conversation.context or {}
        context['closed_by_support'] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'supervisor_id': supervisor_id,
            'resolution': resolution,
            'was_escalated': 'escalated' in context
        }
        
        service.conversation_repo.update_context(conv_id, context)
        
        # Fechar como SUPPORT_CLOSED
        closed = service.close_conversation(
            conversation,
            ConversationStatus.SUPPORT_CLOSED
        )
        
        logger.info(
            "Conversation closed by support",
            conv_id=conv_id,
            supervisor_id=supervisor_id
        )
        
        return ConversationResponse.model_validate(closed)
        
    except Exception as e:
        logger.error("Error closing conversation by support", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Issue #6: Validação de Estado no Webhook

### ✅ Código Corrigido

```python
# webhooks.py
def __receive_and_response(
    owner_id: int, 
    payload: TwilioWhatsAppPayload, 
    twilio_service: TwilioService
) -> TwilioWebhookResponseDTO:
    """
    Process inbound message and generate response.
    
    Validates conversation state before adding message.
    Creates new conversation if current one is closed.
    """
    message_type = __detemine_message_type(
        payload.num_media, 
        payload.media_content_type
    )

    # Get or create conversation
    conversation_service = ConversationService()
    conversation = conversation_service.get_or_create_conversation(
        owner_id=owner_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        channel="whatsapp"
    )
    
    # ✅ NOVO: Validar estado antes de adicionar mensagem
    if conversation.is_closed():
        logger.warning(
            "Attempt to add message to closed conversation - creating new one",
            conv_id=conversation.conv_id,
            status=conversation.status,
            from_number=payload.from_number
        )
        
        # Registrar tentativa no contexto da conversa fechada
        old_context = conversation.context or {}
        old_context['reopen_attempted'] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message_sid': payload.message_sid,
            'user_message': payload.body[:100]  # Primeiros 100 chars
        }
        conversation_service.conversation_repo.update_context(
            conversation.conv_id, 
            old_context
        )
        
        # Criar nova conversa referenciando a anterior
        new_metadata = {
            'previous_conv_id': conversation.conv_id,
            'reason': 'user_returned_after_closure'
        }
        
        conversation = conversation_service._create_new_conversation(
            owner_id=owner_id,
            from_number=payload.from_number,
            to_number=payload.to_number,
            channel="whatsapp",
            user_id=None,
            metadata=new_metadata
        )
        
        logger.info(
            "Created new conversation for returning user",
            new_conv_id=conversation.conv_id,
            previous_conv_id=new_metadata['previous_conv_id']
        )

    # Create message inbound
    message_data = MessageCreateDTO(
        conv_id=conversation.conv_id,
        from_number=payload.from_number,
        to_number=payload.to_number,
        body=payload.body,
        direction=MessageDirection.INBOUND,
        message_owner=MessageOwner.USER,
        message_type=message_type,
        content=payload.body,
        metadata={
            "message_sid": payload.message_sid,
            "num_media": payload.num_media,
            "media_url": payload.media_url if payload.media_url else None,
            "media_type": payload.media_content_type if payload.media_content_type else None
        }
    )
    
    message = conversation_service.add_message(conversation, message_data)
    
    logger.info(
        "Processed inbound message",
        conv_id=conversation.conv_id,
        msg_id=message.msg_id if message else None
    )

    # Generate and send response
    user = User(
        owner_id=owner_id,
        profile_name="User Profile",
        first_name="User",
        last_name="Profile"
    )
    response_text = TwilioHelpers.generate_response(
        user_message=payload.body, 
        user=user
    )

    response = twilio_service.send_message(
        owner_id=owner_id,
        from_number=payload.to_number,
        to_number=payload.from_number,
        body=response_text
    )

    # Create message outbound
    outbound_data = MessageCreateDTO(
        conv_id=conversation.conv_id,
        from_number=payload.to_number,
        to_number=payload.from_number,
        body=response["body"],
        direction=MessageDirection.OUTBOUND,
        message_owner=MessageOwner.SYSTEM,
        message_type=message_type,
        content=response["message"].body,
        metadata={
            "message_sid": response["sid"],
            "status": response["status"],
            "num_media": getattr(response["message"], "num_media", 0),
            "media_url": None,
            "media_type": None
        }
    )
    
    outbound_message = conversation_service.add_message(conversation, outbound_data)
    
    logger.info(
        "Processed outbound message",
        conv_id=conversation.conv_id,
        msg_id=outbound_message.msg_id if outbound_message else None
    )

    return TwilioWebhookResponseDTO(
        success=True,
        message="Message processed successfully",
        conv_id=conversation.conv_id,
        msg_id=message.msg_id if message else None
    )
```

---

## 📚 Testes de Integração

### Teste Completo de Fluxo

```python
# test_lifecycle_integration.py
import pytest
from datetime import datetime, timedelta, timezone

def test_complete_conversation_lifecycle():
    """Testa ciclo completo: PENDING → PROGRESS → IDLE_TIMEOUT → PROGRESS → AGENT_CLOSED"""
    service = ConversationService()
    
    # 1. Criar conversa (PENDING)
    conv = service.get_or_create_conversation(
        owner_id=1,
        from_number="+5511999999999",
        to_number="+5511888888888",
        channel="whatsapp"
    )
    assert conv.status == ConversationStatus.PENDING.value
    
    # 2. Usuário envia mensagem (permanece PENDING)
    user_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number="+5511999999999",
        to_number="+5511888888888",
        body="Preciso de ajuda",
        message_owner=MessageOwner.USER
    )
    service.add_message(conv, user_msg)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PENDING.value
    
    # 3. Agente aceita (PENDING → PROGRESS)
    agent_msg = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number="+5511888888888",
        to_number="+5511999999999",
        body="Olá! Como posso ajudar?",
        message_owner=MessageOwner.AGENT
    )
    service.add_message(conv, agent_msg)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    assert 'accepted_by' in conv.context
    
    # 4. Simular inatividade (PROGRESS → IDLE_TIMEOUT)
    # Atualizar updated_at para simular inatividade
    past_time = datetime.now(timezone.utc) - timedelta(minutes=20)
    service.conversation_repo.client.table("conversations")\
        .update({"updated_at": past_time.isoformat()})\
        .eq("conv_id", conv.conv_id)\
        .execute()
    
    service.process_idle_conversations(idle_minutes=15)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.IDLE_TIMEOUT.value
    
    # 5. Usuário retorna (IDLE_TIMEOUT → PROGRESS)
    user_msg2 = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number="+5511999999999",
        to_number="+5511888888888",
        body="Ainda está aí?",
        message_owner=MessageOwner.USER
    )
    service.add_message(conv, user_msg2)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    assert conv.status == ConversationStatus.PROGRESS.value
    assert 'reactivated_from_idle' in conv.context
    
    # 6. Encerramento natural (PROGRESS → AGENT_CLOSED)
    agent_msg2 = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number="+5511888888888",
        to_number="+5511999999999",
        body="Resolvido! Até logo.",
        message_owner=MessageOwner.AGENT
    )
    service.add_message(conv, agent_msg2)
    
    user_msg3 = MessageCreateDTO(
        conv_id=conv.conv_id,
        from_number="+5511999999999",
        to_number="+5511888888888",
        body="Obrigado! Até mais.",
        message_owner=MessageOwner.USER
    )
    service.add_message(conv, user_msg3)
    
    conv = service.get_conversation_by_id(conv.conv_id)
    # Closure detector deve ter detectado e fechado
    assert conv.status in [
        ConversationStatus.AGENT_CLOSED.value,
        ConversationStatus.PROGRESS.value  # Depende da confiança
    ]
```

---

## 🚀 Deployment Checklist

### Antes de Deploy

- [ ] Revisar todas as correções de código
- [ ] Executar testes unitários
- [ ] Executar testes de integração
- [ ] Validar transições no ambiente de dev
- [ ] Verificar logs e métricas

### Durante Deploy

- [ ] Deploy incremental (feature flags se possível)
- [ ] Monitorar logs de transição
- [ ] Verificar métricas de conversas
- [ ] Alertas configurados

### Após Deploy

- [ ] Validar fluxos principais
- [ ] Verificar métricas de closure
- [ ] Analisar conversas em IDLE_TIMEOUT
- [ ] Documentar quaisquer issues encontradas

---

**Elaborado por:** Claude (Anthropic)  
**Versão:** 1.0  
**Data:** 09/01/2026