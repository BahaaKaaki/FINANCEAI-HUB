from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.models.financial import (
    Account,
    AccountType,
    AccountValue,
    FinancialRecord,
    SourceType,
)

logger = get_logger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ValidationIssue(BaseModel):
    """Represents a validation issue found during data validation."""

    severity: ValidationSeverity
    code: str
    message: str
    field: Optional[str] = None
    value: Optional[Any] = None
    suggestion: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of data validation containing issues and quality score."""

    is_valid: bool
    quality_score: float = Field(ge=0.0, le=1.0)
    issues: List[ValidationIssue] = Field(default_factory=list)

    def add_issue(
        self,
        severity: ValidationSeverity,
        code: str,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add a validation issue to the result."""
        issue = ValidationIssue(
            severity=severity,
            code=code,
            message=message,
            field=field,
            value=value,
            suggestion=suggestion,
        )
        self.issues.append(issue)

        # Update validity based on severity
        if severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False


class FinancialDataValidator:
    """
    Comprehensive validator for financial data with quality scoring.

    Provides validation for:
    - Financial accuracy (negative values, impossible amounts)
    - Date consistency and chronological order
    - Account hierarchies and circular references
    - Balance equations (Revenue - Expenses = Net Profit)
    - Data quality scoring and conflict resolution
    """

    def __init__(self):
        self.tolerance = Decimal("0.01")  # Default tolerance for decimal comparisons

    def validate_financial_record(
        self, record: FinancialRecord, accounts: Optional[List[Account]] = None
    ) -> ValidationResult:
        """
        Validate a complete financial record with comprehensive checks.

        Args:
            record: The financial record to validate
            accounts: Optional list of related accounts for hierarchy validation

        Returns:
            ValidationResult with issues and quality score
        """
        result = ValidationResult(is_valid=True, quality_score=1.0)

        # Basic financial accuracy validation
        self._validate_financial_accuracy(record, result)

        # Date consistency validation
        self._validate_date_consistency(record, result)

        # Balance equation validation
        self._validate_balance_equation(record, result)

        # Currency validation
        self._validate_currency(record, result)

        # Calculate final quality score
        result.quality_score = self._calculate_quality_score(result.issues)

        logger.info(
            "Validated financial record %s: valid=%s, score=%.2f, issues=%d",
            record.id,
            result.is_valid,
            result.quality_score,
            len(result.issues),
        )

        return result

    def validate_account_hierarchy(self, accounts: List[Account]) -> ValidationResult:
        """
        Validate account hierarchy for circular references and consistency.

        Args:
            accounts: List of accounts to validate

        Returns:
            ValidationResult with hierarchy validation issues
        """
        result = ValidationResult(is_valid=True, quality_score=1.0)

        # Build account lookup for efficient validation
        account_lookup = {acc.account_id: acc for acc in accounts}

        # Check for circular references
        self._validate_circular_references(accounts, account_lookup, result)

        # Validate parent-child relationships
        self._validate_parent_child_relationships(accounts, account_lookup, result)

        # Validate account type consistency in hierarchy
        self._validate_account_type_hierarchy(accounts, account_lookup, result)

        result.quality_score = self._calculate_quality_score(result.issues)

        logger.info(
            "Validated account hierarchy: valid=%s, score=%.2f, issues=%d",
            result.is_valid,
            result.quality_score,
            len(result.issues),
        )

        return result

    def validate_account_values(
        self,
        account_values: List[AccountValue],
        financial_record: FinancialRecord,
        accounts: List[Account],
    ) -> ValidationResult:
        """
        Validate account values against financial record totals.

        Args:
            account_values: List of account values to validate
            financial_record: The related financial record
            accounts: List of accounts for type checking

        Returns:
            ValidationResult with account value validation issues
        """
        result = ValidationResult(is_valid=True, quality_score=1.0)

        # Build account lookup
        account_lookup = {acc.account_id: acc for acc in accounts}

        # Validate account value consistency
        self._validate_account_value_totals(
            account_values, financial_record, account_lookup, result
        )

        # Check for missing accounts
        self._validate_account_completeness(
            account_values, financial_record, account_lookup, result
        )

        result.quality_score = self._calculate_quality_score(result.issues)

        logger.info(
            "Validated account values: valid=%s, score=%.2f, issues=%d",
            result.is_valid,
            result.quality_score,
            len(result.issues),
        )

        return result

    def _validate_financial_accuracy(
        self, record: FinancialRecord, result: ValidationResult
    ) -> None:
        """Validate financial accuracy rules."""

        # Check for negative revenue (usually invalid)
        if record.revenue < 0:
            result.add_issue(
                ValidationSeverity.WARNING,
                "NEGATIVE_REVENUE",
                f"Revenue is negative: {record.revenue}",
                field="revenue",
                value=record.revenue,
                suggestion="Verify if negative revenue is expected (e.g., returns/refunds)",
            )

        # Check for negative expenses (usually invalid)
        if record.expenses < 0:
            result.add_issue(
                ValidationSeverity.WARNING,
                "NEGATIVE_EXPENSES",
                f"Expenses are negative: {record.expenses}",
                field="expenses",
                value=record.expenses,
                suggestion="Verify if negative expenses are expected (e.g., expense reversals)",
            )

        # Check for unreasonably large values (potential data entry errors)
        max_reasonable_amount = Decimal("1000000000")  # 1 billion

        if record.revenue > max_reasonable_amount:
            result.add_issue(
                ValidationSeverity.WARNING,
                "UNUSUALLY_HIGH_REVENUE",
                f"Revenue is unusually high: {record.revenue}",
                field="revenue",
                value=record.revenue,
                suggestion="Verify amount is correct and not a data entry error",
            )

        if record.expenses > max_reasonable_amount:
            result.add_issue(
                ValidationSeverity.WARNING,
                "UNUSUALLY_HIGH_EXPENSES",
                f"Expenses are unusually high: {record.expenses}",
                field="expenses",
                value=record.expenses,
                suggestion="Verify amount is correct and not a data entry error",
            )

    def _validate_date_consistency(
        self, record: FinancialRecord, result: ValidationResult
    ) -> None:
        """Validate date consistency and chronological order."""

        # Check if period_end is after period_start (should be caught by Pydantic)
        if record.period_end <= record.period_start:
            result.add_issue(
                ValidationSeverity.ERROR,
                "INVALID_DATE_RANGE",
                f"Period end ({record.period_end}) must be after period start ({record.period_start})",
                field="period_end",
                value=record.period_end,
                suggestion="Ensure period_end is later than period_start",
            )

        # Check for future dates (might be invalid depending on context)
        today = date.today()
        if record.period_end > today:
            result.add_issue(
                ValidationSeverity.WARNING,
                "FUTURE_PERIOD_END",
                f"Period end ({record.period_end}) is in the future",
                field="period_end",
                value=record.period_end,
                suggestion="Verify if future dates are expected for this record",
            )

        # Check for very old dates (might indicate data quality issues)
        from datetime import timedelta

        very_old_date = today - timedelta(days=365 * 10)  # 10 years ago

        if record.period_start < very_old_date:
            result.add_issue(
                ValidationSeverity.INFO,
                "VERY_OLD_PERIOD",
                f"Period start ({record.period_start}) is more than 10 years old",
                field="period_start",
                value=record.period_start,
                suggestion="Verify if historical data is expected",
            )

    def _validate_balance_equation(
        self, record: FinancialRecord, result: ValidationResult
    ) -> None:
        """Validate that net_profit equals revenue minus expenses."""

        expected_profit = record.revenue - record.expenses
        actual_profit = record.net_profit

        if abs(actual_profit - expected_profit) > self.tolerance:
            result.add_issue(
                ValidationSeverity.ERROR,
                "BALANCE_EQUATION_MISMATCH",
                f"Net profit ({actual_profit}) does not equal revenue - expenses ({expected_profit})",
                field="net_profit",
                value=actual_profit,
                suggestion=f"Net profit should be {expected_profit}",
            )

    def _validate_currency(
        self, record: FinancialRecord, result: ValidationResult
    ) -> None:
        """Validate currency code format and consistency."""

        # Check currency code format (should be 3 letters)
        if len(record.currency) != 3 or not record.currency.isalpha():
            result.add_issue(
                ValidationSeverity.ERROR,
                "INVALID_CURRENCY_FORMAT",
                f"Currency code '{record.currency}' is not a valid 3-letter code",
                field="currency",
                value=record.currency,
                suggestion="Use standard 3-letter currency codes (e.g., USD, EUR, GBP)",
            )

        # Check for common currency codes
        common_currencies = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "CNY"}
        if record.currency.upper() not in common_currencies:
            result.add_issue(
                ValidationSeverity.INFO,
                "UNCOMMON_CURRENCY",
                f"Currency '{record.currency}' is not commonly used",
                field="currency",
                value=record.currency,
                suggestion="Verify currency code is correct",
            )

    def _validate_circular_references(
        self,
        accounts: List[Account],
        account_lookup: Dict[str, Account],
        result: ValidationResult,
    ) -> None:
        """Check for circular references in account hierarchy."""

        def has_circular_reference(account_id: str, visited: Set[str]) -> bool:
            if account_id in visited:
                return True

            account = account_lookup.get(account_id)
            if not account or not account.parent_account_id:
                return False

            visited.add(account_id)
            return has_circular_reference(account.parent_account_id, visited)

        for account in accounts:
            if account.parent_account_id:
                visited = set()
                if has_circular_reference(account.account_id, visited):
                    result.add_issue(
                        ValidationSeverity.ERROR,
                        "CIRCULAR_REFERENCE",
                        f"Account '{account.account_id}' has circular reference in hierarchy",
                        field="parent_account_id",
                        value=account.parent_account_id,
                        suggestion="Remove circular reference in account hierarchy",
                    )

    def _validate_parent_child_relationships(
        self,
        accounts: List[Account],
        account_lookup: Dict[str, Account],
        result: ValidationResult,
    ) -> None:
        """Validate parent-child relationships exist and are valid."""

        for account in accounts:
            if account.parent_account_id:
                parent = account_lookup.get(account.parent_account_id)
                if not parent:
                    result.add_issue(
                        ValidationSeverity.ERROR,
                        "MISSING_PARENT_ACCOUNT",
                        f"Parent account '{account.parent_account_id}' not found for account '{account.account_id}'",
                        field="parent_account_id",
                        value=account.parent_account_id,
                        suggestion="Ensure parent account exists or remove parent reference",
                    )

    def _validate_account_type_hierarchy(
        self,
        accounts: List[Account],
        account_lookup: Dict[str, Account],
        result: ValidationResult,
    ) -> None:
        """Validate account type consistency in hierarchy."""

        for account in accounts:
            if account.parent_account_id:
                parent = account_lookup.get(account.parent_account_id)
                if parent and parent.account_type != account.account_type:
                    result.add_issue(
                        ValidationSeverity.WARNING,
                        "INCONSISTENT_ACCOUNT_TYPE_HIERARCHY",
                        f"Account '{account.account_id}' type '{account.account_type}' differs from parent '{parent.account_id}' type '{parent.account_type}'",
                        field="account_type",
                        value=account.account_type,
                        suggestion="Consider aligning account types in hierarchy",
                    )

    def _validate_account_value_totals(
        self,
        account_values: List[AccountValue],
        financial_record: FinancialRecord,
        account_lookup: Dict[str, Account],
        result: ValidationResult,
    ) -> None:
        """Validate that account values sum to financial record totals."""

        # Group account values by type
        revenue_total = Decimal("0")
        expense_total = Decimal("0")

        for account_value in account_values:
            account = account_lookup.get(account_value.account_id)
            if account:
                if account.account_type == AccountType.REVENUE:
                    revenue_total += account_value.value
                elif account.account_type == AccountType.EXPENSE:
                    expense_total += account_value.value

        # Check revenue total
        if abs(revenue_total - financial_record.revenue) > self.tolerance:
            result.add_issue(
                ValidationSeverity.ERROR,
                "REVENUE_TOTAL_MISMATCH",
                f"Account values revenue total ({revenue_total}) does not match financial record revenue ({financial_record.revenue})",
                field="revenue",
                value=revenue_total,
                suggestion=f"Revenue account values should sum to {financial_record.revenue}",
            )

        # Check expense total
        if abs(expense_total - financial_record.expenses) > self.tolerance:
            result.add_issue(
                ValidationSeverity.ERROR,
                "EXPENSE_TOTAL_MISMATCH",
                f"Account values expense total ({expense_total}) does not match financial record expenses ({financial_record.expenses})",
                field="expenses",
                value=expense_total,
                suggestion=f"Expense account values should sum to {financial_record.expenses}",
            )

    def _validate_account_completeness(
        self,
        account_values: List[AccountValue],
        financial_record: FinancialRecord,
        account_lookup: Dict[str, Account],
        result: ValidationResult,
    ) -> None:
        """Check for missing account values that might be expected."""

        # This is a basic check - in a real system, we might have
        # business rules about which accounts are required

        account_ids_with_values = {av.account_id for av in account_values}
        all_account_ids = set(account_lookup.keys())

        missing_accounts = all_account_ids - account_ids_with_values

        if missing_accounts:
            result.add_issue(
                ValidationSeverity.INFO,
                "MISSING_ACCOUNT_VALUES",
                f"Some accounts have no values for this period: {', '.join(sorted(missing_accounts))}",
                suggestion="Verify if all accounts should have values for this period",
            )

    def _calculate_quality_score(self, issues: List[ValidationIssue]) -> float:
        """
        Calculate data quality score based on validation issues.

        Score ranges from 0.0 (worst) to 1.0 (perfect).
        """
        if not issues:
            return 1.0

        # Weight different severity levels
        severity_weights = {
            ValidationSeverity.INFO: 0.05,
            ValidationSeverity.WARNING: 0.15,
            ValidationSeverity.ERROR: 0.35,
            ValidationSeverity.CRITICAL: 0.50,
        }

        total_penalty = sum(
            severity_weights.get(issue.severity, 0.1) for issue in issues
        )

        # Ensure score doesn't go below 0
        score = max(0.0, 1.0 - total_penalty)

        return round(score, 2)


