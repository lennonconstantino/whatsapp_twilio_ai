import pytest
from unittest.mock import MagicMock
from src.modules.ai.engines.lchain.feature.finance.tools.add import AddExpenseTool, AddRevenueTool, AddCustomerTool
from src.modules.ai.engines.lchain.feature.finance.models.models import Expense, Revenue, Customer

from src.modules.ai.engines.lchain.feature.finance.repositories.expense_repository import ExpenseRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.revenue_repository import RevenueRepository
from src.modules.ai.engines.lchain.feature.finance.repositories.customer_repository import CustomerRepository

class TestAddTools:
    @pytest.fixture
    def mock_expense_repo(self):
        return MagicMock(spec=ExpenseRepository)

    @pytest.fixture
    def mock_revenue_repo(self):
        return MagicMock(spec=RevenueRepository)

    @pytest.fixture
    def mock_customer_repo(self):
        return MagicMock(spec=CustomerRepository)

    def test_add_expense_success(self, mock_expense_repo):
        tool = AddExpenseTool(repository=mock_expense_repo)
        
        # Mock repository return
        mock_expense = Expense(
            id=1,
            description="Office Supplies",
            net_amount=100.0,
            gross_amount=119.0, # 19% tax
            tax_rate=0.19,
            date="2023-01-01"
        )
        mock_expense_repo.create_from_schema.return_value = mock_expense
        
        # Add required fields for validation (tax_rate is computed but for test we pass simple case)
        # Actually ExpenseCreate validator calculates gross/tax if missing, but we need at least 2 of 3
        # Or if we provide just net, we might need tax_rate default? No, tax_rate is mandatory in Base
        # But wait, the validators in ExpenseBase (check_net_gross) allow inferring one from other two.
        # So we need to provide at least 2 fields or provide all required ones.
        # Let's provide net_amount and tax_rate
        result = tool._run(description="Office Supplies", net_amount=100.0, tax_rate=0.19, date="2023-01-01")
        
        assert result.success is True
        assert "Successfully added expense" in result.content
        assert "119.0" in result.content
        mock_expense_repo.create_from_schema.assert_called_once()

    def test_add_expense_error(self, mock_expense_repo):
        tool = AddExpenseTool(repository=mock_expense_repo)
        mock_expense_repo.create_from_schema.side_effect = Exception("Database error")
        
        result = tool._run(description="Office Supplies", net_amount=100.0, tax_rate=0.19, date="2023-01-01")
        
        assert result.success is False
        assert "Database error" in result.content

    def test_add_revenue_success(self, mock_revenue_repo):
        tool = AddRevenueTool(repository=mock_revenue_repo)
        
        mock_revenue = Revenue(
            id=1,
            description="Project A",
            net_amount=1000.0,
            gross_amount=1190.0,
            tax_rate=0.19,
            date="2023-01-01"
        )
        mock_revenue_repo.create_from_schema.return_value = mock_revenue
        
        result = tool._run(description="Project A", net_amount=1000.0, tax_rate=0.19, date="2023-01-01")
        
        assert result.success is True
        assert "Successfully added revenue" in result.content
        assert "1190.0" in result.content

    def test_add_customer_success(self, mock_customer_repo):
        tool = AddCustomerTool(repository=mock_customer_repo)
        
        mock_customer = Customer(
            id=1,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="+1234567890",
            address="123 Main St",
            city="Anytown",
            zip="12345",
            country="US"
        )
        mock_customer_repo.create_from_schema.return_value = mock_customer
        
        result = tool._run(
            first_name="John", 
            last_name="Doe", 
            phone="+1234567890",
            address="123 Main St",
            city="Anytown",
            zip="12345",
            country="US"
        )
        
        assert result.success is True
        assert "Successfully added customer" in result.content
        assert "John Doe" in result.content

    def test_add_customer_error(self, mock_customer_repo):
        tool = AddCustomerTool(repository=mock_customer_repo)
        mock_customer_repo.create_from_schema.side_effect = Exception("Invalid email")
        
        result = tool._run(
            first_name="John", 
            last_name="Doe", 
            phone="+1234567890",
            address="123 Main St",
            city="Anytown",
            zip="12345",
            country="US"
        )
        
        assert result.success is False
        assert "Invalid email" in result.content
