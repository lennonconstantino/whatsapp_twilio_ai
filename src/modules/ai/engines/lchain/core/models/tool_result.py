from typing import Optional

from pydantic import BaseModel


class ToolResult(BaseModel):
    content: Optional[str] = None
    success: bool
    error: Optional[str] = None
