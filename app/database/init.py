from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List

from app.core.logging import get_logger
from app.database.connection import check_database_connection, get_db_session
from app.database.migrations import initialize_database
from app.database.models import (
    AccountDB,
    AccountValueDB,
    DataIngestionLogDB,
    FinancialRecordDB,
)
from app.models.financial import AccountType, SourceType

logger = get_logger(__name__)


def setup_database() -> bool:
    """
    database setup including initialization and optional sample data.

    Returns:
        True if setup was successful, False otherwise
    """
    try:
        from app.core.config import get_settings

        settings = get_settings()

        logger.info("Starting database setup...")

        # Check database connection
        if not check_database_connection():
            logger.error("Database connection failed")
            return False

        # Initialize database with migrations
        if not initialize_database():
            logger.error("Database initialization failed")
            return False

        # Optionally create sample data based on configuration
        if settings.CREATE_SAMPLE_DATA_ON_INIT:
            logger.info("Creating sample data as configured...")
            if not create_sample_data():
                logger.warning("Sample data creation failed, but continuing with setup")
        else:
            logger.info("Skipping sample data creation (not configured)")

        logger.info("Database setup completed successfully")
        return True

    except Exception as e:
        logger.error("Database setup failed: %s", str(e))
        return False


def create_sample_accounts() -> bool:
    """
    Create sample accounts for testing and development.

    Returns:
        True if sample accounts were created successfully
    """
    try:
        logger.info("Creating sample accounts...")

        sample_accounts = [
            # Revenue accounts
            {
                "account_id": "REV_001",
                "name": "Product Sales Revenue",
                "account_type": AccountType.REVENUE.value,
                "source": SourceType.QUICKBOOKS.value,
                "description": "Revenue from product sales",
            },
            {
                "account_id": "REV_002",
                "name": "Service Revenue",
                "account_type": AccountType.REVENUE.value,
                "source": SourceType.QUICKBOOKS.value,
                "description": "Revenue from services",
            },
            {
                "account_id": "REV_003",
                "name": "Subscription Revenue",
                "account_type": AccountType.REVENUE.value,
                "source": SourceType.ROOTFI.value,
                "description": "Recurring subscription revenue",
            },
            # Expense accounts
            {
                "account_id": "EXP_001",
                "name": "Operating Expenses",
                "account_type": AccountType.EXPENSE.value,
                "source": SourceType.QUICKBOOKS.value,
                "description": "General operating expenses",
            },
            {
                "account_id": "EXP_002",
                "name": "Payroll Expenses",
                "account_type": AccountType.EXPENSE.value,
                "source": SourceType.QUICKBOOKS.value,
                "parent_account_id": "EXP_001",
                "description": "Employee salaries and benefits",
            },
            {
                "account_id": "EXP_003",
                "name": "Marketing Expenses",
                "account_type": AccountType.EXPENSE.value,
                "source": SourceType.ROOTFI.value,
                "description": "Marketing and advertising costs",
            },
            {
                "account_id": "EXP_004",
                "name": "Office Rent",
                "account_type": AccountType.EXPENSE.value,
                "source": SourceType.QUICKBOOKS.value,
                "parent_account_id": "EXP_001",
                "description": "Monthly office rent payments",
            },
            # Asset accounts
            {
                "account_id": "AST_001",
                "name": "Cash and Cash Equivalents",
                "account_type": AccountType.ASSET.value,
                "source": SourceType.QUICKBOOKS.value,
                "description": "Cash in bank accounts",
            },
            {
                "account_id": "AST_002",
                "name": "Accounts Receivable",
                "account_type": AccountType.ASSET.value,
                "source": SourceType.ROOTFI.value,
                "description": "Money owed by customers",
            },
        ]

        with get_db_session() as session:
            for account_data in sample_accounts:
                # Check if account already exists
                existing = (
                    session.query(AccountDB)
                    .filter(AccountDB.account_id == account_data["account_id"])
                    .first()
                )

                if not existing:
                    account = AccountDB(**account_data)
                    session.add(account)
                    logger.debug(
                        "Created sample account: %s", account_data["account_id"]
                    )

        logger.info("Sample accounts created successfully")
        return True

    except Exception as e:
        logger.error("Failed to create sample accounts: %s", str(e))
        return False


def create_sample_financial_records() -> bool:
    """
    Create sample financial records for testing and development.

    Returns:
        True if sample records were created successfully
    """
    try:
        logger.info("Creating sample financial records...")

        from app.core.config import get_settings

        settings = get_settings()

        sample_records = [
            {
                "id": "FR_2024_Q1",
                "source": SourceType.QUICKBOOKS.value,
                "period_start": date(2024, 1, 1),
                "period_end": date(2024, 3, 31),
                "currency": settings.SAMPLE_DATA_CURRENCY,
                "revenue": Decimal("150000.00"),
                "expenses": Decimal("120000.00"),
                "net_profit": Decimal("30000.00"),
                "raw_data": '{"source": "quickbooks", "quarter": "Q1_2024"}',
            },
            {
                "id": "FR_2024_Q2",
                "source": SourceType.ROOTFI.value,
                "period_start": date(2024, 4, 1),
                "period_end": date(2024, 6, 30),
                "currency": settings.SAMPLE_DATA_CURRENCY,
                "revenue": Decimal("175000.00"),
                "expenses": Decimal("135000.00"),
                "net_profit": Decimal("40000.00"),
                "raw_data": '{"source": "rootfi", "quarter": "Q2_2024"}',
            },
            {
                "id": "FR_2024_Q3",
                "source": SourceType.QUICKBOOKS.value,
                "period_start": date(2024, 7, 1),
                "period_end": date(2024, 9, 30),
                "currency": settings.SAMPLE_DATA_CURRENCY,
                "revenue": Decimal("200000.00"),
                "expenses": Decimal("150000.00"),
                "net_profit": Decimal("50000.00"),
                "raw_data": '{"source": "quickbooks", "quarter": "Q3_2024"}',
            },
        ]

        with get_db_session() as session:
            for record_data in sample_records:
                # Check if record already exists
                existing = (
                    session.query(FinancialRecordDB)
                    .filter(FinancialRecordDB.id == record_data["id"])
                    .first()
                )

                if not existing:
                    record = FinancialRecordDB(**record_data)
                    session.add(record)
                    logger.debug(
                        "Created sample financial record: %s", record_data["id"]
                    )

        logger.info("Sample financial records created successfully")
        return True

    except Exception as e:
        logger.error("Failed to create sample financial records: %s", str(e))
        return False


