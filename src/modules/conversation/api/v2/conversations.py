"""
API routes for conversation management (V2).
"""

from typing import List, Optional

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from src.core.di.container import Container
from src.core.utils import get_logger
from src.modules.conversation.dtos.conversation_dto import \
    ConversationCreateDTO
from src.modules.conversation.dtos.message_dto import MessageCreateDTO
from src.modules.conversation.enums.conversation_status import \
    ConversationStatus
from src.modules.conversation.v2.services.conversation_service import \
    ConversationServiceV2

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations_v2"])


# Response models (Reusing existing or creating new ones if schema changed)
# For now, we assume schema compatibility
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
    # V2 specific fields if any, keeping it compatible for now

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


@router.post("/", response_model=ConversationResponse, status_code=201)
@inject
async def create_conversation(
    conversation_data: ConversationCreateDTO,
    service: ConversationServiceV2 = Depends(
        Provide[Container.conversation_service_v2]
    ),
):
    """
    Create or get an active conversation (V2).
    """
    try:
        conversation = service.get_or_create_conversation(
            owner_id=conversation_data.owner_id,
            from_number=conversation_data.from_number,
            to_number=conversation_data.to_number,
            channel=conversation_data.channel,
            user_id=conversation_data.user_id,
            metadata=conversation_data.metadata,
        )

        return ConversationResponse.model_validate(conversation)
    except Exception as e:
        logger.error("Error creating conversation V2", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{conv_id}", response_model=ConversationResponse)
@inject
async def get_conversation(
    conv_id: str,
    service: ConversationServiceV2 = Depends(
        Provide[Container.conversation_service_v2]
    ),
):
    """Get a conversation by ID (V2)."""
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationResponse.model_validate(conversation)


@router.get("/", response_model=ConversationListResponse)
@inject
async def list_conversations(
    owner_id: str = Query(..., description="Owner ID"),
    limit: int = Query(100, ge=1, le=1000),
    service: ConversationServiceV2 = Depends(
        Provide[Container.conversation_service_v2]
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
async def get_conversation_messages(
    conv_id: str,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: ConversationServiceV2 = Depends(
        Provide[Container.conversation_service_v2]
    ),
):
    """Get messages from a conversation (V2)."""
    # Verify conversation exists
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = service.get_conversation_messages(conv_id, limit, offset)

    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{conv_id}/messages", response_model=MessageResponse, status_code=201)
@inject
async def add_message(
    conv_id: str,
    message_data: MessageCreateDTO,
    service: ConversationServiceV2 = Depends(
        Provide[Container.conversation_service_v2]
    ),
):
    """Add a message to a conversation (V2)."""
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
        logger.error("Error adding message V2", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{conv_id}/close", response_model=ConversationResponse)
@inject
async def close_conversation(
    conv_id: str,
    status: ConversationStatus,
    reason: str = Query(..., description="Reason for closure"),
    service: ConversationServiceV2 = Depends(
        Provide[Container.conversation_service_v2]
    ),
):
    """Close a conversation (V2)."""
    conversation = service.get_conversation_by_id(conv_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        closed = service.close_conversation(
            conversation, status, initiated_by="api_user_v2", reason=reason
        )
        return ConversationResponse.model_validate(closed)
    except Exception as e:
        logger.error("Error closing conversation V2", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
