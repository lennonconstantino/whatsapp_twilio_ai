from enum import Enum


class UserRole(str, Enum):
    """
    Enum for user roles.
    
    Defines the role of users in the system:
    - ADMIN: Administrator with full access
    - AGENT: Agent with limited access
    - USER: Regular user
    """
    ADMIN = "admin"
    AGENT = "agent"
    USER = "user"

    def __repr__(self) -> str:
        return f"UserRole.{self.name}"
    