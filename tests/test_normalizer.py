"""
Tests for data normalization service.

This module tests the data normalizer that converts parsed data from various sources
into unified schema with comprehensive validation.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any

from app.models.financial import AccountType, SourceType
from app.services.normalizer import DataNormalizer, NormalizationError
from app.services.validation import ValidationSeverity


class TestDataNormalizer:
    """Test cases for DataNormalizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.normalizer = DataNormalizer()
        
        # Sample QuickBooks parsed data
        self.quickbooks_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 15000.00,
            "total_expenses": 10000.00,
            "accounts": [
                {
                    "account_id": "qb-revenue-001",
                    "name": "Sales Revenue",
                    "type": "revenue",
                    "value": 15000.00,
                    "description": "Primary sales revenue",
                    "is_active": True,
                },
                {
                    "account_id": "qb-expense-001",
                    "name": "Office Expenses",
                    "type": "expense",
                    "value": 6000.00,
                    "description": "General office expenses",
                    "is_active": True,
                },
                {
                    "account_id": "qb-expense-002",
                    "name": "Marketing Expenses",
                    "type": "expense",
                    "parent_id": "qb-expense-001",
                    "value": 4000.00,
                    "description": "Marketing and advertising",
                    "is_active": True,
                },
            ],
        }
        
        # Sample Rootfi parsed data
        self.rootfi_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 14500.00,  # Slightly different from QuickBooks
            "total_expenses": 9800.00,
            "accounts": [
                {
                    "account_id": "rf-revenue-001",
                    "name": "Operating Revenue",
                    "type": "operating_revenue",
                    "value": 14500.00,
                    "description": "Main operating revenue",
                    "is_active": True,
                },
                {
                    "account_id": "rf-expense-001",
                    "name": "Operating Expenses",
                    "type": "operating_expenses",
                    "value": 5800.00,
                    "description": "Core operating expenses",
                    "is_active": True,
                },
                {
                    "account_id": "rf-expense-002",
                    "name": "Administrative Costs",
                    "type": "expense",
                    "value": 4000.00,
                    "description": "Administrative overhead",
                    "is_active": True,
                },
            ],
        }
    
    def test_normalize_quickbooks_data_success(self):
        """Test successful normalization of QuickBooks data."""
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_quickbooks_data(self.quickbooks_data, "test_qb.json")
        
        # Check financial record
        assert financial_record.source == SourceType.QUICKBOOKS
        assert financial_record.period_start == date(2024, 1, 1)
        assert financial_record.period_end == date(2024, 1, 31)
        assert financial_record.currency == "USD"
        assert financial_record.revenue == Decimal("15000.00")
        assert financial_record.expenses == Decimal("10000.00")
        assert financial_record.net_profit == Decimal("5000.00")
        assert financial_record.raw_data is not None
        assert financial_record.raw_data["source_file"] == "test_qb.json"
        
        # Check accounts
        assert len(accounts) == 3
        revenue_accounts = [acc for acc in accounts if acc.account_type == AccountType.REVENUE]
        expense_accounts = [acc for acc in accounts if acc.account_type == AccountType.EXPENSE]
        assert len(revenue_accounts) == 1
        assert len(expense_accounts) == 2
        
        # Check account hierarchy
        parent_account = next((acc for acc in accounts if acc.account_id == "qb-expense-001"), None)
        child_account = next((acc for acc in accounts if acc.account_id == "qb-expense-002"), None)
        assert parent_account is not None
        assert child_account is not None
        assert child_account.parent_account_id == "qb-expense-001"
        
        # Check account values
        assert len(account_values) == 3
        total_revenue_values = sum(
            av.value for av in account_values 
            if any(acc.account_id == av.account_id and acc.account_type == AccountType.REVENUE 
                  for acc in accounts)
        )
        total_expense_values = sum(
            av.value for av in account_values 
            if any(acc.account_id == av.account_id and acc.account_type == AccountType.EXPENSE 
                  for acc in accounts)
        )
        assert total_revenue_values == Decimal("15000.00")
        assert total_expense_values == Decimal("10000.00")
        
        # Check validation result
        assert validation_result.is_valid is True
        assert validation_result.quality_score > 0.8  # Should be high quality
    
    def test_normalize_rootfi_data_success(self):
        """Test successful normalization of Rootfi data."""
        financial_record, accounts, account_values, validation_result = \
            self.normalizer.normalize_rootfi_data(self.rootfi_data, "test_rf.json")
        
        # Check financial record
        assert financial_record.source == SourceType.ROOTFI
        assert financial_record.period_start == date(2024, 1, 1)
        assert financial_record.period_end == date(2024, 1, 31)
        assert financial_record.currency == "USD"
        assert financial_record.revenue == Decimal("14500.00")
        assert financial_record.expenses == Decimal("9800.00")
        assert financial_record.net_profit == Decimal("4700.00")
        assert financial_record.raw_data is not None
        assert financial_record.raw_data["source_file"] == "test_rf.json"
        
        # Check accounts
        assert len(accounts) == 3
        revenue_accounts = [acc for acc in accounts if acc.account_type == AccountType.REVENUE]
        expense_accounts = [acc for acc in accounts if acc.account_type == AccountType.EXPENSE]
        assert len(revenue_accounts) == 1
        assert len(expense_accounts) == 2
        
        # Check account values
        assert len(account_values) == 3
        
        # Check validation result
        assert validation_result.is_valid is True
        assert validation_result.quality_score > 0.8
    
    def test_normalize_quickbooks_missing_period_data(self):
        """Test normalization fails with missing period data."""
        invalid_data = self.quickbooks_data.copy()
        del invalid_data["period_start"]
        
        with pytest.raises(NormalizationError, match="Missing period information"):
            self.normalizer.normalize_quickbooks_data(invalid_data)
    
    def test_normalize_rootfi_missing_period_data(self):
        """Test normalization fails with missing period data."""
        invalid_data = self.rootfi_data.copy()
        del invalid_data["period_end"]
        
        with pytest.raises(NormalizationError, match="Missing period information"):
            self.normalizer.normalize_rootfi_data(invalid_data)
    
    def test_map_account_type_common_types(self):
        """Test account type mapping for common types."""
        # Test revenue mappings
        assert self.normalizer._map_account_type("revenue") == AccountType.REVENUE
        assert self.normalizer._map_account_type("income") == AccountType.REVENUE
        assert self.normalizer._map_account_type("sales") == AccountType.REVENUE
        assert self.normalizer._map_account_type("other_income") == AccountType.REVENUE
        assert self.normalizer._map_account_type("operating_revenue") == AccountType.REVENUE
        
        # Test expense mappings
        assert self.normalizer._map_account_type("expense") == AccountType.EXPENSE
        assert self.normalizer._map_account_type("cost") == AccountType.EXPENSE
        assert self.normalizer._map_account_type("operating_expense") == AccountType.EXPENSE
        assert self.normalizer._map_account_type("cost_of_goods_sold") == AccountType.EXPENSE
        assert self.normalizer._map_account_type("operating_expenses") == AccountType.EXPENSE
        
        # Test other types
        assert self.normalizer._map_account_type("asset") == AccountType.ASSET
        assert self.normalizer._map_account_type("liability") == AccountType.LIABILITY
        assert self.normalizer._map_account_type("equity") == AccountType.EQUITY
        
        # Test unknown type defaults to expense
        assert self.normalizer._map_account_type("unknown_type") == AccountType.EXPENSE
    
    def test_resolve_conflicts_and_merge_single_dataset(self):
        """Test conflict resolution with single dataset."""
        qb_normalized = self.normalizer.normalize_quickbooks_data(self.quickbooks_data)
        
        merged_result = self.normalizer.resolve_conflicts_and_merge([qb_normalized])
        
        # Should return the same data
        financial_record, accounts, account_values, validation_result = merged_result
        assert financial_record.source == SourceType.QUICKBOOKS
        assert len(accounts) == 3
        assert len(account_values) == 3
        assert validation_result.is_valid is True
    
    def test_resolve_conflicts_and_merge_multiple_datasets(self):
        """Test conflict resolution with multiple datasets."""
        qb_normalized = self.normalizer.normalize_quickbooks_data(self.quickbooks_data)
        rf_normalized = self.normalizer.normalize_rootfi_data(self.rootfi_data)
        
        merged_result = self.normalizer.resolve_conflicts_and_merge([qb_normalized, rf_normalized])
        
        financial_record, accounts, account_values, validation_result = merged_result
        
        # Should prefer QuickBooks (higher priority)
        assert financial_record.source == SourceType.QUICKBOOKS
        assert financial_record.revenue == Decimal("15000.00")  # QuickBooks value
        assert financial_record.expenses == Decimal("10000.00")  # QuickBooks value
        
        # Should have merged accounts from both sources
        assert len(accounts) >= 3  # At least the accounts from one source
        
        # Should have conflict issues in validation result
        conflict_issues = [
            issue for issue in validation_result.issues 
            if "CONFLICT" in issue.code
        ]
        assert len(conflict_issues) > 0  # Should have detected conflicts
        
        # Quality score should be reduced due to conflicts
        assert validation_result.quality_score < 1.0
    
    def test_merge_accounts_removes_duplicates(self):
        """Test that merging accounts removes duplicates by account_id."""
        # Create duplicate accounts with same ID but different sources
        accounts1 = [
            self.normalizer._create_accounts_from_quickbooks(self.quickbooks_data)[0]
        ]
        accounts2 = [
            self.normalizer._create_accounts_from_rootfi(self.rootfi_data)[0]
        ]
        
        # Manually set same account_id to test deduplication
        accounts2[0].account_id = accounts1[0].account_id
        
        all_accounts = accounts1 + accounts2
        merged_accounts = self.normalizer._merge_accounts(all_accounts)
        
        # Should have only one account (duplicate removed)
        assert len(merged_accounts) == 1
        
        # Should prefer higher priority source (QuickBooks)
        assert merged_accounts[0].source == SourceType.QUICKBOOKS
    
    def test_create_financial_record_with_date_objects(self):
        """Test creating financial record when dates are already date objects."""
        data_with_date_objects = self.quickbooks_data.copy()
        data_with_date_objects["period_start"] = date(2024, 1, 1)
        data_with_date_objects["period_end"] = date(2024, 1, 31)
        
        financial_record = self.normalizer._create_financial_record_from_quickbooks(
            data_with_date_objects, "test.json"
        )
        
        assert financial_record.period_start == date(2024, 1, 1)
        assert financial_record.period_end == date(2024, 1, 31)
    
    def test_create_account_values_skips_zero_values(self):
        """Test that account values with zero amounts are skipped."""
        data_with_zero_values = self.quickbooks_data.copy()
        data_with_zero_values["accounts"].append({
            "account_id": "zero-account",
            "name": "Zero Account",
            "type": "expense",
            "value": 0.00,  # Zero value should be skipped
        })
        
        accounts = self.normalizer._create_accounts_from_quickbooks(data_with_zero_values)
        account_values = self.normalizer._create_account_values_from_quickbooks(
            data_with_zero_values, "test-record-id", accounts
        )
        
        # Should not include the zero-value account
        zero_value_accounts = [av for av in account_values if av.account_id == "zero-account"]
        assert len(zero_value_accounts) == 0
    
    def test_validate_normalized_data_combines_validations(self):
        """Test that validation combines results from all validation types."""
        # Create data that will have validation issues
        financial_record, accounts, account_values, _ = \
            self.normalizer.normalize_quickbooks_data(self.quickbooks_data)
        
        # Modify data to introduce validation issues
        financial_record.net_profit = Decimal("999999.00")  # Wrong net profit
        accounts[0].parent_account_id = "non-existent-parent"  # Missing parent
        
        validation_result = self.normalizer._validate_normalized_data(
            financial_record, accounts, account_values
        )
        
        # Should have issues from multiple validation types
        assert len(validation_result.issues) > 0
        assert validation_result.is_valid is False
        assert validation_result.quality_score < 1.0
        
        # Should have both balance equation and missing parent issues
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "BALANCE_EQUATION_MISMATCH" in issue_codes
        assert "MISSING_PARENT_ACCOUNT" in issue_codes
    
    def test_resolve_conflicts_empty_list_raises_error(self):
        """Test that empty dataset list raises ValueError."""
        with pytest.raises(ValueError, match="No normalized data provided"):
            self.normalizer.resolve_conflicts_and_merge([])
    
    def test_normalization_preserves_audit_trail(self):
        """Test that normalization preserves audit trail in raw_data."""
        financial_record, _, _, _ = self.normalizer.normalize_quickbooks_data(
            self.quickbooks_data, "audit_test.json"
        )
        
        assert financial_record.raw_data is not None
        assert financial_record.raw_data["source_file"] == "audit_test.json"
        assert "original_data" in financial_record.raw_data
        assert "normalized_at" in financial_record.raw_data
        
        # Original data should be preserved
        assert financial_record.raw_data["original_data"] == self.quickbooks_data
    
    def test_currency_normalization_to_uppercase(self):
        """Test that currency codes are normalized to uppercase."""
        data_with_lowercase_currency = self.quickbooks_data.copy()
        data_with_lowercase_currency["currency"] = "usd"  # lowercase
        
        financial_record, _, _, _ = self.normalizer.normalize_quickbooks_data(
            data_with_lowercase_currency
        )
        
        assert financial_record.currency == "USD"  # Should be uppercase
    
    def test_account_name_and_description_handling(self):
        """Test proper handling of account names and descriptions."""
        financial_record, accounts, _, _ = self.normalizer.normalize_quickbooks_data(
            self.quickbooks_data
        )
        
        # Check that account names and descriptions are preserved
        revenue_account = next(
            acc for acc in accounts if acc.account_type == AccountType.REVENUE
        )
        assert revenue_account.name == "Sales Revenue"
        assert revenue_account.description == "Primary sales revenue"
        
        # Check that is_active flag is preserved
        assert revenue_account.is_active is True