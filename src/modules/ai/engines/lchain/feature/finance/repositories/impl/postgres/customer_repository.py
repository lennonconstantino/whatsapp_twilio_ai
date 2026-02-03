from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.customer_repository import (
    CustomerRepository,
)


class PostgresCustomerRepository(PostgresRepository[Customer], CustomerRepository):
    """Repository for Customer operations via Postgres."""

    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "customer", Customer)

    def create_from_schema(self, customer: CustomerCreate) -> Optional[Customer]:
        """Create customer from Pydantic schema."""
        data = customer.model_dump()
        return self.create(data)

    def update_from_schema(
        self, customer_id: int, customer: CustomerUpdate
    ) -> Optional[Customer]:
        """Update customer from Pydantic schema."""
        data = customer.model_dump(exclude_unset=True)
        if not data:
            return self.find_by_id(customer_id)
        return self.update(customer_id, data)

    def search_by_name(self, search_term: str, limit: int = 100) -> List[Customer]:
        """Search customers by name."""
        raise NotImplementedError("Postgres implementation not yet available")

    def get_by_phone(self, phone: str) -> Optional[Customer]:
        """Find customer by phone number."""
        return self.find_by({"phone": phone}, limit=1)[0] if self.find_by({"phone": phone}, limit=1) else None

    def get_by_company(self, company_name: str) -> List[Customer]:
        """Find customers by company name."""
        return self.find_by({"company_name": company_name})