class ConflictResolver:
    """
    Handles conflict resolution when multiple data sources provide conflicting information.
    """

    def __init__(self):
        # Source priority for conflict resolution (higher number = higher priority)
        self.source_priority = {
            SourceType.QUICKBOOKS: 2,
            SourceType.ROOTFI: 1,
        }

    def resolve_financial_record_conflicts(
        self, records: List[FinancialRecord]
    ) -> Tuple[FinancialRecord, List[ValidationIssue]]:
        """
        Resolve conflicts between multiple financial records for the same period.

        Args:
            records: List of conflicting financial records

        Returns:
            Tuple of (resolved_record, conflict_issues)
        """
        if not records:
            raise ValueError("No records provided for conflict resolution")

        if len(records) == 1:
            return records[0], []

        issues = []

        # Sort by source priority (highest first)
        sorted_records = sorted(
            records, key=lambda r: self.source_priority.get(r.source, 0), reverse=True
        )

        primary_record = sorted_records[0]

        # Check for conflicts and log them
        for other_record in sorted_records[1:]:
            conflicts = self._detect_record_conflicts(primary_record, other_record)
            issues.extend(conflicts)

        logger.info(
            "Resolved conflicts for period %s-%s: selected %s source, found %d conflicts",
            primary_record.period_start,
            primary_record.period_end,
            primary_record.source,
            len(issues),
        )

        return primary_record, issues

    def _detect_record_conflicts(
        self, record1: FinancialRecord, record2: FinancialRecord
    ) -> List[ValidationIssue]:
        """Detect conflicts between two financial records."""

        conflicts = []
        tolerance = Decimal("0.01")

        # Check revenue conflicts
        if abs(record1.revenue - record2.revenue) > tolerance:
            conflicts.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="REVENUE_CONFLICT",
                    message=f"Revenue conflict: {record1.source}={record1.revenue}, {record2.source}={record2.revenue}",
                    field="revenue",
                    suggestion=f"Using {record1.source} value: {record1.revenue}",
                )
            )

        # Check expense conflicts
        if abs(record1.expenses - record2.expenses) > tolerance:
            conflicts.append(
                ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="EXPENSE_CONFLICT",
                    message=f"Expense conflict: {record1.source}={record1.expenses}, {record2.source}={record2.expenses}",
                    field="expenses",
                    suggestion=f"Using {record1.source} value: {record1.expenses}",
                )
            )

        # Check currency conflicts
        if record1.currency != record2.currency:
            conflicts.append(
                ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="CURRENCY_CONFLICT",
                    message=f"Currency conflict: {record1.source}={record1.currency}, {record2.source}={record2.currency}",
                    field="currency",
                    suggestion=f"Using {record1.source} currency: {record1.currency}",
                )
            )

        return conflicts
