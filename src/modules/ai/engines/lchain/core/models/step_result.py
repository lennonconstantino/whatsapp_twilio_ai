from typing import Optional
from pydantic import BaseModel


class StepResult(BaseModel):
    event: str
    content: Optional[str] = None
    success: bool
