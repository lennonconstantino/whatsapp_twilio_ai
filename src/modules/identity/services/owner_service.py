"""
Owner Service module.
"""
from typing import List, Optional
from src.core.utils import get_logger
from src.modules.identity.repositories.interfaces import IOwnerRepository
from src.modules.identity.models.owner import Owner
from src.modules.identity.dtos.owner_dto import OwnerCreateDTO

logger = get_logger(__name__)

class OwnerService:
    """Service for managing owners (tenants)."""

    def __init__(self, repository: IOwnerRepository):
        """
        Initialize OwnerService.
        
        Args:
            repository: OwnerRepository instance
        """
        self.repository = repository

    def create_owner(self, data: OwnerCreateDTO) -> Optional[Owner]:
        """
        Create a new owner.
        
        Args:
            data: Owner creation data DTO
            
        Returns:
            Created Owner or None
            
        Raises:
            ValueError: If owner with same email already exists
        """
        logger.info(f"Creating owner with email: {data.email}")
        
        existing = self.repository.find_by_email(data.email)
        if existing:
            logger.warning(f"Owner with email '{data.email}' already exists")
            raise ValueError(f"Owner with email '{data.email}' already exists.")
        
        owner = self.repository.create_owner(data.name, data.email)
        if owner:
            logger.info(f"Owner created with ID: {owner.owner_id}")
        return owner

    def get_owner_by_email(self, email: str) -> Optional[Owner]:
        """
        Find owner by email.
        
        Args:
            email: Email address
            
        Returns:
            Owner instance or None
        """
        return self.repository.find_by_email(email)

    def get_active_owners(self) -> List[Owner]:
        """
        Get all active owners.
        
        Returns:
            List of active Owners
        """
        return self.repository.find_active_owners()
    
    def get_owner_by_id(self, owner_id: str) -> Optional[Owner]:
        """
        Get owner by ID.
        
        Args:
            owner_id: Owner ID (ULID)
            
        Returns:
            Owner instance or None
        """
        return self.repository.find_by_id(owner_id)

    def deactivate_owner(self, owner_id: str) -> Optional[Owner]:
        """
        Deactivate an owner.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            Updated Owner or None
        """
        logger.info(f"Deactivating owner {owner_id}")
        return self.repository.deactivate_owner(owner_id)
        
    def activate_owner(self, owner_id: str) -> Optional[Owner]:
        """
        Activate an owner.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            Updated Owner or None
        """
        logger.info(f"Activating owner {owner_id}")
        return self.repository.activate_owner(owner_id)

    def delete_owner(self, owner_id: str) -> bool:
        """
        Delete an owner (Hard Delete).
        Used primarily for rollback operations or cleanup.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            True if deleted, False otherwise
        """
        logger.warning(f"Permanently deleting owner {owner_id}")
        return self.repository.delete(owner_id, id_column="owner_id")
