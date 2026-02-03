from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Invoice,
    InvoiceCreate,
    InvoiceUpdate,
)


class InvoiceRepository(ABC):
    """
    Abstract Base Class for Invoice Repository.
    Defines the contract for Invoice data access.
    """

    @abstractmethod
    def create_from_schema(self, invoice: InvoiceCreate) -> Optional[Invoice]:
        """Create invoice from Pydantic schema."""
        pass

    @abstractmethod
    def update_from_schema(
        self, invoice_id: int, invoice: InvoiceUpdate
    ) -> Optional[Invoice]:
        """Update invoice from Pydantic schema."""
        pass

    @abstractmethod
    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Find invoice by unique number."""
        pass

    @abstractmethod
    def get_by_customer(self, customer_id: int, limit: int = 100) -> List[Invoice]:
        """Find all invoices for a customer."""
        pass

    @abstractmethod
    def get_with_customer(self, invoice_id: int) -> Optional[dict]:
        """Find invoice with customer data (JOIN)."""
        pass

    @abstractmethod
    def get_all_with_customers(self, limit: int = 100, offset: int = 0) -> List[dict]:
        """List all invoices with customer data."""
        pass

    @abstractmethod
    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Invoice]:
        """Find invoices in a date range."""
        pass
