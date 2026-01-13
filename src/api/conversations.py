"""
API routes for conversation management.
"""
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from src.models.domain import ConversationCreateDTO, MessageCreateDTO

from ..models import (
    Conversation,
    Message,
    ConversationStatus
)
from ..services import ConversationService
from ..utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


# Response models
class ConversationResponse(BaseModel):
    """Response model for conversation."""
    conv_id: str
    owner_id: str
    from_number: str
    to_number: str
    status: str
    started_at: Optional[str]
    ended_at: Optional[str]
    channel: Optional[str]
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response model for message."""
    msg_id: str
    conv_id: str
    body: str
    direction: str
    timestamp: Optional[str]
    message_owner: str
    
    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response model for conversation list."""
    conversations: List[ConversationResponse]
    total: int


class TransferRequest(BaseModel):
    """Request model for transferring conversation."""
    new_user_id: str
    reason: Optional[str] = None


class EscalationRequest(BaseModel):
    """Request model for escalating conversation."""
    supervisor_id: str
    reason: str


def get_conversation_service() -> ConversationService:
    """Dependency to get conversation service."""
    return ConversationService()


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    conversation_data: ConversationCreateDTO,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Create or get an active conversation.
    
    If an active conversation exists for the given parameters, returns it.
    Otherwise, creates a new conversation.
    """
    try:
        conversation = service.get_or_create_conversation(
            owner_id=conversation_data.owner_id,
            from_number=conversation_data.from_number,
            to_number=conversation_data.to_number,
            channel=conversation_data.channel,
            user_id=conversation_data.user_id,
            metadata=conversation_data.metadata
        )
        
        return ConversationResponse.model_validate(conversation)
    except Exception as e:
        logger.error("Error creating conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conv_id}", response_model=ConversationResponse)
async def get_conversation(
    conv_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Get a conversation by ID."""
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return ConversationResponse.model_validate(conversation)


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    owner_id: str = Query(..., description="Owner ID"),
    limit: int = Query(100, ge=1, le=1000),
    service: ConversationService = Depends(get_conversation_service)
):
    """List active conversations for an owner."""
    conversations = service.get_active_conversations(owner_id, limit)
    
    return ConversationListResponse(
        conversations=[ConversationResponse.model_validate(c) for c in conversations],
        total=len(conversations)
    )


@router.get("/{conv_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conv_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ConversationService = Depends(get_conversation_service)
):
    """Get messages from a conversation."""
    # Verify conversation exists
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = service.get_conversation_messages(conv_id, limit, offset)
    
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{conv_id}/messages", response_model=MessageResponse, status_code=201)
async def add_message(
    conv_id: str,
    message_data: MessageCreateDTO,
    service: ConversationService = Depends(get_conversation_service)
):
    """Add a message to a conversation."""
    # Verify conversation exists
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Ensure conv_id matches
    message_data.conv_id = conv_id
    
    try:
        message = service.add_message(conversation, message_data)
        return MessageResponse.model_validate(message)
    except Exception as e:
        logger.error("Error adding message", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conv_id}/close", response_model=ConversationResponse)
async def close_conversation(
    conv_id: str,
    status: ConversationStatus,
    reason: Optional[str] = None,
    service: ConversationService = Depends(get_conversation_service)
):
    """Close a conversation."""
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        # Use priority-aware closure
        closed = service.close_conversation_with_priority(
            conversation, 
            status, 
            initiated_by="api_user", 
            reason=reason
        )
        return ConversationResponse.model_validate(closed)
    except Exception as e:
        logger.error("Error closing conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conv_id}/extend", response_model=ConversationResponse)
async def extend_conversation(
    conv_id: str,
    additional_minutes: Optional[int] = None,
    service: ConversationService = Depends(get_conversation_service)
):
    """Extend conversation expiration time."""
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        extended = service.extend_expiration(conversation, additional_minutes)
        return ConversationResponse.model_validate(extended)
    except Exception as e:
        logger.error("Error extending conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conv_id}/transfer", response_model=ConversationResponse)
async def transfer_conversation(
    conv_id: str,
    transfer_data: TransferRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Transfer conversation to another agent.
    
    Keeps status as PROGRESS but changes user_id and updates history.
    """
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        transferred = service.transfer_conversation(
            conversation,
            transfer_data.new_user_id,
            transfer_data.reason
        )
        return ConversationResponse.model_validate(transferred)
    except Exception as e:
        logger.error("Error transferring conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conv_id}/escalate", response_model=ConversationResponse)
async def escalate_conversation(
    conv_id: str,
    escalation_data: EscalationRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """
    Escalate conversation to supervisor.
    
    Keeps status as PROGRESS but adds escalation info to context.
    """
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        escalated = service.escalate_conversation(
            conversation,
            escalation_data.supervisor_id,
            escalation_data.reason
        )
        return ConversationResponse.model_validate(escalated)
    except Exception as e:
        logger.error("Error escalating conversation", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

