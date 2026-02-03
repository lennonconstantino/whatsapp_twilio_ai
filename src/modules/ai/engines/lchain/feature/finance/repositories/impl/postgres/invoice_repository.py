from datetime import datetime
from typing import List, Optional

from psycopg2 import sql

from src.core.database.postgres_repository import PostgresRepository
from src.core.database.postgres_session import PostgresDatabase
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Invoice,
    InvoiceCreate,
    InvoiceUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.interfaces import (
    IInvoiceRepository,
)


class PostgresInvoiceRepository(PostgresRepository[Invoice], IInvoiceRepository):
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

    def get_by_customer(self, customer_id: int) -> List[Invoice]:
        """Find all invoices for a customer."""
        return self.find_by({"customer_id": customer_id}, limit=100)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Invoice]:
        """Find invoices in a date range."""
        query = sql.SQL(
            "SELECT * FROM {} WHERE issue_date >= %s AND issue_date <= %s ORDER BY issue_date DESC"
        ).format(sql.Identifier(self.table_name))
        
        results = self._execute_query(
            query, 
            (start_date, end_date), 
            fetch_all=True
        )
        
        return [self.model_class(**item) for item in results]
