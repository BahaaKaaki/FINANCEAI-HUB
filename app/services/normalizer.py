import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

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
from app.services.validation import (
    ConflictResolver,
    FinancialDataValidator,
    ValidationResult,
)

logger = get_logger(__name__)


class NormalizationError(Exception):
    """Exception raised during data normalization process."""

    pass


class DataNormalizer:
    """
    Normalizes financial data from various sources into unified schema.

    Handles conversion of parsed data from different formats (QuickBooks, Rootfi, etc.).
    into consistent FinancialRecord, Account, and AccountValue models.
    """

    def __init__(self):
        self.validator = FinancialDataValidator()
        self.conflict_resolver = ConflictResolver()

    def normalize_quickbooks_data(
        self, parsed_data: Dict[str, Any], source_file: Optional[str] = None
    ) -> Tuple[FinancialRecord, List[Account], List[AccountValue], ValidationResult]:
        """
        Normalize QuickBooks parsed data into unified schema.

        Args:
            parsed_data: Parsed QuickBooks data from parser
            source_file: Optional source file name for audit trail

        Returns:
            Tuple of (financial_record, accounts, account_values, validation_result)
        """
        logger.info(
            "Normalizing QuickBooks data from source: %s", source_file or "unknown"
        )

        try:
            # Extract basic financial information
            financial_record = self._create_financial_record_from_quickbooks(
                parsed_data, source_file
            )

            # Extract and normalize accounts
            accounts = self._create_accounts_from_quickbooks(parsed_data)

            # Create account values linking accounts to financial record
            account_values = self._create_account_values_from_quickbooks(
                parsed_data, financial_record.id, accounts
            )

            # Validate the normalized data
            validation_result = self._validate_normalized_data(
                financial_record, accounts, account_values
            )

            logger.info(
                "Normalized QuickBooks data: record_id=%s, accounts=%d, values=%d, valid=%s",
                financial_record.id,
                len(accounts),
                len(account_values),
                validation_result.is_valid,
            )

            return financial_record, accounts, account_values, validation_result

        except Exception as e:
            logger.error("Failed to normalize QuickBooks data: %s", str(e))
            raise NormalizationError(
                f"QuickBooks normalization failed: {str(e)}"
            ) from e

    def normalize_rootfi_data(
        self, parsed_data: Dict[str, Any], source_file: Optional[str] = None
    ) -> Tuple[FinancialRecord, List[Account], List[AccountValue], ValidationResult]:
        """
        Normalize Rootfi parsed data into unified schema.

        Args:
            parsed_data: Parsed Rootfi data from parser
            source_file: Optional source file name for audit trail

        Returns:
            Tuple of (financial_record, accounts, account_values, validation_result)
        """
        logger.info("Normalizing Rootfi data from source: %s", source_file or "unknown")

        try:
            # Extract basic financial information
            financial_record = self._create_financial_record_from_rootfi(
                parsed_data, source_file
            )

            # Extract and normalize accounts
            accounts = self._create_accounts_from_rootfi(parsed_data)

            # Create account values linking accounts to financial record
            account_values = self._create_account_values_from_rootfi(
                parsed_data, financial_record.id, accounts
            )

            # Validate the normalized data
            validation_result = self._validate_normalized_data(
                financial_record, accounts, account_values
            )

            logger.info(
                "Normalized Rootfi data: record_id=%s, accounts=%d, values=%d, valid=%s",
                financial_record.id,
                len(accounts),
                len(account_values),
                validation_result.is_valid,
            )

            return financial_record, accounts, account_values, validation_result

        except Exception as e:
            logger.error("Failed to normalize Rootfi data: %s", str(e))
            raise NormalizationError(f"Rootfi normalization failed: {str(e)}") from e

    def resolve_conflicts_and_merge(
        self,
        normalized_data_list: List[
            Tuple[FinancialRecord, List[Account], List[AccountValue], ValidationResult]
        ],
    ) -> Tuple[FinancialRecord, List[Account], List[AccountValue], ValidationResult]:
        """
        Resolve conflicts between multiple normalized datasets and merge them.

        Args:
            normalized_data_list: List of normalized data tuples from different sources

        Returns:
            Tuple of merged (financial_record, accounts, account_values, validation_result)
        """
        if not normalized_data_list:
            raise ValueError("No normalized data provided for merging")

        if len(normalized_data_list) == 1:
            return normalized_data_list[0]

        logger.info(
            "Resolving conflicts and merging %d datasets", len(normalized_data_list)
        )

        # Extract financial records for conflict resolution
        financial_records = [data[0] for data in normalized_data_list]

        # Resolve financial record conflicts
        resolved_record, conflict_issues = (
            self.conflict_resolver.resolve_financial_record_conflicts(financial_records)
        )

        # Merge accounts from all sources
        all_accounts = []
        for _, accounts, _, _ in normalized_data_list:
            all_accounts.extend(accounts)

        merged_accounts = self._merge_accounts(all_accounts)

        # Merge account values, preferring the resolved record's source
        merged_account_values = self._merge_account_values(
            normalized_data_list, resolved_record
        )

        # Create combined validation result
        combined_validation = ValidationResult(is_valid=True, quality_score=1.0)

        # Add conflict issues
        combined_validation.issues.extend(conflict_issues)

        # Re-validate merged data
        final_validation = self._validate_normalized_data(
            resolved_record, merged_accounts, merged_account_values
        )

        # Combine validation results
        combined_validation.issues.extend(final_validation.issues)
        combined_validation.is_valid = (
            final_validation.is_valid and len(conflict_issues) == 0
        )
        combined_validation.quality_score = min(
            final_validation.quality_score,
            1.0 - (len(conflict_issues) * 0.1),  # Reduce score for conflicts
        )

        logger.info(
            "Merged datasets: conflicts=%d, final_valid=%s, final_score=%.2f",
            len(conflict_issues),
            combined_validation.is_valid,
            combined_validation.quality_score,
        )

        return (
            resolved_record,
            merged_accounts,
            merged_account_values,
            combined_validation,
        )

    def _create_financial_record_from_quickbooks(
        self, parsed_data: Dict[str, Any], source_file: Optional[str]
    ) -> FinancialRecord:
        """Create FinancialRecord from QuickBooks parsed data."""

        # Generate unique ID
        record_id = str(uuid.uuid4())

        # Extract period information
        period_start = parsed_data.get("period_start")
        period_end = parsed_data.get("period_end")

        if not period_start or not period_end:
            raise NormalizationError("Missing period information in QuickBooks data")

        # Convert string dates to date objects if needed
        if isinstance(period_start, str):
            period_start = datetime.fromisoformat(period_start).date()
        if isinstance(period_end, str):
            period_end = datetime.fromisoformat(period_end).date()

        # Extract financial totals
        revenue = Decimal(str(parsed_data.get("total_revenue", 0)))
        expenses = Decimal(str(parsed_data.get("total_expenses", 0)))

        # Extract currency
        currency = parsed_data.get("currency", "USD").upper()

        # Create raw data for audit trail
        raw_data = {
            "source_file": source_file,
            "original_data": parsed_data,
            "normalized_at": datetime.now(timezone.utc).isoformat(),
        }

        return FinancialRecord(
            id=record_id,
            source=SourceType.QUICKBOOKS,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            revenue=revenue,
            expenses=expenses,
            net_profit=revenue - expenses,
            raw_data=raw_data,
        )

    def _create_financial_record_from_rootfi(
        self, parsed_data: Dict[str, Any], source_file: Optional[str]
    ) -> FinancialRecord:
        """Create FinancialRecord from Rootfi parsed data."""

        # Generate unique ID
        record_id = str(uuid.uuid4())

        # Extract period information
        period_start = parsed_data.get("period_start")
        period_end = parsed_data.get("period_end")

        if not period_start or not period_end:
            raise NormalizationError("Missing period information in Rootfi data")

        # Convert string dates to date objects if needed
        if isinstance(period_start, str):
            period_start = datetime.fromisoformat(period_start).date()
        if isinstance(period_end, str):
            period_end = datetime.fromisoformat(period_end).date()

        # Extract financial totals
        revenue = Decimal(str(parsed_data.get("total_revenue", 0)))
        expenses = Decimal(str(parsed_data.get("total_expenses", 0)))

        # Extract currency
        currency = parsed_data.get("currency", "USD").upper()

        # Create raw data for audit trail
        raw_data = {
            "source_file": source_file,
            "original_data": parsed_data,
            "normalized_at": datetime.now(timezone.utc).isoformat(),
        }

        return FinancialRecord(
            id=record_id,
            source=SourceType.ROOTFI,
            period_start=period_start,
            period_end=period_end,
            currency=currency,
            revenue=revenue,
            expenses=expenses,
            net_profit=revenue - expenses,
            raw_data=raw_data,
        )

    def _create_accounts_from_quickbooks(
        self, parsed_data: Dict[str, Any]
    ) -> List[Account]:
        """Create Account objects from QuickBooks parsed data."""

        accounts = []
        account_data = parsed_data.get("accounts", [])

        for acc_data in account_data:
            account = Account(
                account_id=acc_data.get("account_id", str(uuid.uuid4())),
                name=acc_data.get("name", "Unknown Account"),
                account_type=self._map_account_type(acc_data.get("type", "expense")),
                parent_account_id=acc_data.get("parent_id"),
                source=SourceType.QUICKBOOKS,
                description=acc_data.get("description"),
                is_active=acc_data.get("is_active", True),
            )
            accounts.append(account)

        return accounts

    def _create_accounts_from_rootfi(
        self, parsed_data: Dict[str, Any]
    ) -> List[Account]:
        """Create Account objects from Rootfi parsed data."""

        accounts = []
        account_data = parsed_data.get("accounts", [])

        for acc_data in account_data:
            account = Account(
                account_id=acc_data.get("account_id", str(uuid.uuid4())),
                name=acc_data.get("name", "Unknown Account"),
                account_type=self._map_account_type(acc_data.get("type", "expense")),
                parent_account_id=acc_data.get("parent_id"),
                source=SourceType.ROOTFI,
                description=acc_data.get("description"),
                is_active=acc_data.get("is_active", True),
            )
            accounts.append(account)

        return accounts

    def _create_account_values_from_quickbooks(
        self,
        parsed_data: Dict[str, Any],
        financial_record_id: str,
        accounts: List[Account],
    ) -> List[AccountValue]:
        """Create AccountValue objects from QuickBooks parsed data."""

        account_values = []
        account_data = parsed_data.get("accounts", [])

        for acc_data in account_data:
            value = acc_data.get("value", 0)
            if value != 0:  # Only create values for non-zero amounts
                account_value = AccountValue(
                    account_id=acc_data.get("account_id", str(uuid.uuid4())),
                    financial_record_id=financial_record_id,
                    value=Decimal(str(value)),
                )
                account_values.append(account_value)

        return account_values

    def _create_account_values_from_rootfi(
        self,
        parsed_data: Dict[str, Any],
        financial_record_id: str,
        accounts: List[Account],
    ) -> List[AccountValue]:
        """Create AccountValue objects from Rootfi parsed data."""

        account_values = []
        account_data = parsed_data.get("accounts", [])

        for acc_data in account_data:
            value = acc_data.get("value", 0)
            if value != 0:  # Only create values for non-zero amounts
                account_value = AccountValue(
                    account_id=acc_data.get("account_id", str(uuid.uuid4())),
                    financial_record_id=financial_record_id,
                    value=Decimal(str(value)),
                )
                account_values.append(account_value)

        return account_values

    def _map_account_type(self, source_type: str) -> AccountType:
        """Map source-specific account type to unified AccountType enum."""

        type_mapping = {
            # Common mappings
            "revenue": AccountType.REVENUE,
            "income": AccountType.REVENUE,
            "sales": AccountType.REVENUE,
            "expense": AccountType.EXPENSE,
            "cost": AccountType.EXPENSE,
            "operating_expense": AccountType.EXPENSE,
            "asset": AccountType.ASSET,
            "liability": AccountType.LIABILITY,
            "equity": AccountType.EQUITY,
            # QuickBooks specific mappings
            "other_income": AccountType.REVENUE,
            "cost_of_goods_sold": AccountType.EXPENSE,
            "other_expense": AccountType.EXPENSE,
            # Rootfi specific mappings
            "operating_revenue": AccountType.REVENUE,
            "operating_expenses": AccountType.EXPENSE,
        }

        normalized_type = source_type.lower().replace(" ", "_")
        return type_mapping.get(
            normalized_type, AccountType.EXPENSE
        )  # Default to expense

    def _merge_accounts(self, all_accounts: List[Account]) -> List[Account]:
        """Merge accounts from multiple sources, removing duplicates."""

        # Use account_id as the key for deduplication
        account_map = {}

        for account in all_accounts:
            existing = account_map.get(account.account_id)

            if existing is None:
                account_map[account.account_id] = account
            else:
                # If duplicate, prefer higher priority source
                if self.conflict_resolver.source_priority.get(
                    account.source, 0
                ) > self.conflict_resolver.source_priority.get(existing.source, 0):
                    account_map[account.account_id] = account

        return list(account_map.values())

    def _merge_account_values(
        self,
        normalized_data_list: List[
            Tuple[FinancialRecord, List[Account], List[AccountValue], ValidationResult]
        ],
        resolved_record: FinancialRecord,
    ) -> List[AccountValue]:
        """Merge account values, preferring values from the resolved record's source."""

        # Find the dataset that matches the resolved record's source
        preferred_values = None

        for financial_record, _, account_values, _ in normalized_data_list:
            if financial_record.source == resolved_record.source:
                preferred_values = account_values
                break

        # If no preferred values found, use the first dataset
        if preferred_values is None and normalized_data_list:
            preferred_values = normalized_data_list[0][2]

        # Update financial_record_id to match resolved record
        merged_values = []
        for account_value in preferred_values or []:
            merged_value = AccountValue(
                id=account_value.id,
                account_id=account_value.account_id,
                financial_record_id=resolved_record.id,  # Use resolved record ID
                value=account_value.value,
                created_at=account_value.created_at,
            )
            merged_values.append(merged_value)

        return merged_values

    def _validate_normalized_data(
        self,
        financial_record: FinancialRecord,
        accounts: List[Account],
        account_values: List[AccountValue],
    ) -> ValidationResult:
        """Validate the complete normalized dataset."""

        # Validate financial record
        record_validation = self.validator.validate_financial_record(
            financial_record, accounts
        )

        # Validate account hierarchy
        hierarchy_validation = self.validator.validate_account_hierarchy(accounts)

        # Validate account values
        values_validation = self.validator.validate_account_values(
            account_values, financial_record, accounts
        )

        # Combine all validation results
        combined_result = ValidationResult(is_valid=True, quality_score=1.0)

        # Combine issues
        combined_result.issues.extend(record_validation.issues)
        combined_result.issues.extend(hierarchy_validation.issues)
        combined_result.issues.extend(values_validation.issues)

        # Overall validity is true only if all validations pass
        combined_result.is_valid = (
            record_validation.is_valid
            and hierarchy_validation.is_valid
            and values_validation.is_valid
        )

        # Use minimum quality score
        combined_result.quality_score = min(
            record_validation.quality_score,
            hierarchy_validation.quality_score,
            values_validation.quality_score,
        )

        return combined_result
