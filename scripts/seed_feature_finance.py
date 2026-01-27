"""
Seed script for Finance feature.
Populates initial financial data: revenues, expenses, customers, and invoices.
"""

from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

# Add src to path if needed
# sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.config import settings
from src.core.utils import configure_logging, get_db, get_logger
from src.modules.ai.engines.lchain.feature.finance.models.models import (
    CustomerCreate, ExpenseCreate, InvoiceCreate, RevenueCreate)
# Import finance repositories and models
from src.modules.ai.engines.lchain.feature.finance.repositories.repository_finance import (
    get_customer_repository, get_expense_repository, get_invoice_repository,
    get_revenue_repository)

configure_logging()
logger = get_logger(__name__)


def seed_customers(customer_repo):
    """
    Seed customer data.

    Returns:
        List of created/existing customers
    """
    logger.info("Seeding customers...")

    customers_data = [
        {
            "company_name": "Tech Solutions Inc.",
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1-234-567-89",
            "address": "123 Elm Street",
            "city": "Tech City",
            "zip": "45678",
            "country": "USA",
        },
        {
            "company_name": None,
            "first_name": "Jane",
            "last_name": "Smith",
            "phone": "+1-987-654-321",
            "address": "456 Oak Street",
            "city": "Innovate Town",
            "zip": "78901",
            "country": "Canada",
        },
        {
            "company_name": "Future Ventures",
            "first_name": "Albert",
            "last_name": "Einstein",
            "phone": "+49-555-666-777",
            "address": "789 Pine Avenue",
            "city": "Science City",
            "zip": "12345",
            "country": "Germany",
        },
    ]

    customers = []
    for data in customers_data:
        # Check if customer exists by phone
        existing = customer_repo.get_by_phone(data["phone"])
        if existing:
            logger.info(
                f"Customer {data['first_name']} {data['last_name']} already exists"
            )
            customers.append(existing)
        else:
            customer_input = CustomerCreate(**data)
            customer = customer_repo.create_from_schema(customer_input)
            logger.info(
                f"Created customer: {customer.first_name} {customer.last_name} "
                f"(ID: {customer.id})"
            )
            customers.append(customer)

    return customers


def seed_revenues(revenue_repo):
    """
    Seed revenue data.

    Returns:
        List of created/existing revenues
    """
    logger.info("Seeding revenues...")

    revenues_data = [
        {
            "description": "Website development",
            "net_amount": 1000.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 1, 15),
        },
        {
            "description": "Consulting services",
            "net_amount": 2000.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 2, 10),
        },
        {
            "description": "Annual subscription",
            "net_amount": 500.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 3, 5),
        },
    ]

    revenues = []
    for data in revenues_data:
        # Check if revenue exists by description and date
        filters = {"description": data["description"], "date": data["date"].isoformat()}
        existing_list = revenue_repo.find_by(filters, limit=1)

        if existing_list:
            logger.info(f"Revenue '{data['description']}' already exists")
            revenues.append(existing_list[0])
        else:
            revenue_input = RevenueCreate(**data)
            revenue = revenue_repo.create_from_schema(revenue_input)
            logger.info(
                f"Created revenue: {revenue.description} "
                f"(ID: {revenue.id}, Amount: {revenue.gross_amount})"
            )
            revenues.append(revenue)

    return revenues


def seed_expenses(expense_repo):
    """
    Seed expense data.

    Returns:
        List of created/existing expenses
    """
    logger.info("Seeding expenses...")

    expenses_data = [
        {
            "description": "Office supplies",
            "net_amount": 300.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 1, 20),
        },
        {
            "description": "Cloud hosting",
            "net_amount": 150.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 2, 5),
        },
        {
            "description": "Marketing campaign",
            "net_amount": 1200.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 2, 28),
        },
    ]

    expenses = []
    for data in expenses_data:
        # Check if expense exists by description and date
        filters = {"description": data["description"], "date": data["date"].isoformat()}
        existing_list = expense_repo.find_by(filters, limit=1)

        if existing_list:
            logger.info(f"Expense '{data['description']}' already exists")
            expenses.append(existing_list[0])
        else:
            expense_input = ExpenseCreate(**data)
            expense = expense_repo.create_from_schema(expense_input)
            logger.info(
                f"Created expense: {expense.description} "
                f"(ID: {expense.id}, Amount: {expense.gross_amount})"
            )
            expenses.append(expense)

    return expenses


