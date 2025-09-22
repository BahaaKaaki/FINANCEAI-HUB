import json
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from app.core.logging import get_logger
from app.models.financial import (
    Account,
    AccountCreate,
    AccountType,
    AccountValue,
    AccountValueCreate,
    FinancialRecord,
    FinancialRecordCreate,
    SourceType,
)

logger = get_logger(__name__)


class QuickBooksParseError(Exception):
    """Custom exception for QuickBooks parsing errors."""

    pass


class QuickBooksParser:
    """
    Parser for QuickBooks P&L JSON format with monthly columns.
    """

    def __init__(self):
        """Initialize the QuickBooks parser."""
        self.currency = "USD"
        self.periods = []
        self.accounts = {}
        self.account_values = []

    def parse_file(
        self, file_path: str
    ) -> Tuple[
        List[FinancialRecordCreate], List[AccountCreate], List[AccountValueCreate]
    ]:
        """
        Parse QuickBooks P&L JSON file.

        Args:
            file_path: Path to the QuickBooks JSON file

        Returns:
            Tuple of (financial_records, accounts, account_values)

        Raises:
            QuickBooksParseError: If parsing fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return self.parse_data(data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Failed to load QuickBooks file %s: %s", file_path, str(e))
            raise QuickBooksParseError(f"Failed to load file {file_path}: {str(e)}")

    def parse_data(
        self, data: Dict[str, Any]
    ) -> Tuple[
        List[FinancialRecordCreate], List[AccountCreate], List[AccountValueCreate]
    ]:
        """
        Parse QuickBooks P&L data structure.

        Args:
            data: QuickBooks JSON data structure

        Returns:
            Tuple of (financial_records, accounts, account_values)

        Raises:
            QuickBooksParseError: If parsing fails
        """
        try:

            self.currency = "USD"
            self.periods = []
            self.accounts = {}
            self.account_values = []

            header = data.get("data", {}).get("Header", {})
            self._parse_header(header)

            columns = data.get("data", {}).get("Columns", {}).get("Column", [])
            self._parse_columns(columns)

            rows = data.get("data", {}).get("Rows", {}).get("Row", [])
            self._parse_rows(rows)

            financial_records = self._generate_financial_records()

            accounts_create = [
                AccountCreate(**account) for account in self.accounts.values()
            ]
            account_values_create = [
                AccountValueCreate(**av) for av in self.account_values
            ]

            logger.info(
                "Successfully parsed QuickBooks data: %d periods, %d accounts, %d account values",
                len(financial_records),
                len(accounts_create),
                len(account_values_create),
            )

            return financial_records, accounts_create, account_values_create

        except Exception as e:
            logger.error("Failed to parse QuickBooks data: %s", str(e))
            raise QuickBooksParseError(f"Failed to parse QuickBooks data: {str(e)}")

    def _parse_header(self, header: Dict[str, Any]) -> None:
        """
        Parse header information to extract currency and metadata.

        Args:
            header: Header section from QuickBooks data
        """
        self.currency = header.get("Currency", "USD")

        # Log header information for debugging
        logger.debug(
            "Parsed header - Currency: %s, Report: %s, Basis: %s",
            self.currency,
            header.get("ReportName", "Unknown"),
            header.get("ReportBasis", "Unknown"),
        )

    def _parse_columns(self, columns: List[Dict[str, Any]]) -> None:
        """
        Parse column definitions to extract time periods.

        Args:
            columns: List of column definitions from QuickBooks data
        """
        self.periods = []

        for col in columns:
            if col.get("ColType") == "Money":

                metadata = {
                    item["Name"]: item["Value"] for item in col.get("MetaData", [])
                }

                if "StartDate" in metadata and "EndDate" in metadata:
                    try:
                        start_date = datetime.strptime(
                            metadata["StartDate"], "%Y-%m-%d"
                        ).date()
                        end_date = datetime.strptime(
                            metadata["EndDate"], "%Y-%m-%d"
                        ).date()

                        period_info = {
                            "title": col.get("ColTitle", ""),
                            "start_date": start_date,
                            "end_date": end_date,
                            "col_key": metadata.get("ColKey", ""),
                        }
                        self.periods.append(period_info)

                    except ValueError as e:
                        logger.warning(
                            "Failed to parse date in column %s: %s",
                            col.get("ColTitle", ""),
                            str(e),
                        )

        logger.debug("Parsed %d time periods from columns", len(self.periods))

    def _parse_rows(
        self,
        rows: List[Dict[str, Any]],
        parent_account_id: Optional[str] = None,
        level: int = 0,
    ) -> None:
        """
        Recursively parse account rows to extract hierarchical account data.

        Args:
            rows: List of row data from QuickBooks
            parent_account_id: Parent account ID for hierarchical structure
            level: Current nesting level for logging
        """
        for row in rows:

            if "Header" in row:
                self._parse_account_row(row["Header"], parent_account_id, level)

            if "Rows" in row and "Row" in row["Rows"]:
                nested_rows = row["Rows"]["Row"]
                # Use the account ID from the current row as parent for nested rows
                current_account_id = self._extract_account_id_from_row(
                    row.get("Header", {})
                )
                self._parse_rows(nested_rows, current_account_id, level + 1)

    def _parse_account_row(
        self, header: Dict[str, Any], parent_account_id: Optional[str], level: int
    ) -> None:
        """
        Parse individual account row to extract account information and values.

        Args:
            header: Header section of the row containing account data
            parent_account_id: Parent account ID for hierarchical structure
            level: Current nesting level
        """
        col_data = header.get("ColData", [])
        if not col_data:
            return

        # First column contains account information
        account_col = col_data[0]
        account_name = account_col.get("value", "").strip()
        account_id = account_col.get("id")

        # Skip empty or summary rows
        if not account_name or account_name in ["", "TOTAL"]:
            return

        if not account_id:
            account_id = self._generate_account_id(account_name, parent_account_id)

        account_type = self._determine_account_type(account_name, level)

        # Store account information
        if account_id not in self.accounts:
            self.accounts[account_id] = {
                "account_id": account_id,
                "name": account_name,
                "account_type": account_type,
                "parent_account_id": parent_account_id,
                "source": SourceType.QUICKBOOKS,
                "description": f"QuickBooks account at level {level}",
                "is_active": True,
            }

        # Parse monetary values for each period
        self._parse_account_values(
            account_id, col_data[1:]
        )  # Skip first column (account name)

    def _parse_account_values(
        self, account_id: str, value_columns: List[Dict[str, Any]]
    ) -> None:
        """
        Parse monetary values for an account across all periods.

        Args:
            account_id: Account identifier
            value_columns: List of value columns corresponding to time periods
        """
        for i, col in enumerate(value_columns):
            if i >= len(self.periods):
                break  # More values than periods defined

            value_str = col.get("value", "").strip()
            if not value_str or value_str == "":
                continue

            try:

                value = Decimal(value_str)

                period = self.periods[i]
                record_id = self._generate_record_id(
                    period["start_date"], period["end_date"]
                )

                account_value = {
                    "account_id": account_id,
                    "financial_record_id": record_id,
                    "value": value,
                }
                self.account_values.append(account_value)

            except (InvalidOperation, ValueError) as e:
                logger.warning(
                    "Failed to parse value '%s' for account %s: %s",
                    value_str,
                    account_id,
                    str(e),
                )

    def _generate_financial_records(self) -> List[FinancialRecordCreate]:
        """
        Generate financial records for each period based on parsed account values.

        Returns:
            List of FinancialRecordCreate objects
        """
        financial_records = []

        for period in self.periods:
            record_id = self._generate_record_id(
                period["start_date"], period["end_date"]
            )

            revenue, expenses = self._calculate_period_totals(record_id)

            # Create financial record
            financial_record_data = {
                "source": SourceType.QUICKBOOKS,
                "period_start": period["start_date"],
                "period_end": period["end_date"],
                "currency": self.currency,
                "revenue": revenue,
                "expenses": expenses,
                "raw_data": {
                    "period_title": period["title"],
                    "col_key": period["col_key"],
                    "parser_version": "1.0",
                    "record_id": record_id,
                },
            }

            financial_record = FinancialRecordCreate(**financial_record_data)
            financial_records.append(financial_record)

        return financial_records

    def _calculate_period_totals(self, record_id: str) -> Tuple[Decimal, Decimal]:
        """
        Calculate revenue and expense totals for a specific period.

        Args:
            record_id: Financial record ID for the period

        Returns:
            Tuple of (revenue, expenses)
        """
        revenue = Decimal("0.00")
        expenses = Decimal("0.00")

        for account_value in self.account_values:
            if account_value["financial_record_id"] != record_id:
                continue

            account_id = account_value["account_id"]
            if account_id not in self.accounts:
                continue

            account = self.accounts[account_id]
            value = account_value["value"]

            if account["account_type"] == AccountType.REVENUE:
                revenue += abs(value)  # Revenue should be positive
            elif account["account_type"] == AccountType.EXPENSE:
                expenses += abs(value)  # Expenses should be positive

        return revenue, expenses

    def _extract_account_id_from_row(self, header: Dict[str, Any]) -> Optional[str]:
        """
        Extract account ID from a row header.

        Args:
            header: Row header containing account data

        Returns:
            Account ID if found, None otherwise
        """
        col_data = header.get("ColData", [])
        if col_data:
            return col_data[0].get("id")
        return None

    def _generate_account_id(
        self, account_name: str, parent_account_id: Optional[str]
    ) -> str:
        """
        Generate a unique account ID based on name and parent.

        Args:
            account_name: Name of the account
            parent_account_id: Parent account ID

        Returns:
            Generated account ID
        """

        base_name = account_name.lower().replace(" ", "_").replace("-", "_")
        if parent_account_id:
            return f"{parent_account_id}_{base_name}"
        return f"qb_{base_name}"

    def _generate_record_id(self, start_date: date, end_date: date) -> str:
        """
        Generate a unique financial record ID for a period.

        Args:
            start_date: Period start date
            end_date: Period end date

        Returns:
            Generated record ID
        """
        return f"qb_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

    def _determine_account_type(self, account_name: str, level: int) -> AccountType:
        """
        Determine account type based on name and hierarchical level.

        Args:
            account_name: Name of the account
            level: Hierarchical level of the account

        Returns:
            Determined AccountType
        """
        name_lower = account_name.lower()

        # Liability indicators (check first to avoid conflicts)
        if any(
            keyword in name_lower
            for keyword in ["payable", "loan", "debt", "liability", "accrued"]
        ):
            return AccountType.LIABILITY

        # Revenue indicators
        if any(
            keyword in name_lower
            for keyword in [
                "income",
                "revenue",
                "sales",
                "service",
                "consulting",
                "subscription",
            ]
        ):
            return AccountType.REVENUE

        # Expense indicators
        if any(
            keyword in name_lower
            for keyword in [
                "expense",
                "cost",
                "payroll",
                "rent",
                "utilities",
                "marketing",
                "travel",
                "supplies",
                "insurance",
                "legal",
                "accounting",
            ]
        ):
            return AccountType.EXPENSE

        # Asset indicators
        if any(
            keyword in name_lower
            for keyword in [
                "cash",
                "bank",
                "receivable",
                "inventory",
                "equipment",
                "asset",
            ]
        ):
            return AccountType.ASSET

        # Default based on level - top level accounts are usually categories
        if level == 0:
            if "income" in name_lower or name_lower == "income":
                return AccountType.REVENUE
            else:
                return AccountType.EXPENSE

        # Default to expense for unknown accounts
        return AccountType.EXPENSE


def parse_quickbooks_file(
    file_path: str,
) -> Tuple[List[FinancialRecordCreate], List[AccountCreate], List[AccountValueCreate]]:
    """
    Convenience function to parse a QuickBooks file.

    Args:
        file_path: Path to the QuickBooks JSON file

    Returns:
        Tuple of (financial_records, accounts, account_values)

    Raises:
        QuickBooksParseError: If parsing fails
    """
    parser = QuickBooksParser()
    return parser.parse_file(file_path)
