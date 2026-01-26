from typing import Optional
from pydantic import BaseModel, EmailStr

class RegisterOrganizationDTO(BaseModel):
    """DTO for registering a new organization."""
    name: str
    email: EmailStr
    auth_id: str
    
    # Optional profile info
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

    def __repr__(self) -> str:
        return f"RegisterOrganizationDTO(name={self.name}, email={self.email})"
