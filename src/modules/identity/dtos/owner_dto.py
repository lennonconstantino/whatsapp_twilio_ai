
from pydantic import BaseModel

class OwnerCreateDTO(BaseModel):
    """DTO for creating an owner."""
    name: str
    email: str

    def __repr__(self) -> str:
        return f"OwnerCreateDTO(name={self.name}, email={self.email})"