def create_sample_account_values() -> bool:
    """
    Create sample account values linking accounts to financial records.

    Returns:
        True if sample account values were created successfully
    """
    try:
        logger.info("Creating sample account values...")

        sample_values = [
            # Q1 2024 values
            {
                "account_id": "REV_001",
                "financial_record_id": "FR_2024_Q1",
                "value": Decimal("80000.00"),
            },
            {
                "account_id": "REV_002",
                "financial_record_id": "FR_2024_Q1",
                "value": Decimal("70000.00"),
            },
            {
                "account_id": "EXP_002",
                "financial_record_id": "FR_2024_Q1",
                "value": Decimal("60000.00"),
            },
            {
                "account_id": "EXP_003",
                "financial_record_id": "FR_2024_Q1",
                "value": Decimal("25000.00"),
            },
            {
                "account_id": "EXP_004",
                "financial_record_id": "FR_2024_Q1",
                "value": Decimal("35000.00"),
            },
            # Q2 2024 values
            {
                "account_id": "REV_001",
                "financial_record_id": "FR_2024_Q2",
                "value": Decimal("90000.00"),
            },
            {
                "account_id": "REV_003",
                "financial_record_id": "FR_2024_Q2",
                "value": Decimal("85000.00"),
            },
            {
                "account_id": "EXP_002",
                "financial_record_id": "FR_2024_Q2",
                "value": Decimal("65000.00"),
            },
            {
                "account_id": "EXP_003",
                "financial_record_id": "FR_2024_Q2",
                "value": Decimal("30000.00"),
            },
            {
                "account_id": "EXP_004",
                "financial_record_id": "FR_2024_Q2",
                "value": Decimal("40000.00"),
            },
            # Q3 2024 values
            {
                "account_id": "REV_001",
                "financial_record_id": "FR_2024_Q3",
                "value": Decimal("110000.00"),
            },
            {
                "account_id": "REV_002",
                "financial_record_id": "FR_2024_Q3",
                "value": Decimal("90000.00"),
            },
            {
                "account_id": "EXP_002",
                "financial_record_id": "FR_2024_Q3",
                "value": Decimal("70000.00"),
            },
            {
                "account_id": "EXP_003",
                "financial_record_id": "FR_2024_Q3",
                "value": Decimal("35000.00"),
            },
            {
                "account_id": "EXP_004",
                "financial_record_id": "FR_2024_Q3",
                "value": Decimal("45000.00"),
            },
        ]

        with get_db_session() as session:
            for value_data in sample_values:
                # Check if account value already exists
                existing = (
                    session.query(AccountValueDB)
                    .filter(
                        AccountValueDB.account_id == value_data["account_id"],
                        AccountValueDB.financial_record_id
                        == value_data["financial_record_id"],
                    )
                    .first()
                )

                if not existing:
                    account_value = AccountValueDB(**value_data)
                    session.add(account_value)
                    logger.debug(
                        "Created account value: %s -> %s",
                        value_data["account_id"],
                        value_data["financial_record_id"],
                    )

        logger.info("Sample account values created successfully")
        return True

    except Exception as e:
        logger.error("Failed to create sample account values: %s", str(e))
        return False


def create_sample_data() -> bool:
    """
    Create all sample data for testing and development.

    Returns:
        True if all sample data was created successfully
    """
    try:
        logger.info("Creating sample data...")

        success = (
            create_sample_accounts()
            and create_sample_financial_records()
            and create_sample_account_values()
        )

        if success:
            logger.info("All sample data created successfully")
        else:
            logger.error("Failed to create some sample data")

        return success

    except Exception as e:
        logger.error("Failed to create sample data: %s", str(e))
        return False


def reset_database_with_sample_data() -> bool:
    """
    Reset the database and populate it with sample data.

    WARNING: This will delete all existing data!

    Returns:
        True if reset and sample data creation was successful
    """
    try:
        logger.warning("Resetting database with sample data...")

        from app.database.connection import reset_database

        # Reset the database (drops and recreates tables)
        reset_database()

        # Create sample data
        success = create_sample_data()

        if success:
            logger.info("Database reset with sample data completed successfully")
        else:
            logger.error("Database reset completed but sample data creation failed")

        return success

    except Exception as e:
        logger.error("Failed to reset database with sample data: %s", str(e))
        return False
