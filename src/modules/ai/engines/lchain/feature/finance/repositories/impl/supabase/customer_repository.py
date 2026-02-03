from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.customer_repository import (
    CustomerRepository,
)

logger = get_logger(__name__)


class SupabaseCustomerRepository(SupabaseRepository[Customer], CustomerRepository):
    """Repository for Customer operations via Supabase."""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="customer",
            model_class=Customer,
            validates_ulid=False,
        )

    def create_from_schema(self, customer: CustomerCreate) -> Optional[Customer]:
        """Create customer from Pydantic schema"""
        data = customer.model_dump()
        return self.create(data)

    def update_from_schema(
        self, customer_id: int, customer: CustomerUpdate
    ) -> Optional[Customer]:
        """Update customer from Pydantic schema"""
        data = customer.model_dump(exclude_unset=True)
        if not data:
            return self.find_by_id(customer_id)
        return self.update(customer_id, data)

    def search_by_name(self, search_term: str, limit: int = 100) -> List[Customer]:
        """
        Search customers by name (first_name, last_name or company_name).
        Case-insensitive.
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .or_(
                    f"first_name.ilike.%{search_term}%,"
                    f"last_name.ilike.%{search_term}%,"
                    f"company_name.ilike.%{search_term}%"
                )
                .limit(limit)
                .execute()
            )

            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(
                f"Error searching customers by name",
                error=str(e),
                search_term=search_term,
            )
            raise

    def get_by_phone(self, phone: str) -> Optional[Customer]:
        """Find customer by phone number"""
        results = self.find_by({"phone": phone}, limit=1)
        return results[0] if results else None

    def get_by_company(self, company_name: str) -> List[Customer]:
        """Find customers by company name"""
        return self.find_by({"company_name": company_name})
