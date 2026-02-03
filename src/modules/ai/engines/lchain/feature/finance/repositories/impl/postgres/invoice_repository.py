from datetime import datetime
from typing import List, Optional

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Invoice,
    InvoiceCreate,
    InvoiceUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.invoice_repository import (
    InvoiceRepository,
)


class PostgresInvoiceRepository(PostgresRepository[Invoice], InvoiceRepository):
    """Repository for Invoice operations via Postgres."""

    def __init__(self, db: PostgresDatabase):
        super().__init__(db, "invoice", Invoice)

    def create_from_schema(self, invoice: InvoiceCreate) -> Optional[Invoice]:
        """Create invoice from Pydantic schema."""
        data = invoice.model_dump()
        return self.create(data)

    def update_from_schema(
        self, invoice_id: int, invoice: InvoiceUpdate
    ) -> Optional[Invoice]:
        """Update invoice from Pydantic schema."""
        data = invoice.model_dump(exclude_unset=True)
        if not data:
            return self.find_by_id(invoice_id)
        return self.update(invoice_id, data)

    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Find invoice by number (unique)."""
        return self.find_by({"invoice_number": invoice_number}, limit=1)[0] if self.find_by({"invoice_number": invoice_number}, limit=1) else None

    def get_by_customer(self, customer_id: int, limit: int = 100) -> List[Invoice]:
        """Find all invoices for a customer."""
        return self.find_by({"customer_id": customer_id}, limit=limit)

    def get_with_customer(self, invoice_id: int) -> Optional[dict]:
        """Find invoice with customer data (JOIN)."""
        raise NotImplementedError("Postgres implementation not yet available")

    def get_all_with_customers(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """List all invoices with customer data."""
        raise NotImplementedError("Postgres implementation not yet available")

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Invoice]:
        """Find invoices in a date range."""
        raise NotImplementedError("Postgres implementation not yet available")
