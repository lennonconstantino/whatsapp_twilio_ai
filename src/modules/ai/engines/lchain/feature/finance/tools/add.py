from typing import Type

from pydantic import BaseModel

from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.engines.lchain.core.tools.tool import Tool
from src.modules.ai.engines.lchain.feature.finance.models import *
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    Customer, CustomerCreate, Expense, ExpenseCreate, Revenue, RevenueCreate)
from src.modules.ai.engines.lchain.feature.finance.repositories.revenue_repository import RevenueRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.expense_repository import ExpenseRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.customer_repository import CustomerRepository


def prepare_data_for_db(data: dict) -> dict:
    """Helper to prepare data for DB insertion (e.g. converting datetimes)"""
    processed = {}
    for k, v in data.items():
        if hasattr(v, 'isoformat'):
            processed[k] = v.isoformat()
        else:
            processed[k] = v
    return processed


class AddExpenseTool(Tool):
    """
    Tool para adicionar despesas ao banco de dados.

    Usa Supabase via repository pattern.
    Calcula automaticamente gross_amount baseado em net_amount e tax_rate.
    """

    name: str = "add_expense"
    description: str = (
        "Add an expense to the database. "
        "The tax rate is 0.19 (19%). "
        "Provide net_amount (before tax), and gross_amount will be calculated automatically."
    )
    args_schema: Type[BaseModel] = ExpenseCreate
    model: Type[BaseModel] = Expense
    repository: ExpenseRepository

    def _run(self, **kwargs) -> ToolResult:
        """Executa a tool de forma síncrona"""
        return self.execute(**kwargs)

    async def _arun(self, **kwargs) -> ToolResult:
        """Executa a tool de forma assíncrona"""
        return self._run(**kwargs)

    def execute(self, **kwargs) -> ToolResult:
        """
        Executa a adição de expense.

        Args:
            **kwargs: Argumentos validados pelo args_schema

        Returns:
            ToolResult com mensagem de sucesso ou erro
        """
        try:
            # Validar e criar expense
            expense_input = ExpenseCreate.model_validate(kwargs)

            # Salvar via repository
            expense = self.repository.create_from_schema(expense_input)

            content = f"Successfully added expense: {expense.description} (ID: {expense.id}, Amount: {expense.gross_amount})"
            return ToolResult(success=True, content=content)
        except Exception as e:
            return ToolResult(success=False, content=str(e))


class AddRevenueTool(Tool):
    """
    Tool para adicionar receitas ao banco de dados.

    Usa Supabase via repository pattern.
    Calcula automaticamente gross_amount baseado em net_amount e tax_rate.
    """

    name: str = "add_revenue"
    description: str = (
        "Add a revenue entry to the database. "
        "The tax rate is 0.19 (19%). "
        "Provide net_amount (before tax), and gross_amount will be calculated automatically."
    )
    args_schema: Type[BaseModel] = RevenueCreate
    model: Type[BaseModel] = Revenue
    repository: RevenueRepository

    def _run(self, **kwargs) -> ToolResult:
        """Executa a tool de forma síncrona"""
        return self.execute(**kwargs)

    async def _arun(self, **kwargs) -> ToolResult:
        """Executa a tool de forma assíncrona"""
        return self._run(**kwargs)

    def execute(self, **kwargs) -> ToolResult:
        """
        Executa a adição de revenue.

        Args:
            **kwargs: Argumentos validados pelo args_schema

        Returns:
            ToolResult com mensagem de sucesso ou erro
        """
        try:
            # Validar e criar revenue
            revenue_input = RevenueCreate.model_validate(kwargs)

            # Salvar via repository
            revenue = self.repository.create_from_schema(revenue_input)

            content = f"Successfully added revenue: {revenue.description} (ID: {revenue.id}, Amount: {revenue.gross_amount})"
            return ToolResult(success=True, content=content)
        except Exception as e:
            return ToolResult(success=False, content=str(e))


class AddCustomerTool(Tool):
    """
    Tool para adicionar clientes ao banco de dados.

    Usa Supabase via repository pattern.
    """

    name: str = "add_customer"
    description: str = (
        "Add a customer to the database with their contact and address information."
    )
    args_schema: Type[BaseModel] = CustomerCreate
    model: Type[BaseModel] = Customer
    repository: CustomerRepository

    def _run(self, **kwargs) -> ToolResult:
        """Executa a tool de forma síncrona"""
        return self.execute(**kwargs)

    async def _arun(self, **kwargs) -> ToolResult:
        """Executa a tool de forma assíncrona"""
        return self._run(**kwargs)

    def execute(self, **kwargs) -> ToolResult:
        """
        Executa a adição de customer.

        Args:
            **kwargs: Argumentos validados pelo args_schema

        Returns:
            ToolResult com mensagem de sucesso ou erro
        """
        try:
            # Validar e criar customer
            customer_input = CustomerCreate.model_validate(kwargs)

            # Salvar via repository
            customer = self.repository.create_from_schema(customer_input)

            content = f"Successfully added customer: {customer.first_name} {customer.last_name} (ID: {customer.id})"
            return ToolResult(success=True, message=content)
        except Exception as e:
            return ToolResult(success=False, message=str(e))



