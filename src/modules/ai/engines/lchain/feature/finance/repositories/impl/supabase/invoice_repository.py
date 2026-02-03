from datetime import datetime
from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils import get_logger
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Invoice,
    InvoiceCreate,
    InvoiceUpdate,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.invoice_repository import (
    InvoiceRepository,
)
from src.modules.ai.engines.lchain.feature.finance.repositories.impl.supabase.utils import (
    prepare_data_for_db,
)

logger = get_logger(__name__)


class SupabaseInvoiceRepository(SupabaseRepository[Invoice], InvoiceRepository):
    """Repository for Invoice operations via Supabase."""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="invoice",
            model_class=Invoice,
            validates_ulid=False,
        )

    def create_from_schema(self, invoice: InvoiceCreate) -> Optional[Invoice]:
        """Create invoice from Pydantic schema"""
        data = prepare_data_for_db(invoice.model_dump())
        return self.create(data)

    def update_from_schema(
        self, invoice_id: int, invoice: InvoiceUpdate
    ) -> Optional[Invoice]:
        """Update invoice from Pydantic schema"""
        data = prepare_data_for_db(invoice.model_dump(exclude_unset=True))
        if not data:
            return self.find_by_id(invoice_id)
        return self.update(invoice_id, data)

    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Find invoice by number (unique)"""
        results = self.find_by({"invoice_number": invoice_number}, limit=1)
        return results[0] if results else None

    def get_by_customer(self, customer_id: int, limit: int = 100) -> List[Invoice]:
        """Find all invoices for a customer"""
        return self.find_by({"customer_id": customer_id}, limit=limit)

    def get_with_customer(self, invoice_id: int) -> Optional[dict]:
        """
        Find invoice with customer data (JOIN).
        Returns dict with complete data.
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*, customer(*)")
                .eq("id", invoice_id)
                .execute()
            )

            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(
                f"Error finding invoice with customer",
                error=str(e),
                invoice_id=invoice_id,
            )
            raise

    def get_all_with_customers(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """
        List all invoices with customer data (JOIN).
        Useful for reports.
        """
        try:
            result = (
                self.client.table(self.table_name)
                .select("*, customer(*)")
                .range(offset, offset + limit - 1)
                .order("date", desc=True)
                .execute()
            )

            return result.data
        except Exception as e:
            logger.error(f"Error finding all invoices with customers", error=str(e))
            raise

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Invoice]:
        """Find invoices in a date range"""
        try:
            result = (
                self.client.table(self.table_name)
                .select("*")
                .gte("date", start_date.isoformat())
                .lte("date", end_date.isoformat())
                .order("date", desc=True)
                .execute()
            )

            return [self.model_class(**item) for item in result.data]
        except Exception as e:
            logger.error(
                f"Error finding invoices by date range",
                error=str(e),
                start_date=start_date,
                end_date=end_date,
            )
            raise
