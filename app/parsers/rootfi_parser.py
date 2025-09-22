import json
import uuid
from datetime import datetime, date
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


class RootfiParseError(Exception):
    """Custom exception for Rootfi parsing errors."""

    pass


class RootfiParser:
    """
    Parser for Rootfi JSON format with hierarchical line items.
    """

    def __init__(self):
        """Initialize the Rootfi parser."""
        self.currency = "USD"
        self.accounts = {}
        self.account_values = []

    def parse_file(
        self, file_path: str
    ) -> Tuple[
        List[FinancialRecordCreate], List[AccountCreate], List[AccountValueCreate]
    ]:
        """
        Parse Rootfi JSON file.

        Args:
            file_path: Path to the Rootfi JSON file

        Returns:
            Tuple of (financial_records, accounts, account_values)

        Raises:
            RootfiParseError: If parsing fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            return self.parse_data(data)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error("Failed to load Rootfi file %s: %s", file_path, str(e))
            raise RootfiParseError(f"Failed to load file {file_path}: {str(e)}")

    def parse_data(
        self, data: Dict[str, Any]
    ) -> Tuple[
        List[FinancialRecordCreate], List[AccountCreate], List[AccountValueCreate]
    ]:
        """
        Parse Rootfi data structure.

        Args:
            data: Rootfi JSON data structure

        Returns:
            Tuple of (financial_records, accounts, account_values)

        Raises:
            RootfiParseError: If parsing fails
        """
        try:

            self.currency = "USD"
            self.accounts = {}
            self.account_values = []

            data_array = data.get("data", [])
            if not isinstance(data_array, list):
                raise RootfiParseError("Expected 'data' to be an array")

            financial_records = []

            # Process each period record
            for record_data in data_array:
                financial_record = self._parse_period_record(record_data)
                if financial_record:
                    financial_records.append(financial_record)

            accounts_create = [
                AccountCreate(**account) for account in self.accounts.values()
            ]
            account_values_create = [
                AccountValueCreate(**av) for av in self.account_values
            ]

            logger.info(
                "Successfully parsed Rootfi data: %d periods, %d accounts, %d account values",
                len(financial_records),
                len(accounts_create),
                len(account_values_create),
            )

            return financial_records, accounts_create, account_values_create

        except Exception as e:
            logger.error("Failed to parse Rootfi data: %s", str(e))
            raise RootfiParseError(f"Failed to parse Rootfi data: {str(e)}")

    def _parse_period_record(
        self, record_data: Dict[str, Any]
    ) -> Optional[FinancialRecordCreate]:
        """
        Parse a single period record from Rootfi data.

        Args:
            record_data: Single period record from Rootfi data

        Returns:
            FinancialRecordCreate object or None if parsing fails
        """
        try:
            # Extract period info
            period_start_str = record_data.get("period_start")
            period_end_str = record_data.get("period_end")

            if not period_start_str or not period_end_str:
                logger.warning(
                    "Missing period dates in record %s",
                    record_data.get("rootfi_id", "unknown"),
                )
                return None

            period_start = datetime.strptime(period_start_str, "%Y-%m-%d").date()
            period_end = datetime.strptime(period_end_str, "%Y-%m-%d").date()

            record_id = self._generate_record_id(
                period_start, period_end, record_data.get("rootfi_id")
            )

            currency = record_data.get("currency_id", "USD") or "USD"

            total_revenue = self._parse_line_items(
                record_data.get("revenue", []),
                AccountType.REVENUE,
                record_id,
                "revenue",
            )

            total_cogs = self._parse_line_items(
                record_data.get("cost_of_goods_sold", []),
                AccountType.EXPENSE,
                record_id,
                "cost_of_goods_sold",
            )

            total_operating_expenses = self._parse_line_items(
                record_data.get("operating_expenses", []),
                AccountType.EXPENSE,
                record_id,
                "operating_expenses",
            )

            total_non_operating_expenses = self._parse_line_items(
                record_data.get("non_operating_expenses", []),
                AccountType.EXPENSE,
                record_id,
                "non_operating_expenses",
            )

            total_non_operating_revenue = self._parse_line_items(
                record_data.get("non_operating_revenue", []),
                AccountType.REVENUE,
                record_id,
                "non_operating_revenue",
            )

            total_revenue_amount = total_revenue + total_non_operating_revenue
            total_expenses_amount = (
                total_cogs + total_operating_expenses + total_non_operating_expenses
            )

            # Create financial record
            financial_record_data = {
                "source": SourceType.ROOTFI,
                "period_start": period_start,
                "period_end": period_end,
                "currency": currency,
                "revenue": total_revenue_amount,
                "expenses": total_expenses_amount,
                "raw_data": {
                    "rootfi_id": record_data.get("rootfi_id"),
                    "platform_id": record_data.get("platform_id"),
                    "gross_profit": record_data.get("gross_profit"),
                    "operating_profit": record_data.get("operating_profit"),
                    "net_profit": record_data.get("net_profit"),
                    "parser_version": "1.0",
                    "record_id": record_id,
                },
            }

            return FinancialRecordCreate(**financial_record_data)

        except (ValueError, KeyError) as e:
            logger.error(
                "Failed to parse period record %s: %s",
                record_data.get("rootfi_id", "unknown"),
                str(e),
            )
            return None

    def _parse_line_items(
        self,
        line_items: List[Dict[str, Any]],
        account_type: AccountType,
        record_id: str,
        category: str,
        parent_account_id: Optional[str] = None,
    ) -> Decimal:
        """
        Recursively parse hierarchical line items.

        Args:
            line_items: List of line item dictionaries
            account_type: Type of accounts being parsed
            record_id: Financial record ID
            category: Category name for account hierarchy
            parent_account_id: Parent account ID for nested items

        Returns:
            Total value of all line items
        """
        total_value = Decimal("0.00")

        for item in line_items:
            if not isinstance(item, dict):
                continue

            name = item.get("name", "").strip()
            value = item.get("value", 0)
            account_id = item.get("account_id")
            nested_items = item.get("line_items", [])

            if not name:
                continue

            try:
                decimal_value = Decimal(str(value))
                total_value += decimal_value
            except (InvalidOperation, ValueError) as e:
                logger.warning(
                    "Failed to parse value '%s' for item '%s': %s", value, name, str(e)
                )
                continue

            if not account_id:
                account_id = self._generate_account_id(
                    name, category, parent_account_id
                )

            if account_id not in self.accounts:
                self.accounts[account_id] = {
                    "account_id": account_id,
                    "name": name,
                    "account_type": account_type,
                    "parent_account_id": parent_account_id,
                    "source": SourceType.ROOTFI,
                    "description": f"Rootfi {category} account",
                    "is_active": True,
                }

            if decimal_value != Decimal("0.00"):
                account_value = {
                    "account_id": account_id,
                    "financial_record_id": record_id,
                    "value": abs(decimal_value),
                }
                self.account_values.append(account_value)

            if nested_items:
                nested_total = self._parse_line_items(
                    nested_items, account_type, record_id, category, account_id
                )
                # Note: nested_total is already included in total_value from the parent item

        return total_value

    def _generate_account_id(
        self, name: str, category: str, parent_account_id: Optional[str] = None
    ) -> str:
        """
        Generate a unique account ID based on name, category, and parent.

        Args:
            name: Account name
            category: Account category
            parent_account_id: Parent account ID

        Returns:
            Generated account ID
        """

        base_name = name.lower().replace(" ", "_").replace("-", "_").replace("&", "and")
        base_name = "".join(c for c in base_name if c.isalnum() or c == "_")

        if parent_account_id:
            return f"{parent_account_id}_{base_name}"
        return f"rootfi_{category}_{base_name}"

    def _generate_record_id(
        self, start_date: date, end_date: date, rootfi_id: Optional[Any] = None
    ) -> str:
        """
        Generate a unique financial record ID for a period.

        Args:
            start_date: Period start date
            end_date: Period end date
            rootfi_id: Rootfi record ID

        Returns:
            Generated record ID
        """
        base_id = (
            f"rootfi_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
        )
        if rootfi_id:
            base_id += f"_{rootfi_id}"
        return base_id


def parse_rootfi_file(
    file_path: str,
) -> Tuple[List[FinancialRecordCreate], List[AccountCreate], List[AccountValueCreate]]:
    """
    Convenience function to parse a Rootfi file.

    Args:
        file_path: Path to the Rootfi JSON file

    Returns:
        Tuple of (financial_records, accounts, account_values)

    Raises:
        RootfiParseError: If parsing fails
    """
    parser = RootfiParser()
    return parser.parse_file(file_path)
