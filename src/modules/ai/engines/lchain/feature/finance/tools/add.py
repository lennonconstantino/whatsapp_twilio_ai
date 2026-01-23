from typing import Type
from pydantic import BaseModel

from src.modules.ai.engines.lchain.feature.finance.models.models import Customer, CustomerCreate, Expense, ExpenseCreate, Revenue, RevenueCreate
from src.modules.ai.engines.lchain.feature.finance.repositories.repository_finance import get_customer_repository, get_expense_repository, get_revenue_repository
from src.modules.ai.engines.lchain.feature.finance.models import *
from src.modules.ai.engines.lchain.core.models.tool_result import ToolResult
from src.modules.ai.engines.lchain.core.tools.tool import Tool

def add_expense_to_db(data: dict) -> str:
    """
    Adiciona expense ao banco de dados via Supabase.
    
    Args:
        data: Dicionário com dados da expense
        
    Returns:
        Mensagem de sucesso
        
    Raises:
        ValueError: Se validação falhar
        Exception: Se erro ao salvar no DB
    """
    try:
        # Validar e criar expense
        expense_input = ExpenseCreate.model_validate(data)
        
        # Salvar via repository
        repo = get_expense_repository()
        expense = repo.create_from_schema(expense_input)
        
        return f"Successfully added expense: {expense.description} (ID: {expense.id}, Amount: {expense.gross_amount})"
    
    except Exception as e:
        raise RuntimeError(f"Failed to add expense: {str(e)}")


def add_revenue_to_db(data: dict) -> str:
    """
    Adiciona revenue ao banco de dados via Supabase.
    
    Args:
        data: Dicionário com dados da revenue
        
    Returns:
        Mensagem de sucesso
        
    Raises:
        ValueError: Se validação falhar
        Exception: Se erro ao salvar no DB
    """
    try:
        # Validar e criar revenue
        revenue_input = RevenueCreate.model_validate(data)
        
        # Salvar via repository
        repo = get_revenue_repository()
        revenue = repo.create_from_schema(revenue_input)
        
        return f"Successfully added revenue: {revenue.description} (ID: {revenue.id}, Amount: {revenue.gross_amount})"
    
    except Exception as e:
        raise RuntimeError(f"Failed to add revenue: {str(e)}")


def add_customer_to_db(data: dict) -> str:
    """
    Adiciona customer ao banco de dados via Supabase.
    
    Args:
        data: Dicionário com dados do customer
        
    Returns:
        Mensagem de sucesso
        
    Raises:
        ValueError: Se validação falhar
        Exception: Se erro ao salvar no DB
    """
    try:
        # Validar e criar customer
        customer_input = CustomerCreate.model_validate(data)
        
        # Salvar via repository
        repo = get_customer_repository()
        customer = repo.create_from_schema(customer_input)
        
        return f"Successfully added customer: {customer.first_name} {customer.last_name} (ID: {customer.id})"
    
    except Exception as e:
        raise RuntimeError(f"Failed to add customer: {str(e)}")


# ============================================
# TOOLS REFATORADAS
# ============================================

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
    args_schema: Type[BaseModel] = ExpenseCreate  # ← Usar *Create schema
    model: Type[BaseModel] = Expense  # ← Modelo de retorno completo
    
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
            result = add_expense_to_db(kwargs)
            return ToolResult(success=True, content=result)
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
    args_schema: Type[BaseModel] = RevenueCreate  # ← Usar *Create schema
    model: Type[BaseModel] = Revenue  # ← Modelo de retorno completo
    
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
            result = add_revenue_to_db(kwargs)
            return ToolResult(success=True, content=result)
        except Exception as e:
            return ToolResult(success=False, content=str(e))


class AddCustomerTool(Tool):
    """
    Tool para adicionar clientes ao banco de dados.
    
    Usa Supabase via repository pattern.
    """
    name: str = "add_customer"
    description: str = "Add a customer to the database with their contact and address information."
    args_schema: Type[BaseModel] = CustomerCreate  # ← Usar *Create schema
    model: Type[BaseModel] = Customer  # ← Modelo de retorno completo
    
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
            result = add_customer_to_db(kwargs)
            return ToolResult(success=True, message=result)
        except Exception as e:
            return ToolResult(success=False, message=str(e))


# ============================================
# INSTÂNCIAS DAS TOOLS (SINGLETON)
# ============================================

add_expense_tool = AddExpenseTool()
add_revenue_tool = AddRevenueTool()
add_customer_tool = AddCustomerTool()


# ============================================
# VERSÃO ALTERNATIVA: Factory Pattern
# ============================================

def create_add_tool(
    name: str,
    description: str,
    create_schema: Type[BaseModel],
    model_class: Type[BaseModel],
    add_function: callable
) -> Tool:
    """
    Factory para criar tools de adição padronizadas.
    
    Args:
        name: Nome da tool
        description: Descrição da tool
        create_schema: Schema Pydantic para entrada (ex: ExpenseCreate)
        model_class: Modelo Pydantic completo (ex: Expense)
        add_function: Função que adiciona ao DB
        
    Returns:
        Instância configurada da Tool
        
    Example:
        >>> add_expense_tool = create_add_tool(
        ...     name="add_expense",
        ...     description="Add expense to database",
        ...     create_schema=ExpenseCreate,
        ...     model_class=Expense,
        ...     add_function=add_expense_to_db
        ... )
    """
    
    class DynamicAddTool(Tool):
        def execute(self, **kwargs) -> ToolResult:
            try:
                result = add_function(kwargs)
                return ToolResult(success=True, content=result)
            except Exception as e:
                return ToolResult(success=False, content=str(e))
        
        def _run(self, **kwargs) -> ToolResult:
            return self.execute(**kwargs)
        
        async def _arun(self, **kwargs) -> ToolResult:
            return self._run(**kwargs)
    
    return DynamicAddTool(
        name=name,
        description=description,
        args_schema=create_schema,
        model=model_class
    )


# Usar factory para criar tools (alternativa)
"""
add_expense_tool_v2 = create_add_tool(
    name="add_expense",
    description="Add an expense to the database. Tax rate is 0.19.",
    create_schema=ExpenseCreate,
    model_class=Expense,
    add_function=add_expense_to_db
)

add_revenue_tool_v2 = create_add_tool(
    name="add_revenue",
    description="Add a revenue entry to the database. Tax rate is 0.19.",
    create_schema=RevenueCreate,
    model_class=Revenue,
    add_function=add_revenue_to_db
)

add_customer_tool_v2 = create_add_tool(
    name="add_customer",
    description="Add a customer to the database.",
    create_schema=CustomerCreate,
    model_class=Customer,
    add_function=add_customer_to_db
)
"""
