from typing import List, Optional, Protocol
from datetime import datetime
from src.core.database.interface import IRepository
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer, CustomerCreate, CustomerUpdate,
    Expense, ExpenseCreate, ExpenseUpdate,
    Invoice, InvoiceCreate, InvoiceUpdate,
    Revenue, RevenueCreate, RevenueUpdate
)

class IRevenueRepository(IRepository[Revenue], Protocol):
    """Interface for Revenue repository."""
    
    def create_from_schema(self, revenue: RevenueCreate) -> Optional[Revenue]:
        ...

    def update_from_schema(self, revenue_id: int, revenue: RevenueUpdate) -> Optional[Revenue]:
        ...

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Revenue]:
        ...

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        ...


class IExpenseRepository(IRepository[Expense], Protocol):
    """Interface for Expense repository."""

    def create_from_schema(self, expense: ExpenseCreate) -> Optional[Expense]:
        ...

    def update_from_schema(self, expense_id: int, expense: ExpenseUpdate) -> Optional[Expense]:
        ...

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Expense]:
        ...

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        ...


class ICustomerRepository(IRepository[Customer], Protocol):
    """Interface for Customer repository."""

    def create_from_schema(self, customer: CustomerCreate) -> Optional[Customer]:
        ...

    def update_from_schema(self, customer_id: int, customer: CustomerUpdate) -> Optional[Customer]:
        ...

    def search_by_name(self, search_term: str, limit: int = 100) -> List[Customer]:
        ...

    def get_by_phone(self, phone: str) -> Optional[Customer]:
        ...


class IInvoiceRepository(IRepository[Invoice], Protocol):
    """Interface for Invoice repository."""

    def create_from_schema(self, invoice: InvoiceCreate) -> Optional[Invoice]:
        ...

    def update_from_schema(self, invoice_id: int, invoice: InvoiceUpdate) -> Optional[Invoice]:
        ...

    def get_by_customer(self, customer_id: int) -> List[Invoice]:
        ...

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Invoice]:
        ...
