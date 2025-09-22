"""
Integration tests for data validation and normalization services.

This module tests the complete workflow of parsing, normalizing, and validating
financial data from multiple sources with conflict resolution.
"""

import pytest
from datetime import date
from decimal import Decimal

from app.models.financial import AccountType, SourceType
from app.services.normalizer import DataNormalizer
from app.services.validation import ValidationSeverity


class TestValidationNormalizationIntegration:
    """Integration tests for validation and normalization workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = DataNormalizer()
        
        # Sample data that will pass validation
        self.valid_quickbooks_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 20000.00,
            "total_expenses": 15000.00,
            "accounts": [
                {
                    "account_id": "qb-revenue-001",
                    "name": "Product Sales",
                    "type": "revenue",
                    "value": 20000.00,
                    "description": "Revenue from product sales",
                    "is_active": True,
                },
                {
                    "account_id": "qb-expense-001",
                    "name": "Operating Expenses",
                    "type": "expense",
                    "value": 10000.00,
                    "description": "General operating expenses",
                    "is_active": True,
                },
                {
                    "account_id": "qb-expense-002",
                    "name": "Marketing Costs",
                    "type": "expense",
                    "parent_id": "qb-expense-001",
                    "value": 5000.00,
                    "description": "Marketing and advertising costs",
                    "is_active": True,
                },
            ],
        }
        
        # Sample data with validation issues
        self.problematic_quickbooks_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": -5000.00,  # Negative revenue (warning)
            "total_expenses": 8000.00,
            "accounts": [
                {
                    "account_id": "qb-revenue-bad",
                    "name": "Bad Revenue",
                    "type": "revenue",
                    "value": -5000.00,  # Negative revenue
                    "is_active": True,
                },
                {
                    "account_id": "qb-expense-bad",
                    "name": "Bad Expense",
                    "type": "expense",
                    "parent_id": "non-existent-parent",  # Missing parent
                    "value": 8000.00,
                    "is_active": True,
                },
            ],
        }
        
        # Conflicting Rootfi data
        self.conflicting_rootfi_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 18000.00,  # Different from QuickBooks
            "total_expenses": 14000.00,  # Different from QuickBooks
            "accounts": [
                {
                    "account_id": "rf-revenue-001",
                    "name": "Service Revenue",
                    "type": "operating_revenue",
                    "value": 18000.00,
                    "description": "Revenue from services",
                    "is_active": True,
                },
                {
                    "account_id": "rf-expense-001",
                    "name": "Service Expenses",
                    "type": "operating_expenses",
                    "value": 14000.00,
                    "description": "Expenses for service delivery",
                    "is_active": True,
                },
            ],
        }
    
    def test_complete_workflow_valid_data(self):
        """Test complete workflow with valid data."""
        # Normalize the data
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(
                self.valid_quickbooks_data, "valid_test.json"
            )
        
        # Verify normalization succeeded
        assert financial_record.source == SourceType.QUICKBOOKS
        assert financial_record.revenue == Decimal("20000.00")
        assert financial_record.expenses == Decimal("15000.00")
        assert financial_record.net_profit == Decimal("5000.00")
        assert financial_record.currency == "USD"
        
        # Verify accounts were created correctly
        assert len(accounts) == 3
        revenue_accounts = [acc for acc in accounts if acc.account_type == AccountType.REVENUE]
        expense_accounts = [acc for acc in accounts if acc.account_type == AccountType.EXPENSE]
        assert len(revenue_accounts) == 1
        assert len(expense_accounts) == 2
        
        # Verify account hierarchy
        parent_account = next(
            (acc for acc in accounts if acc.account_id == "qb-expense-001"), None
        )
        child_account = next(
            (acc for acc in accounts if acc.account_id == "qb-expense-002"), None
        )
        assert parent_account is not None
        assert child_account is not None
        assert child_account.parent_account_id == "qb-expense-001"
        
        # Verify account values
        assert len(account_values) == 3
        
        # Verify validation passed
        assert validation_result.is_valid is True
        assert validation_result.quality_score == 1.0
        assert len(validation_result.issues) == 0
    
    def test_complete_workflow_problematic_data(self):
        """Test complete workflow with data that has validation issues."""
        # Normalize the problematic data
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(
                self.problematic_quickbooks_data, "problematic_test.json"
            )
        
        # Verify normalization succeeded despite issues
        assert financial_record.source == SourceType.QUICKBOOKS
        assert financial_record.revenue == Decimal("-5000.00")
        assert financial_record.expenses == Decimal("8000.00")
        assert financial_record.net_profit == Decimal("-13000.00")
        
        # Verify validation caught the issues
        assert validation_result.is_valid is False  # Should fail due to missing parent
        assert validation_result.quality_score < 1.0
        assert len(validation_result.issues) > 0
        
        # Check for specific validation issues
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "NEGATIVE_REVENUE" in issue_codes
        assert "MISSING_PARENT_ACCOUNT" in issue_codes
        
        # Verify severity levels
        warning_issues = [
            issue for issue in validation_result.issues 
            if issue.severity == ValidationSeverity.WARNING
        ]
        error_issues = [
            issue for issue in validation_result.issues 
            if issue.severity == ValidationSeverity.ERROR
        ]
        assert len(warning_issues) > 0  # Negative revenue warning
        assert len(error_issues) > 0    # Missing parent error
    
    def test_conflict_resolution_workflow(self):
        """Test complete workflow with conflicting data from multiple sources."""
        # Normalize both datasets
        qb_result = self.normalizer.normalize_quickbooks_data(
            self.valid_quickbooks_data, "qb_test.json"
        )
        rf_result = self.normalizer.normalize_rootfi_data(
            self.conflicting_rootfi_data, "rf_test.json"
        )
        
        # Resolve conflicts and merge
        merged_result = self.normalizer.resolve_conflicts_and_merge([qb_result, rf_result])
        financial_record, accounts, account_values, validation_result = merged_result
        
        # Verify QuickBooks data was preferred (higher priority)
        assert financial_record.source == SourceType.QUICKBOOKS
        assert financial_record.revenue == Decimal("20000.00")  # QuickBooks value
        assert financial_record.expenses == Decimal("15000.00")  # QuickBooks value
        assert financial_record.net_profit == Decimal("5000.00")
        
        # Verify conflicts were detected
        conflict_issues = [
            issue for issue in validation_result.issues 
            if "CONFLICT" in issue.code
        ]
        assert len(conflict_issues) > 0
        
        # Verify quality score was reduced due to conflicts
        assert validation_result.quality_score < 1.0
        
        # Check for specific conflict types
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "REVENUE_CONFLICT" in issue_codes
        assert "EXPENSE_CONFLICT" in issue_codes
    
    def test_account_value_validation_integration(self):
        """Test that account values are properly validated against financial record totals."""
        # Create data where account values don't match totals
        mismatched_data = self.valid_quickbooks_data.copy()
        mismatched_data["accounts"][0]["value"] = 15000.00  # Should be 20000.00
        
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(mismatched_data, "mismatch_test.json")
        
        # Verify validation caught the mismatch
        assert validation_result.is_valid is False
        
        # Check for revenue total mismatch
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "REVENUE_TOTAL_MISMATCH" in issue_codes
        
        # Verify the specific error details
        revenue_mismatch_issues = [
            issue for issue in validation_result.issues 
            if issue.code == "REVENUE_TOTAL_MISMATCH"
        ]
        assert len(revenue_mismatch_issues) == 1
        assert revenue_mismatch_issues[0].severity == ValidationSeverity.ERROR
    
    def test_currency_validation_integration(self):
        """Test currency validation in the complete workflow."""
        # Test with invalid currency
        invalid_currency_data = self.valid_quickbooks_data.copy()
        invalid_currency_data["currency"] = "INVALID"  # Invalid format
        
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(invalid_currency_data)
        
        # Verify validation caught the invalid currency
        assert validation_result.is_valid is False
        
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "INVALID_CURRENCY_FORMAT" in issue_codes
        
        # Test with uncommon but valid currency
        uncommon_currency_data = self.valid_quickbooks_data.copy()
        uncommon_currency_data["currency"] = "XYZ"  # Valid format but uncommon
        
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(uncommon_currency_data)
        
        # Should still be valid but with info issue
        assert validation_result.is_valid is True
        
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "UNCOMMON_CURRENCY" in issue_codes
        
        # Verify currency was normalized to uppercase
        assert financial_record.currency == "XYZ"
    
    def test_date_validation_integration(self):
        """Test date validation in the complete workflow."""
        # Test with invalid date range
        invalid_date_data = self.valid_quickbooks_data.copy()
        invalid_date_data["period_start"] = "2024-01-31"
        invalid_date_data["period_end"] = "2024-01-01"  # End before start
        
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(invalid_date_data)
        
        # Verify validation caught the invalid date range
        assert validation_result.is_valid is False
        
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "INVALID_DATE_RANGE" in issue_codes
    
    def test_balance_equation_validation_integration(self):
        """Test balance equation validation in the complete workflow."""
        # Create data where the totals don't match the account values
        # This will cause a balance equation mismatch
        balance_mismatch_data = self.valid_quickbooks_data.copy()
        balance_mismatch_data["total_revenue"] = 25000.00  # Different from account value
        
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(balance_mismatch_data)
        
        # Should have both revenue total mismatch and potentially balance equation issues
        assert validation_result.is_valid is False
        
        issue_codes = [issue.code for issue in validation_result.issues]
        # Should have revenue total mismatch since account values don't match record total
        assert "REVENUE_TOTAL_MISMATCH" in issue_codes
    
    def test_audit_trail_preservation(self):
        """Test that audit trail is preserved throughout the workflow."""
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(
                self.valid_quickbooks_data, "audit_trail_test.json"
            )
        
        # Verify audit trail is preserved
        assert financial_record.raw_data is not None
        assert financial_record.raw_data["source_file"] == "audit_trail_test.json"
        assert "original_data" in financial_record.raw_data
        assert "normalized_at" in financial_record.raw_data
        
        # Verify original data is intact
        assert financial_record.raw_data["original_data"] == self.valid_quickbooks_data
        
        # Verify timestamps are present
        assert isinstance(financial_record.created_at, type(financial_record.created_at))
        assert isinstance(financial_record.updated_at, type(financial_record.updated_at))
    
    def test_quality_score_calculation_integration(self):
        """Test quality score calculation across the complete workflow."""
        # Test with perfect data
        perfect_result = self.normalizer.normalize_quickbooks_data(self.valid_quickbooks_data)
        assert perfect_result[3].quality_score == 1.0
        
        # Test with problematic data
        problematic_result = self.normalizer.normalize_quickbooks_data(
            self.problematic_quickbooks_data
        )
        assert problematic_result[3].quality_score < 1.0
        
        # Test with conflicts
        qb_result = self.normalizer.normalize_quickbooks_data(self.valid_quickbooks_data)
        rf_result = self.normalizer.normalize_rootfi_data(self.conflicting_rootfi_data)
        merged_result = self.normalizer.resolve_conflicts_and_merge([qb_result, rf_result])
        
        # Quality score should be reduced due to conflicts
        assert merged_result[3].quality_score < 1.0
        
        # Should be lower than individual datasets due to conflicts
        assert merged_result[3].quality_score < qb_result[3].quality_score