from datetime import datetime
from typing import List, Optional

from supabase import Client

from src.core.database.supabase_repository import SupabaseRepository
from src.core.utils.logging import get_logger
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer, CustomerCreate, CustomerUpdate, Expense, ExpenseCreate,
    ExpenseUpdate, Invoice, InvoiceCreate, InvoiceUpdate, Revenue,
    RevenueCreate, RevenueUpdate)
from src.modules.ai.engines.lchain.feature.finance.repositories.interfaces import (
    ICustomerRepository, IExpenseRepository, IInvoiceRepository,
    IRevenueRepository)

logger = get_logger(__name__)


def prepare_data_for_db(data: dict) -> dict:
    """
    Prepara dados Pydantic para inserção no Supabase.
    Converte datetime para ISO string.
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


class SupabaseRevenueRepository(SupabaseRepository[Revenue], IRevenueRepository):
    """Repository para operações de Revenue"""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="revenue",
            model_class=Revenue,
            validates_ulid=False,  # Usa BIGSERIAL (int) ao invés de ULID
        )

    def create_from_schema(self, revenue: RevenueCreate) -> Optional[Revenue]:
        """
        Cria revenue a partir do schema Pydantic.
        Converte automaticamente datetime para ISO string.
        """
        data = prepare_data_for_db(revenue.model_dump())
        return self.create(data)

    def update_from_schema(
        self, revenue_id: int, revenue: RevenueUpdate
    ) -> Optional[Revenue]:
        """
        Atualiza revenue a partir do schema Pydantic.
        Apenas campos fornecidos são atualizados.
        """
        data = prepare_data_for_db(revenue.model_dump(exclude_unset=True))
        if not data:  # Se não há dados para atualizar
            return self.find_by_id(revenue_id)
        return self.update(revenue_id, data)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Revenue]:
        """Busca revenues em um intervalo de datas"""
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
                f"Error finding revenues by date range",
                error=str(e),
                start_date=start_date,
                end_date=end_date,
            )
            raise

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calcula total de revenues em um período"""
        revenues = self.get_by_date_range(start_date, end_date)
        return sum(r.gross_amount for r in revenues)


class SupabaseExpenseRepository(SupabaseRepository[Expense], IExpenseRepository):
    """Repository para operações de Expense"""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="expense",
            model_class=Expense,
            validates_ulid=False,
        )

    def create_from_schema(self, expense: ExpenseCreate) -> Optional[Expense]:
        """Cria expense a partir do schema Pydantic"""
        data = prepare_data_for_db(expense.model_dump())
        return self.create(data)

    def update_from_schema(
        self, expense_id: int, expense: ExpenseUpdate
    ) -> Optional[Expense]:
        """Atualiza expense a partir do schema Pydantic"""
        data = prepare_data_for_db(expense.model_dump(exclude_unset=True))
        if not data:
            return self.find_by_id(expense_id)
        return self.update(expense_id, data)

    def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Expense]:
        """Busca expenses em um intervalo de datas"""
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
                f"Error finding expenses by date range",
                error=str(e),
                start_date=start_date,
                end_date=end_date,
            )
            raise

    def get_total_by_period(self, start_date: datetime, end_date: datetime) -> float:
        """Calcula total de expenses em um período"""
        expenses = self.get_by_date_range(start_date, end_date)
        return sum(e.gross_amount for e in expenses)


class SupabaseCustomerRepository(SupabaseRepository[Customer], ICustomerRepository):
    """Repository para operações de Customer"""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="customer",
            model_class=Customer,
            validates_ulid=False,
        )

    def create_from_schema(self, customer: CustomerCreate) -> Optional[Customer]:
        """Cria customer a partir do schema Pydantic"""
        data = customer.model_dump()
        return self.create(data)

    def update_from_schema(
        self, customer_id: int, customer: CustomerUpdate
    ) -> Optional[Customer]:
        """Atualiza customer a partir do schema Pydantic"""
        data = customer.model_dump(exclude_unset=True)
        if not data:
            return self.find_by_id(customer_id)
        return self.update(customer_id, data)

    def search_by_name(self, search_term: str, limit: int = 100) -> List[Customer]:
        """
        Busca customers por nome (first_name, last_name ou company_name).
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
        """Busca customer por telefone"""
        results = self.find_by({"phone": phone}, limit=1)
        return results[0] if results else None

    def get_by_company(self, company_name: str) -> List[Customer]:
        """Busca customers por nome da empresa"""
        return self.find_by({"company_name": company_name})


class SupabaseInvoiceRepository(SupabaseRepository[Invoice], IInvoiceRepository):
    """Repository para operações de Invoice"""

    def __init__(self, client: Client):
        super().__init__(
            client=client,
            table_name="invoice",
            model_class=Invoice,
            validates_ulid=False,
        )

    def create_from_schema(self, invoice: InvoiceCreate) -> Optional[Invoice]:
        """Cria invoice a partir do schema Pydantic"""
        data = prepare_data_for_db(invoice.model_dump())
        return self.create(data)

    def update_from_schema(
        self, invoice_id: int, invoice: InvoiceUpdate
    ) -> Optional[Invoice]:
        """Atualiza invoice a partir do schema Pydantic"""
        data = prepare_data_for_db(invoice.model_dump(exclude_unset=True))
        if not data:
            return self.find_by_id(invoice_id)
        return self.update(invoice_id, data)

    def get_by_invoice_number(self, invoice_number: str) -> Optional[Invoice]:
        """Busca invoice por número (único)"""
        results = self.find_by({"invoice_number": invoice_number}, limit=1)
        return results[0] if results else None

    def get_by_customer(self, customer_id: int, limit: int = 100) -> List[Invoice]:
        """Busca todas as invoices de um customer"""
        return self.find_by({"customer_id": customer_id}, limit=limit)

    def get_with_customer(self, invoice_id: int) -> Optional[dict]:
        """
        Busca invoice com dados do customer (JOIN).
        Retorna dict com dados completos.
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
        Lista todas as invoices com dados dos customers (JOIN).
        Útil para relatórios.
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
        """Busca invoices em um intervalo de datas"""
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
