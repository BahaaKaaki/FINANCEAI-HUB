"""
Tests for data validation service.

This module tests the comprehensive validation rules for financial accuracy,
data quality scoring, and validation for date consistency, account hierarchies,
and balance equations.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List

from app.models.financial import (
    Account,
    AccountType,
    AccountValue,
    FinancialRecord,
    SourceType,
)
from app.services.validation import (
    ConflictResolver,
    FinancialDataValidator,
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
)


class TestFinancialDataValidator:
    """Test cases for FinancialDataValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = FinancialDataValidator()
        
        # Create a valid financial record for testing
        self.valid_record = FinancialRecord(
            id="test-record-1",
            source=SourceType.QUICKBOOKS,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            currency="USD",
            revenue=Decimal("10000.00"),
            expenses=Decimal("7000.00"),
            net_profit=Decimal("3000.00"),
        )
        
        # Create valid accounts for testing
        self.valid_accounts = [
            Account(
                account_id="revenue-001",
                name="Sales Revenue",
                account_type=AccountType.REVENUE,
                source=SourceType.QUICKBOOKS,
            ),
            Account(
                account_id="expense-001",
                name="Office Expenses",
                account_type=AccountType.EXPENSE,
                source=SourceType.QUICKBOOKS,
            ),
            Account(
                account_id="expense-002",
                name="Marketing Expenses",
                account_type=AccountType.EXPENSE,
                parent_account_id="expense-001",
                source=SourceType.QUICKBOOKS,
            ),
        ]
        
        # Create valid account values
        self.valid_account_values = [
            AccountValue(
                account_id="revenue-001",
                financial_record_id="test-record-1",
                value=Decimal("10000.00"),
            ),
            AccountValue(
                account_id="expense-001",
                financial_record_id="test-record-1",
                value=Decimal("5000.00"),
            ),
            AccountValue(
                account_id="expense-002",
                financial_record_id="test-record-1",
                value=Decimal("2000.00"),
            ),
        ]
    
    def test_validate_valid_financial_record(self):
        """Test validation of a completely valid financial record."""
        result = self.validator.validate_financial_record(self.valid_record)
        
        assert result.is_valid is True
        assert result.quality_score == 1.0
        assert len(result.issues) == 0
    
    def test_validate_negative_revenue(self):
        """Test validation catches negative revenue."""
        record = self.valid_record.model_copy()
        record.revenue = Decimal("-1000.00")
        record.net_profit = record.revenue - record.expenses
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "NEGATIVE_REVENUE" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.WARNING for issue in result.issues)
    
    def test_validate_negative_expenses(self):
        """Test validation catches negative expenses."""
        record = self.valid_record.model_copy()
        record.expenses = Decimal("-500.00")
        record.net_profit = record.revenue - record.expenses
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "NEGATIVE_EXPENSES" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.WARNING for issue in result.issues)
    
    def test_validate_unusually_high_amounts(self):
        """Test validation catches unusually high amounts."""
        record = self.valid_record.model_copy()
        record.revenue = Decimal("2000000000.00")  # 2 billion
        record.net_profit = record.revenue - record.expenses
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "UNUSUALLY_HIGH_REVENUE" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.WARNING for issue in result.issues)
    
    def test_validate_invalid_date_range(self):
        """Test validation catches invalid date ranges."""
        record = self.valid_record.model_copy()
        record.period_end = record.period_start - timedelta(days=1)
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "INVALID_DATE_RANGE" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
        assert result.is_valid is False
    
    def test_validate_future_period_end(self):
        """Test validation catches future period end dates."""
        record = self.valid_record.model_copy()
        record.period_end = date.today() + timedelta(days=30)
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "FUTURE_PERIOD_END" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.WARNING for issue in result.issues)
    
    def test_validate_very_old_period(self):
        """Test validation flags very old periods."""
        record = self.valid_record.model_copy()
        record.period_start = date.today() - timedelta(days=365 * 15)  # 15 years ago
        record.period_end = record.period_start + timedelta(days=30)
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "VERY_OLD_PERIOD" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.INFO for issue in result.issues)
    
    def test_validate_balance_equation_mismatch(self):
        """Test validation catches balance equation mismatches."""
        record = self.valid_record.model_copy()
        record.net_profit = Decimal("5000.00")  # Should be 3000.00
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "BALANCE_EQUATION_MISMATCH" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
        assert result.is_valid is False
    
    def test_validate_invalid_currency_format(self):
        """Test validation catches invalid currency formats."""
        record = self.valid_record.model_copy()
        record.currency = "INVALID"  # Should be 3 letters
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "INVALID_CURRENCY_FORMAT" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
        assert result.is_valid is False
    
    def test_validate_uncommon_currency(self):
        """Test validation flags uncommon currencies."""
        record = self.valid_record.model_copy()
        record.currency = "XYZ"  # Valid format but uncommon
        
        result = self.validator.validate_financial_record(record)
        
        assert any(issue.code == "UNCOMMON_CURRENCY" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.INFO for issue in result.issues)
    
    def test_validate_account_hierarchy_valid(self):
        """Test validation of valid account hierarchy."""
        result = self.validator.validate_account_hierarchy(self.valid_accounts)
        
        assert result.is_valid is True
        assert result.quality_score == 1.0
        assert len(result.issues) == 0
    
    def test_validate_circular_reference(self):
        """Test validation catches circular references in account hierarchy."""
        accounts = [
            Account(
                account_id="acc-1",
                name="Account 1",
                account_type=AccountType.EXPENSE,
                parent_account_id="acc-2",
                source=SourceType.QUICKBOOKS,
            ),
            Account(
                account_id="acc-2",
                name="Account 2",
                account_type=AccountType.EXPENSE,
                parent_account_id="acc-1",  # Circular reference
                source=SourceType.QUICKBOOKS,
            ),
        ]
        
        result = self.validator.validate_account_hierarchy(accounts)
        
        assert any(issue.code == "CIRCULAR_REFERENCE" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
        assert result.is_valid is False
    
    def test_validate_missing_parent_account(self):
        """Test validation catches missing parent accounts."""
        accounts = [
            Account(
                account_id="child-acc",
                name="Child Account",
                account_type=AccountType.EXPENSE,
                parent_account_id="missing-parent",
                source=SourceType.QUICKBOOKS,
            ),
        ]
        
        result = self.validator.validate_account_hierarchy(accounts)
        
        assert any(issue.code == "MISSING_PARENT_ACCOUNT" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
        assert result.is_valid is False
    
    def test_validate_inconsistent_account_type_hierarchy(self):
        """Test validation flags inconsistent account types in hierarchy."""
        accounts = [
            Account(
                account_id="parent-acc",
                name="Parent Account",
                account_type=AccountType.REVENUE,
                source=SourceType.QUICKBOOKS,
            ),
            Account(
                account_id="child-acc",
                name="Child Account",
                account_type=AccountType.EXPENSE,  # Different type from parent
                parent_account_id="parent-acc",
                source=SourceType.QUICKBOOKS,
            ),
        ]
        
        result = self.validator.validate_account_hierarchy(accounts)
        
        assert any(issue.code == "INCONSISTENT_ACCOUNT_TYPE_HIERARCHY" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.WARNING for issue in result.issues)
    
    def test_validate_account_values_valid(self):
        """Test validation of valid account values."""
        result = self.validator.validate_account_values(
            self.valid_account_values, self.valid_record, self.valid_accounts
        )
        
        assert result.is_valid is True
        assert result.quality_score == 1.0
        assert len(result.issues) == 0
    
    def test_validate_revenue_total_mismatch(self):
        """Test validation catches revenue total mismatches."""
        # Modify account values to have incorrect revenue total
        account_values = self.valid_account_values.copy()
        account_values[0].value = Decimal("8000.00")  # Should be 10000.00
        
        result = self.validator.validate_account_values(
            account_values, self.valid_record, self.valid_accounts
        )
        
        assert any(issue.code == "REVENUE_TOTAL_MISMATCH" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
        assert result.is_valid is False
    
    def test_validate_expense_total_mismatch(self):
        """Test validation catches expense total mismatches."""
        # Modify account values to have incorrect expense total
        account_values = self.valid_account_values.copy()
        account_values[1].value = Decimal("3000.00")  # Should be 5000.00
        
        result = self.validator.validate_account_values(
            account_values, self.valid_record, self.valid_accounts
        )
        
        assert any(issue.code == "EXPENSE_TOTAL_MISMATCH" for issue in result.issues)
        assert any(issue.severity == ValidationSeverity.ERROR for issue in result.issues)
        assert result.is_valid is False
    
    def test_calculate_quality_score(self):
        """Test quality score calculation with various issue severities."""
        result = ValidationResult(is_valid=True, quality_score=1.0)
        
        # Add issues of different severities
        result.add_issue(ValidationSeverity.INFO, "INFO_ISSUE", "Info message")
        result.add_issue(ValidationSeverity.WARNING, "WARNING_ISSUE", "Warning message")
        result.add_issue(ValidationSeverity.ERROR, "ERROR_ISSUE", "Error message")
        
        final_score = self.validator._calculate_quality_score(result.issues)
        
        # Score should be reduced based on severity weights
        expected_penalty = 0.05 + 0.15 + 0.35  # INFO + WARNING + ERROR
        expected_score = max(0.0, 1.0 - expected_penalty)
        
        # Use approximate equality for floating point comparison
        assert abs(final_score - expected_score) < 0.001
        assert final_score < 1.0


class TestConflictResolver:
    """Test cases for ConflictResolver."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = ConflictResolver()
        
        # Create conflicting financial records
        self.quickbooks_record = FinancialRecord(
            id="qb-record-1",
            source=SourceType.QUICKBOOKS,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            currency="USD",
            revenue=Decimal("10000.00"),
            expenses=Decimal("7000.00"),
            net_profit=Decimal("3000.00"),
        )
        
        self.rootfi_record = FinancialRecord(
            id="rf-record-1",
            source=SourceType.ROOTFI,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            currency="USD",
            revenue=Decimal("9500.00"),  # Different revenue
            expenses=Decimal("7200.00"),  # Different expenses
            net_profit=Decimal("2300.00"),
        )
    
    def test_resolve_single_record(self):
        """Test conflict resolution with single record."""
        resolved_record, issues = self.resolver.resolve_financial_record_conflicts(
            [self.quickbooks_record]
        )
        
        assert resolved_record == self.quickbooks_record
        assert len(issues) == 0
    
    def test_resolve_conflicts_quickbooks_priority(self):
        """Test conflict resolution prioritizes QuickBooks over Rootfi."""
        resolved_record, issues = self.resolver.resolve_financial_record_conflicts(
            [self.rootfi_record, self.quickbooks_record]  # Order shouldn't matter
        )
        
        assert resolved_record.source == SourceType.QUICKBOOKS
        assert resolved_record.revenue == self.quickbooks_record.revenue
        assert len(issues) > 0  # Should have conflict issues
    
    def test_detect_revenue_conflict(self):
        """Test detection of revenue conflicts."""
        conflicts = self.resolver._detect_record_conflicts(
            self.quickbooks_record, self.rootfi_record
        )
        
        revenue_conflicts = [c for c in conflicts if c.code == "REVENUE_CONFLICT"]
        assert len(revenue_conflicts) == 1
        assert revenue_conflicts[0].severity == ValidationSeverity.WARNING
    
    def test_detect_expense_conflict(self):
        """Test detection of expense conflicts."""
        conflicts = self.resolver._detect_record_conflicts(
            self.quickbooks_record, self.rootfi_record
        )
        
        expense_conflicts = [c for c in conflicts if c.code == "EXPENSE_CONFLICT"]
        assert len(expense_conflicts) == 1
        assert expense_conflicts[0].severity == ValidationSeverity.WARNING
    
    def test_detect_currency_conflict(self):
        """Test detection of currency conflicts."""
        # Create record with different currency
        eur_record = self.rootfi_record.model_copy()
        eur_record.currency = "EUR"
        
        conflicts = self.resolver._detect_record_conflicts(
            self.quickbooks_record, eur_record
        )
        
        currency_conflicts = [c for c in conflicts if c.code == "CURRENCY_CONFLICT"]
        assert len(currency_conflicts) == 1
        assert currency_conflicts[0].severity == ValidationSeverity.ERROR
    
    def test_no_conflicts_identical_records(self):
        """Test no conflicts detected for identical records."""
        identical_record = self.quickbooks_record.model_copy()
        identical_record.id = "different-id"
        identical_record.source = SourceType.ROOTFI
        
        conflicts = self.resolver._detect_record_conflicts(
            self.quickbooks_record, identical_record
        )
        
        assert len(conflicts) == 0
    
    def test_resolve_empty_list_raises_error(self):
        """Test that empty record list raises ValueError."""
        with pytest.raises(ValueError, match="No records provided"):
            self.resolver.resolve_financial_record_conflicts([])


class TestValidationResult:
    """Test cases for ValidationResult model."""
    
    def test_add_issue_updates_validity(self):
        """Test that adding error/critical issues updates validity."""
        result = ValidationResult(is_valid=True, quality_score=1.0)
        
        # Adding INFO/WARNING should not affect validity
        result.add_issue(ValidationSeverity.INFO, "INFO_CODE", "Info message")
        assert result.is_valid is True
        
        result.add_issue(ValidationSeverity.WARNING, "WARNING_CODE", "Warning message")
        assert result.is_valid is True
        
        # Adding ERROR should set validity to False
        result.add_issue(ValidationSeverity.ERROR, "ERROR_CODE", "Error message")
        assert result.is_valid is False
        
        # Adding CRITICAL should also set validity to False
        result = ValidationResult(is_valid=True, quality_score=1.0)
        result.add_issue(ValidationSeverity.CRITICAL, "CRITICAL_CODE", "Critical message")
        assert result.is_valid is False
    
    def test_validation_issue_creation(self):
        """Test ValidationIssue creation with all fields."""
        issue = ValidationIssue(
            severity=ValidationSeverity.ERROR,
            code="TEST_CODE",
            message="Test message",
            field="test_field",
            value="test_value",
            suggestion="Test suggestion",
        )
        
        assert issue.severity == ValidationSeverity.ERROR
        assert issue.code == "TEST_CODE"
        assert issue.message == "Test message"
        assert issue.field == "test_field"
        assert issue.value == "test_value"
        assert issue.suggestion == "Test suggestion"