"""
API routes for conversation management (V2).
"""

from typing import List, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.core.di.container import Container
from src.core.security import get_current_owner_id
from src.core.utils import get_logger
from src.modules.conversation.dtos.conversation_dto import \
    ConversationCreateDTO
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.services.conversation_service import \
    ConversationService

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations_v2"])


from datetime import datetime

# Response models (Reusing existing or creating new ones if schema changed)
# For now, we assume schema compatibility
class ConversationResponse(BaseModel):
    """Response model for conversation."""

    conv_id: str
    owner_id: str
    from_number: str
    to_number: str
    status: str
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    channel: Optional[str]
    # V2 specific fields if any, keeping it compatible for now

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response model for message."""

    msg_id: str
    conv_id: str
    body: str
    direction: str
    timestamp: Optional[datetime]
    message_owner: str

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """Response model for conversation list."""

    conversations: List[ConversationResponse]
    total: int


@router.post("/", response_model=ConversationResponse, status_code=201)
@inject
def create_conversation(
    conversation_data: ConversationCreateDTO,
    owner_id: str = Depends(get_current_owner_id),
    service: ConversationService = Depends(
        Provide[Container.conversation_service]
    ),
):
    """
    Create or get an active conversation (V2).
    """
    if conversation_data.owner_id != owner_id:
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized to create conversation for owner {conversation_data.owner_id}",
        )

    conversation = service.get_or_create_conversation(
        owner_id=conversation_data.owner_id,
        from_number=conversation_data.from_number,
        to_number=conversation_data.to_number,
        channel=conversation_data.channel,
        user_id=conversation_data.user_id,
        metadata=conversation_data.metadata,
    )

    return ConversationResponse.model_validate(conversation)


@router.get("/{conv_id}", response_model=ConversationResponse)
@inject
def get_conversation(
    conv_id: str,
    owner_id: str = Depends(get_current_owner_id),
    service: ConversationService = Depends(
        Provide[Container.conversation_service]
    ),
):
    """Get a conversation by ID (V2)."""
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    return ConversationResponse.model_validate(conversation)


@router.get("/", response_model=ConversationListResponse)
@inject
def list_conversations(
    limit: int = Query(100, ge=1, le=1000),
    owner_id: str = Depends(get_current_owner_id),
    service: ConversationService = Depends(
        Provide[Container.conversation_service]
    ),
):
    """List active conversations for an owner (V2)."""
    conversations = service.get_active_conversations(owner_id, limit)

    return ConversationListResponse(
        conversations=[ConversationResponse.model_validate(c) for c in conversations],
        total=len(conversations),
    )


@router.get("/{conv_id}/messages", response_model=List[MessageResponse])
@inject
def get_conversation_messages(
    conv_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    owner_id: str = Depends(get_current_owner_id),
    service: ConversationService = Depends(
        Provide[Container.conversation_service]
    ),
):
    """Get messages from a conversation (V2)."""
    # Verify conversation exists
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    messages = service.get_conversation_messages(conv_id, limit, offset)

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{conv_id}/messages", response_model=MessageResponse, status_code=201)
@inject
def add_message(
    conv_id: str,
    message_data: MessageCreateDTO,
    owner_id: str = Depends(get_current_owner_id),
    service: ConversationService = Depends(
        Provide[Container.conversation_service]
    ),
):
    """Add a message to a conversation (V2)."""
    # Verify conversation exists
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    # Ensure conv_id matches
    message_data.conv_id = conv_id

    message = service.add_message(conversation, message_data)
    return MessageResponse.model_validate(message)


@router.post("/{conv_id}/close", response_model=ConversationResponse)
@inject
def close_conversation(
    conv_id: str,
    status: ConversationStatus,
    reason: str = Query(..., description="Reason for closure"),
    owner_id: str = Depends(get_current_owner_id),
    service: ConversationService = Depends(
        Provide[Container.conversation_service]
    ),
):
    """Close a conversation (V2)."""
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.owner_id != owner_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this conversation")

    closed = service.close_conversation(
        conversation, status, initiated_by="api_user_v2", reason=reason
    )
    return ConversationResponse.model_validate(closed)
