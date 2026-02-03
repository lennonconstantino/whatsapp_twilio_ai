from abc import ABC, abstractmethod
from typing import List, Optional

from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
)


class CustomerRepository(ABC):
    """
    Abstract Base Class for Customer Repository.
    Defines the contract for Customer data access.
    """

    @abstractmethod
    def create_from_schema(self, customer: CustomerCreate) -> Optional[Customer]:
        """Create customer from Pydantic schema."""
        pass

    @abstractmethod
    def update_from_schema(
        self, customer_id: int, customer: CustomerUpdate
    ) -> Optional[Customer]:
        """Update customer from Pydantic schema."""
        pass

    @abstractmethod
    def search_by_name(self, search_term: str, limit: int = 100) -> List[Customer]:
        """Search customers by name (first_name, last_name or company_name)."""
        pass

    @abstractmethod
    def get_by_phone(self, phone: str) -> Optional[Customer]:
        """Find customer by phone number."""
        pass

    @abstractmethod
    def get_by_company(self, company_name: str) -> List[Customer]:
        """Find customers by company name."""
        pass
