from pydantic import BaseModel


class StepResult(BaseModel):
    event: str
    content: str
    success: bool
