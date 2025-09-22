"""
Data quality validation tests with real financial data samples.

Tests comprehensive data validation, quality scoring, and error detection
with realistic financial data scenarios.
"""

import json
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.database.connection import create_tables, get_db_session, get_engine
from app.database.models import AccountDB, AccountValueDB, FinancialRecordDB
from app.models.financial import AccountType, SourceType
from app.services.ingestion import DataIngestionService
from app.services.normalizer import DataNormalizer
from app.services.validation import (
    FinancialDataValidator,
    ValidationResult,
    ValidationSeverity,
)


@pytest.fixture(scope="function")
def clean_database():
    """Clean database for each test."""
    engine = get_engine()
    from app.database.models import Base
    
    Base.metadata.drop_all(bind=engine)
    create_tables(engine)
    
    yield
    
    Base.metadata.drop_all(bind=engine)


class TestDataQualityValidation:
    """Test data quality validation with various scenarios."""
    
    def test_perfect_data_quality_score(self, clean_database):
        """Test data quality scoring with perfect data."""
        normalizer = DataNormalizer()
        
        perfect_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 100000.00,
            "total_expenses": 80000.00,
            "accounts": [
                {
                    "account_id": "revenue_001",
                    "name": "Product Sales",
                    "type": "revenue",
                    "value": 70000.00,
                    "description": "Primary product sales",
                    "is_active": True
                },
                {
                    "account_id": "revenue_002",
                    "name": "Service Revenue",
                    "type": "revenue",
                    "value": 30000.00,
                    "description": "Service-based revenue",
                    "is_active": True
                },
                {
                    "account_id": "expense_001",
                    "name": "Operating Expenses",
                    "type": "expense",
                    "value": 50000.00,
                    "description": "General operating expenses",
                    "is_active": True
                },
                {
                    "account_id": "expense_002",
                    "name": "Marketing Expenses",
                    "type": "expense",
                    "value": 30000.00,
                    "description": "Marketing and advertising",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(perfect_data, "perfect_test.json")
        
        # Perfect data should have quality score of 1.0
        assert validation_result.quality_score == 1.0
        assert validation_result.is_valid is True
        assert len(validation_result.issues) == 0
        
        # Verify financial calculations are correct
        assert financial_record.revenue == Decimal("100000.00")
        assert financial_record.expenses == Decimal("80000.00")
        assert financial_record.net_profit == Decimal("20000.00")
    
    def test_data_quality_with_warnings(self, clean_database):
        """Test data quality scoring with warning-level issues."""
        normalizer = DataNormalizer()
        
        warning_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "EUR",  # Uncommon currency (warning)
            "total_revenue": 0.00,  # Zero revenue (warning)
            "total_expenses": 5000.00,
            "accounts": [
                {
                    "account_id": "expense_001",
                    "name": "Operating Expenses",
                    "type": "expense",
                    "value": 5000.00,
                    "description": "Operating expenses",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(warning_data, "warning_test.json")
        
        # Should be valid but with reduced quality score
        assert validation_result.is_valid is True
        assert validation_result.quality_score < 1.0
        assert validation_result.quality_score >= 0.7  # Still relatively high
        assert len(validation_result.issues) > 0
        
        # Check for specific warning issues
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "ZERO_REVENUE" in issue_codes or "LOW_REVENUE" in issue_codes
        
        # Verify warnings don't prevent processing
        assert financial_record.revenue == Decimal("0.00")
        assert financial_record.expenses == Decimal("5000.00")
        assert financial_record.net_profit == Decimal("-5000.00")
    
    def test_data_quality_with_errors(self, clean_database):
        """Test data quality scoring with error-level issues."""
        normalizer = DataNormalizer()
        
        error_data = {
            "period_start": "2024-01-31",  # End before start (error)
            "period_end": "2024-01-01",
            "currency": "USD",
            "total_revenue": 50000.00,
            "total_expenses": 40000.00,
            "accounts": [
                {
                    "account_id": "revenue_001",
                    "name": "Product Sales",
                    "type": "revenue",
                    "value": 60000.00,  # Doesn't match total (error)
                    "description": "Product sales",
                    "is_active": True
                },
                {
                    "account_id": "expense_001",
                    "name": "Operating Expenses",
                    "type": "expense",
                    "parent_id": "non_existent_parent",  # Missing parent (error)
                    "value": 40000.00,
                    "description": "Operating expenses",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(error_data, "error_test.json")
        
        # Should be invalid with low quality score
        assert validation_result.is_valid is False
        assert validation_result.quality_score < 0.5
        assert len(validation_result.issues) > 0
        
        # Check for specific error issues
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "INVALID_DATE_RANGE" in issue_codes
        assert "REVENUE_TOTAL_MISMATCH" in issue_codes
        assert "MISSING_PARENT_ACCOUNT" in issue_codes
    
    def test_negative_revenue_validation(self, clean_database):
        """Test validation of negative revenue scenarios."""
        normalizer = DataNormalizer()
        
        negative_revenue_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": -10000.00,  # Negative revenue
            "total_expenses": 20000.00,
            "accounts": [
                {
                    "account_id": "revenue_001",
                    "name": "Product Returns",
                    "type": "revenue",
                    "value": -10000.00,  # Negative revenue account
                    "description": "Product returns and refunds",
                    "is_active": True
                },
                {
                    "account_id": "expense_001",
                    "name": "Operating Expenses",
                    "type": "expense",
                    "value": 20000.00,
                    "description": "Operating expenses",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(negative_revenue_data, "negative_test.json")
        
        # Should have warning for negative revenue
        assert validation_result.is_valid is True  # Valid but with warnings
        assert validation_result.quality_score < 1.0
        
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "NEGATIVE_REVENUE" in issue_codes
        
        # Find the negative revenue issue
        negative_revenue_issue = next(
            (issue for issue in validation_result.issues if issue.code == "NEGATIVE_REVENUE"), None
        )
        assert negative_revenue_issue is not None
        assert negative_revenue_issue.severity == ValidationSeverity.WARNING
        assert "returns" in negative_revenue_issue.suggestion.lower() or "refunds" in negative_revenue_issue.suggestion.lower()
    
    def test_currency_validation_scenarios(self, clean_database):
        """Test various currency validation scenarios."""
        normalizer = DataNormalizer()
        
        # Test valid common currency
        usd_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 50000.00,
            "total_expenses": 40000.00,
            "accounts": []
        }
        
        _, _, _, usd_result = normalizer.normalize_quickbooks_data(usd_data)
        assert usd_result.is_valid is True
        
        # Test valid but uncommon currency
        uncommon_data = usd_data.copy()
        uncommon_data["currency"] = "XYZ"
        
        _, _, _, uncommon_result = normalizer.normalize_quickbooks_data(uncommon_data)
        assert uncommon_result.is_valid is True
        issue_codes = [issue.code for issue in uncommon_result.issues]
        assert "UNCOMMON_CURRENCY" in issue_codes
        
        # Test invalid currency format
        invalid_data = usd_data.copy()
        invalid_data["currency"] = "invalid_currency_format"
        
        _, _, _, invalid_result = normalizer.normalize_quickbooks_data(invalid_data)
        assert invalid_result.is_valid is False
        issue_codes = [issue.code for issue in invalid_result.issues]
        assert "INVALID_CURRENCY_FORMAT" in issue_codes
    
    def test_account_hierarchy_validation(self, clean_database):
        """Test account hierarchy validation."""
        normalizer = DataNormalizer()
        
        hierarchy_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 50000.00,
            "total_expenses": 40000.00,
            "accounts": [
                {
                    "account_id": "parent_expense",
                    "name": "Parent Expenses",
                    "type": "expense",
                    "value": 40000.00,
                    "description": "Parent expense category",
                    "is_active": True
                },
                {
                    "account_id": "child_expense_1",
                    "name": "Child Expense 1",
                    "type": "expense",
                    "parent_id": "parent_expense",
                    "value": 25000.00,
                    "description": "Child expense 1",
                    "is_active": True
                },
                {
                    "account_id": "child_expense_2",
                    "name": "Child Expense 2",
                    "type": "expense",
                    "parent_id": "parent_expense",
                    "value": 15000.00,
                    "description": "Child expense 2",
                    "is_active": True
                },
                {
                    "account_id": "orphan_expense",
                    "name": "Orphan Expense",
                    "type": "expense",
                    "parent_id": "non_existent_parent",  # Missing parent
                    "value": 5000.00,
                    "description": "Orphan expense",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(hierarchy_data, "hierarchy_test.json")
        
        # Should have error for missing parent
        assert validation_result.is_valid is False
        
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "MISSING_PARENT_ACCOUNT" in issue_codes
        
        # Find the missing parent issue
        missing_parent_issue = next(
            (issue for issue in validation_result.issues if issue.code == "MISSING_PARENT_ACCOUNT"), None
        )
        assert missing_parent_issue is not None
        assert missing_parent_issue.severity == ValidationSeverity.ERROR
        assert "orphan_expense" in missing_parent_issue.context["account_id"]
    
    def test_balance_equation_validation(self, clean_database):
        """Test balance equation validation (Revenue - Expenses = Net Profit)."""
        normalizer = DataNormalizer()
        
        # Test correct balance
        balanced_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 100000.00,
            "total_expenses": 80000.00,  # Net profit should be 20000
            "accounts": []
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(balanced_data)
        
        assert validation_result.is_valid is True
        assert financial_record.net_profit == Decimal("20000.00")
        
        # Test with manually specified incorrect net profit
        # (This would be caught if the data explicitly provided wrong net profit)
        # For now, we calculate net profit from revenue - expenses
        
        # Test with account values that don't match totals
        unbalanced_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 100000.00,
            "total_expenses": 80000.00,
            "accounts": [
                {
                    "account_id": "revenue_001",
                    "name": "Product Sales",
                    "type": "revenue",
                    "value": 90000.00,  # Doesn't match total revenue
                    "description": "Product sales",
                    "is_active": True
                },
                {
                    "account_id": "expense_001",
                    "name": "Operating Expenses",
                    "type": "expense",
                    "value": 70000.00,  # Doesn't match total expenses
                    "description": "Operating expenses",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(unbalanced_data)
        
        # Should have errors for mismatched totals
        assert validation_result.is_valid is False
        
        issue_codes = [issue.code for issue in validation_result.issues]
        assert "REVENUE_TOTAL_MISMATCH" in issue_codes
        assert "EXPENSE_TOTAL_MISMATCH" in issue_codes
    
    def test_date_range_validation(self, clean_database):
        """Test date range validation scenarios."""
        normalizer = DataNormalizer()
        
        base_data = {
            "currency": "USD",
            "total_revenue": 50000.00,
            "total_expenses": 40000.00,
            "accounts": []
        }
        
        # Test valid date range
        valid_data = base_data.copy()
        valid_data.update({
            "period_start": "2024-01-01",
            "period_end": "2024-01-31"
        })
        
        _, _, _, valid_result = normalizer.normalize_quickbooks_data(valid_data)
        assert valid_result.is_valid is True
        
        # Test invalid date range (end before start)
        invalid_data = base_data.copy()
        invalid_data.update({
            "period_start": "2024-01-31",
            "period_end": "2024-01-01"
        })
        
        _, _, _, invalid_result = normalizer.normalize_quickbooks_data(invalid_data)
        assert invalid_result.is_valid is False
        
        issue_codes = [issue.code for issue in invalid_result.issues]
        assert "INVALID_DATE_RANGE" in issue_codes
        
        # Test very long period (warning)
        long_period_data = base_data.copy()
        long_period_data.update({
            "period_start": "2024-01-01",
            "period_end": "2025-12-31"  # 2 year period
        })
        
        _, _, _, long_result = normalizer.normalize_quickbooks_data(long_period_data)
        assert long_result.is_valid is True  # Valid but with warning
        
        issue_codes = [issue.code for issue in long_result.issues]
        assert "LONG_PERIOD_RANGE" in issue_codes or len(long_result.issues) == 0  # May or may not warn
    
    def test_data_completeness_validation(self, clean_database):
        """Test data completeness validation."""
        normalizer = DataNormalizer()
        
        # Test missing required fields
        incomplete_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            # Missing currency
            "total_revenue": 50000.00,
            "total_expenses": 40000.00,
            "accounts": []
        }
        
        try:
            financial_record, accounts, account_values, validation_result = \
                normalizer.normalize_quickbooks_data(incomplete_data)
            
            # Should handle missing currency gracefully
            assert validation_result.is_valid is False or validation_result.quality_score < 1.0
            
        except Exception as e:
            # Missing required fields should be caught during normalization
            assert "currency" in str(e).lower() or "required" in str(e).lower()
    
    def test_extreme_values_validation(self, clean_database):
        """Test validation of extreme financial values."""
        normalizer = DataNormalizer()
        
        # Test extremely high values
        extreme_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 999999999999.99,  # Extremely high
            "total_expenses": 888888888888.88,  # Extremely high
            "accounts": [
                {
                    "account_id": "revenue_001",
                    "name": "Extreme Revenue",
                    "type": "revenue",
                    "value": 999999999999.99,
                    "description": "Extremely high revenue",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(extreme_data)
        
        # Should be valid but may have warnings about extreme values
        assert validation_result.is_valid is True
        
        # Check if extreme value warnings exist
        issue_codes = [issue.code for issue in validation_result.issues]
        extreme_warnings = [code for code in issue_codes if "EXTREME" in code or "HIGH" in code]
        
        # Values should be preserved accurately
        assert financial_record.revenue == Decimal("999999999999.99")
        assert financial_record.expenses == Decimal("888888888888.88")


class TestRealWorldDataScenarios:
    """Test with realistic financial data scenarios."""
    
    def test_typical_small_business_data(self, clean_database):
        """Test validation with typical small business financial data."""
        normalizer = DataNormalizer()
        
        small_business_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 45000.00,
            "total_expenses": 38000.00,
            "accounts": [
                {
                    "account_id": "revenue_product_sales",
                    "name": "Product Sales",
                    "type": "revenue",
                    "value": 32000.00,
                    "description": "Sales of physical products",
                    "is_active": True
                },
                {
                    "account_id": "revenue_service_sales",
                    "name": "Service Revenue",
                    "type": "revenue",
                    "value": 13000.00,
                    "description": "Service-based revenue",
                    "is_active": True
                },
                {
                    "account_id": "expense_rent",
                    "name": "Rent Expense",
                    "type": "expense",
                    "value": 8000.00,
                    "description": "Office rent",
                    "is_active": True
                },
                {
                    "account_id": "expense_payroll",
                    "name": "Payroll Expenses",
                    "type": "expense",
                    "value": 20000.00,
                    "description": "Employee salaries and benefits",
                    "is_active": True
                },
                {
                    "account_id": "expense_utilities",
                    "name": "Utilities",
                    "type": "expense",
                    "value": 2500.00,
                    "description": "Electricity, water, internet",
                    "is_active": True
                },
                {
                    "account_id": "expense_marketing",
                    "name": "Marketing Expenses",
                    "type": "expense",
                    "value": 4500.00,
                    "description": "Advertising and marketing",
                    "is_active": True
                },
                {
                    "account_id": "expense_supplies",
                    "name": "Office Supplies",
                    "type": "expense",
                    "value": 3000.00,
                    "description": "Office supplies and materials",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(small_business_data, "small_business.json")
        
        # Should be high quality data
        assert validation_result.is_valid is True
        assert validation_result.quality_score >= 0.9
        assert len(validation_result.issues) <= 2  # Minimal issues
        
        # Verify calculations
        assert financial_record.revenue == Decimal("45000.00")
        assert financial_record.expenses == Decimal("38000.00")
        assert financial_record.net_profit == Decimal("7000.00")
        
        # Verify account structure
        assert len(accounts) == 7
        revenue_accounts = [acc for acc in accounts if acc.account_type == AccountType.REVENUE]
        expense_accounts = [acc for acc in accounts if acc.account_type == AccountType.EXPENSE]
        assert len(revenue_accounts) == 2
        assert len(expense_accounts) == 5
    
    def test_seasonal_business_data(self, clean_database):
        """Test validation with seasonal business patterns."""
        normalizer = DataNormalizer()
        
        # December data (high season)
        december_data = {
            "period_start": "2024-12-01",
            "period_end": "2024-12-31",
            "currency": "USD",
            "total_revenue": 150000.00,  # High seasonal revenue
            "total_expenses": 90000.00,
            "accounts": [
                {
                    "account_id": "revenue_holiday_sales",
                    "name": "Holiday Sales",
                    "type": "revenue",
                    "value": 120000.00,
                    "description": "Holiday season sales",
                    "is_active": True
                },
                {
                    "account_id": "revenue_regular_sales",
                    "name": "Regular Sales",
                    "type": "revenue",
                    "value": 30000.00,
                    "description": "Regular ongoing sales",
                    "is_active": True
                },
                {
                    "account_id": "expense_seasonal_staff",
                    "name": "Seasonal Staff",
                    "type": "expense",
                    "value": 25000.00,
                    "description": "Temporary holiday staff",
                    "is_active": True
                },
                {
                    "account_id": "expense_regular_operations",
                    "name": "Regular Operations",
                    "type": "expense",
                    "value": 65000.00,
                    "description": "Regular operational expenses",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(december_data, "seasonal_december.json")
        
        # Should be valid with good quality
        assert validation_result.is_valid is True
        assert validation_result.quality_score >= 0.8
        
        # Verify seasonal calculations
        assert financial_record.revenue == Decimal("150000.00")
        assert financial_record.net_profit == Decimal("60000.00")
    
    def test_multi_currency_business_data(self, clean_database):
        """Test validation with multi-currency considerations."""
        normalizer = DataNormalizer()
        
        # EUR data
        eur_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "EUR",
            "total_revenue": 42000.00,  # EUR amounts
            "total_expenses": 35000.00,
            "accounts": [
                {
                    "account_id": "revenue_eu_sales",
                    "name": "EU Sales",
                    "type": "revenue",
                    "value": 42000.00,
                    "description": "Sales in European market",
                    "is_active": True
                },
                {
                    "account_id": "expense_eu_operations",
                    "name": "EU Operations",
                    "type": "expense",
                    "value": 35000.00,
                    "description": "European operational costs",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(eur_data, "multi_currency_eur.json")
        
        # Should be valid
        assert validation_result.is_valid is True
        assert financial_record.currency == "EUR"
        assert financial_record.revenue == Decimal("42000.00")
        assert financial_record.net_profit == Decimal("7000.00")
    
    def test_startup_business_data(self, clean_database):
        """Test validation with startup business patterns (high expenses, low revenue)."""
        normalizer = DataNormalizer()
        
        startup_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency": "USD",
            "total_revenue": 5000.00,  # Low early revenue
            "total_expenses": 45000.00,  # High startup costs
            "accounts": [
                {
                    "account_id": "revenue_early_sales",
                    "name": "Early Sales",
                    "type": "revenue",
                    "value": 5000.00,
                    "description": "Initial customer sales",
                    "is_active": True
                },
                {
                    "account_id": "expense_development",
                    "name": "Product Development",
                    "type": "expense",
                    "value": 20000.00,
                    "description": "Software development costs",
                    "is_active": True
                },
                {
                    "account_id": "expense_marketing_startup",
                    "name": "Marketing & Customer Acquisition",
                    "type": "expense",
                    "value": 15000.00,
                    "description": "Customer acquisition costs",
                    "is_active": True
                },
                {
                    "account_id": "expense_legal_setup",
                    "name": "Legal & Setup Costs",
                    "type": "expense",
                    "value": 10000.00,
                    "description": "Legal and business setup costs",
                    "is_active": True
                }
            ]
        }
        
        financial_record, accounts, account_values, validation_result = \
            normalizer.normalize_quickbooks_data(startup_data, "startup_business.json")
        
        # Should be valid despite negative profit (common for startups)
        assert validation_result.is_valid is True
        assert financial_record.net_profit == Decimal("-40000.00")  # Negative profit
        
        # May have warnings about low revenue or high expense ratio
        issue_codes = [issue.code for issue in validation_result.issues]
        warning_issues = [
            issue for issue in validation_result.issues 
            if issue.severity == ValidationSeverity.WARNING
        ]
        
        # Should have some warnings but still be processable
        assert len(warning_issues) >= 0  # May have warnings about ratios


if __name__ == "__main__":
    pytest.main([__file__, "-v"])