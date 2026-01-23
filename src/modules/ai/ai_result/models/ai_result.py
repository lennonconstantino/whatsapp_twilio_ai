"""
Updated domain models with ULID support.

This file shows how to update the models to support ULID primary keys.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, field_validator

from src.core.utils.custom_ulid import validate_ulid_field, is_valid_ulid
from src.modules.ai.ai_result.enums.ai_result_type import AIResultType

class AIResult(BaseModel):
    """
    AI Result entity with ULID.
    """
    ai_result_id: Optional[str] = None  # Changed from int to str (ULID)
    msg_id: str  # Changed to ULID
    correlation_id: Optional[str] = None  # Trace ID
    feature_id: int  # Keeping as int
    result_type: AIResultType = AIResultType.AGENT_LOG
    result_json: Dict[str, Any]
    processed_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    @field_validator('ai_result_id')
    @classmethod
    def validate_ai_result_id(cls, v):
        """Validate ULID format for ai_result_id."""
        return validate_ulid_field(v)
    
    @field_validator('msg_id')
    @classmethod
    def validate_msg_id(cls, v):
        """Validate ULID format for msg_id."""
        if not v:
            raise ValueError('msg_id is required')
        if not is_valid_ulid(v):
            raise ValueError(f'Invalid ULID format for msg_id: {v}')
        return v.upper()

    def __repr__(self) -> str:
        return f"AIResult(id={self.ai_result_id}, msg_id={self.msg_id}, feature_id={self.feature_id})"