def seed_invoices(invoice_repo, customers):
    """
    Seed invoice data.

    Args:
        customers: List of customer objects to reference

    Returns:
        List of created/existing invoices
    """
    logger.info("Seeding invoices...")

    # Map customer names to IDs for easier reference
    customer_map = {(c.first_name, c.last_name): c.id for c in customers}

    invoices_data = [
        {
            "customer_id": customer_map.get(("John", "Doe")),
            "invoice_number": "INV-1001",
            "description": "Monthly retainer",
            "amount": 1190.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 1, 31),
        },
        {
            "customer_id": customer_map.get(("Jane", "Smith")),
            "invoice_number": "INV-1002",
            "description": "Project completion",
            "amount": 2380.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 2, 15),
        },
        {
            "customer_id": customer_map.get(("Albert", "Einstein")),
            "invoice_number": "INV-1003",
            "description": "Software license",
            "amount": 595.0,
            "tax_rate": 0.19,
            "date": datetime(2024, 3, 10),
        },
    ]

    invoices = []
    for data in invoices_data:
        # Skip if customer not found
        if data["customer_id"] is None:
            logger.warning(
                f"Skipping invoice {data['invoice_number']}: customer not found"
            )
            continue

        # Check if invoice exists by invoice_number
        existing = invoice_repo.get_by_invoice_number(data["invoice_number"])

        if existing:
            logger.info(f"Invoice {data['invoice_number']} already exists")
            invoices.append(existing)
        else:
            invoice_input = InvoiceCreate(**data)
            invoice = invoice_repo.create_from_schema(invoice_input)
            logger.info(
                f"Created invoice: {invoice.invoice_number} "
                f"(ID: {invoice.id}, Amount: {invoice.amount})"
            )
            invoices.append(invoice)

    return invoices


def clear_finance_data(revenue_repo, expense_repo, customer_repo, invoice_repo):
    """
    Clear all finance data (use with caution!).
    Only use this in development/testing environments.
    """
    logger.warning("CLEARING ALL FINANCE DATA - This action cannot be undone!")

    try:
        # Delete in correct order (respecting foreign keys)
        # Invoices first (reference customers)
        invoices = invoice_repo.find_all(limit=1000)
        for invoice in invoices:
            invoice_repo.delete(invoice.id)
        logger.info(f"Deleted {len(invoices)} invoices")

        # Then customers
        customers = customer_repo.find_all(limit=1000)
        for customer in customers:
            customer_repo.delete(customer.id)
        logger.info(f"Deleted {len(customers)} customers")

        # Revenues (no foreign keys)
        revenues = revenue_repo.find_all(limit=1000)
        for revenue in revenues:
            revenue_repo.delete(revenue.id)
        logger.info(f"Deleted {len(revenues)} revenues")

        # Expenses (no foreign keys)
        expenses = expense_repo.find_all(limit=1000)
        for expense in expenses:
            expense_repo.delete(expense.id)
        logger.info(f"Deleted {len(expenses)} expenses")

        logger.info("All finance data cleared successfully")

    except Exception as e:
        logger.error(f"Error clearing finance data: {e}")
        raise


def main(clear_data: bool = False):
    """
    Main seed function for finance feature.

    Args:
        clear_data: If True, clear existing data before seeding (use with caution!)
    """
    logger.info("Starting finance seed process...")

    try:
        db_client = get_db()

        # Initialize repositories
        revenue_repo = get_revenue_repository()
        expense_repo = get_expense_repository()
        customer_repo = get_customer_repository()
        invoice_repo = get_invoice_repository()

        # Clear data if requested (CAREFUL!)
        if clear_data:
            response = input(
                "WARNING: This will DELETE ALL finance data. " "Type 'YES' to confirm: "
            )
            if response == "YES":
                clear_finance_data(
                    revenue_repo, expense_repo, customer_repo, invoice_repo
                )
            else:
                logger.info("Data clearing cancelled")
                return

        # Seed data in correct order
        # 1. Customers first (no dependencies)
        customers = seed_customers(customer_repo)

        # 2. Revenues (no dependencies)
        revenues = seed_revenues(revenue_repo)

        # 3. Expenses (no dependencies)
        expenses = seed_expenses(expense_repo)

        # 4. Invoices last (depend on customers)
        invoices = seed_invoices(invoice_repo, customers)

        # Summary
        logger.info("\n" + "=" * 50)
        logger.info("Finance Seed Summary:")
        logger.info(f"  Customers: {len(customers)}")
        logger.info(f"  Revenues:  {len(revenues)}")
        logger.info(f"  Expenses:  {len(expenses)}")
        logger.info(f"  Invoices:  {len(invoices)}")
        logger.info("=" * 50)
        logger.info("Finance seed process completed successfully!")

        # Calculate and display financial summary
        total_revenue = sum(r.gross_amount for r in revenues)
        total_expense = sum(e.gross_amount for e in expenses)
        profit = total_revenue - total_expense

        logger.info("\nFinancial Summary:")
        logger.info(f"  Total Revenue: ${total_revenue:.2f}")
        logger.info(f"  Total Expense: ${total_expense:.2f}")
        logger.info(f"  Profit:        ${profit:.2f}")

    except Exception as e:
        logger.error(f"Error during finance seed process: {e}")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed finance data")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before seeding (DANGEROUS!)",
    )

    args = parser.parse_args()
    main(clear_data=args.clear)
