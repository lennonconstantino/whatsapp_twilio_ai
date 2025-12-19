
from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class RoleType(str, Enum):
    """Tipos de papel do usuário."""
    ADMIN: str = "admin"
    BASIC: str = "basic"

class User(BaseModel):
    """Modelo para usuário do sistema."""
    id: str
    profile_name: str
    phone: str
    role: RoleType = RoleType.BASIC
