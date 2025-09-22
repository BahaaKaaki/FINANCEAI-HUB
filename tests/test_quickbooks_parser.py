"""
Unit tests for QuickBooks parser.

Tests the parsing functionality for QuickBooks P&L JSON format including
account hierarchies, financial data extraction, and error handling.
"""

import json
import pytest
import tempfile
import os
from datetime import date
from decimal import Decimal
from unittest.mock import patch, mock_open

from app.parsers.quickbooks_parser import (
    QuickBooksParser, QuickBooksParseError, parse_quickbooks_file
)
from app.models.financial import SourceType, AccountType


class TestQuickBooksParser:
    """Test cases for QuickBooks parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = QuickBooksParser()
        
        # Sample QuickBooks data structure
        self.sample_data = {
            "data": {
                "Header": {
                    "Time": "2025-08-01T00:18:27-07:00",
                    "ReportName": "ProfitAndLoss",
                    "ReportBasis": "Accrual",
                    "StartPeriod": "2020-01-01",
                    "EndPeriod": "2020-03-31",
                    "SummarizeColumnsBy": "Month",
                    "Currency": "USD"
                },
                "Columns": {
                    "Column": [
                        {
                            "ColTitle": "",
                            "ColType": "Account",
                            "MetaData": [{"Name": "ColKey", "Value": "account"}]
                        },
                        {
                            "ColTitle": "Jan 2020",
                            "ColType": "Money",
                            "MetaData": [
                                {"Name": "StartDate", "Value": "2020-01-01"},
                                {"Name": "EndDate", "Value": "2020-01-31"},
                                {"Name": "ColKey", "Value": "Jan 2020"}
                            ]
                        },
                        {
                            "ColTitle": "Feb 2020",
                            "ColType": "Money",
                            "MetaData": [
                                {"Name": "StartDate", "Value": "2020-02-01"},
                                {"Name": "EndDate", "Value": "2020-02-29"},
                                {"Name": "ColKey", "Value": "Feb 2020"}
                            ]
                        }
                    ]
                },
                "Rows": {
                    "Row": [
                        {
                            "Header": {
                                "ColData": [
                                    {"value": "Income", "id": "1"},
                                    {"value": ""},
                                    {"value": ""}
                                ]
                            },
                            "Rows": {
                                "Row": [
                                    {
                                        "Header": {
                                            "ColData": [
                                                {"value": "Service Revenue", "id": "101"},
                                                {"value": "10000.00"},
                                                {"value": "12000.00"}
                                            ]
                                        }
                                    },
                                    {
                                        "Header": {
                                            "ColData": [
                                                {"value": "Product Sales", "id": "102"},
                                                {"value": "5000.00"},
                                                {"value": "6000.00"}
                                            ]
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            "Header": {
                                "ColData": [
                                    {"value": "Expenses", "id": "2"},
                                    {"value": ""},
                                    {"value": ""}
                                ]
                            },
                            "Rows": {
                                "Row": [
                                    {
                                        "Header": {
                                            "ColData": [
                                                {"value": "Office Rent", "id": "201"},
                                                {"value": "2000.00"},
                                                {"value": "2000.00"}
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }
    
    def test_parse_header(self):
        """Test header parsing for currency and metadata extraction."""
        header = self.sample_data["data"]["Header"]
        self.parser._parse_header(header)
        
        assert self.parser.currency == "USD"
    
    def test_parse_header_default_currency(self):
        """Test header parsing with missing currency defaults to USD."""
        header = {"ReportName": "ProfitAndLoss"}
        self.parser._parse_header(header)
        
        assert self.parser.currency == "USD"
    
    def test_parse_columns(self):
        """Test column parsing for time period extraction."""
        columns = self.sample_data["data"]["Columns"]["Column"]
        self.parser._parse_columns(columns)
        
        assert len(self.parser.periods) == 2
        
        # Check first period
        period1 = self.parser.periods[0]
        assert period1["title"] == "Jan 2020"
        assert period1["start_date"] == date(2020, 1, 1)
        assert period1["end_date"] == date(2020, 1, 31)
        assert period1["col_key"] == "Jan 2020"
        
        # Check second period
        period2 = self.parser.periods[1]
        assert period2["title"] == "Feb 2020"
        assert period2["start_date"] == date(2020, 2, 1)
        assert period2["end_date"] == date(2020, 2, 29)
    
    def test_parse_columns_invalid_date(self):
        """Test column parsing with invalid date format."""
        columns = [{
            "ColTitle": "Invalid Month",
            "ColType": "Money",
            "MetaData": [
                {"Name": "StartDate", "Value": "invalid-date"},
                {"Name": "EndDate", "Value": "2020-01-31"}
            ]
        }]
        
        self.parser._parse_columns(columns)
        assert len(self.parser.periods) == 0  # Should skip invalid dates
    
    def test_determine_account_type_revenue(self):
        """Test account type determination for revenue accounts."""
        assert self.parser._determine_account_type("Service Revenue", 1) == AccountType.REVENUE
        assert self.parser._determine_account_type("Product Sales", 1) == AccountType.REVENUE
        assert self.parser._determine_account_type("Consulting Income", 1) == AccountType.REVENUE
        assert self.parser._determine_account_type("Subscription Revenue", 1) == AccountType.REVENUE
    
    def test_determine_account_type_expense(self):
        """Test account type determination for expense accounts."""
        assert self.parser._determine_account_type("Office Rent", 1) == AccountType.EXPENSE
        assert self.parser._determine_account_type("Payroll Expense", 1) == AccountType.EXPENSE
        assert self.parser._determine_account_type("Marketing Costs", 1) == AccountType.EXPENSE
        assert self.parser._determine_account_type("Travel Expense", 1) == AccountType.EXPENSE
    
    def test_determine_account_type_asset(self):
        """Test account type determination for asset accounts."""
        assert self.parser._determine_account_type("Cash Account", 1) == AccountType.ASSET
        assert self.parser._determine_account_type("Bank Checking", 1) == AccountType.ASSET
        assert self.parser._determine_account_type("Accounts Receivable", 1) == AccountType.ASSET
        assert self.parser._determine_account_type("Equipment", 1) == AccountType.ASSET
    
    def test_determine_account_type_liability(self):
        """Test account type determination for liability accounts."""
        assert self.parser._determine_account_type("Accounts Payable", 1) == AccountType.LIABILITY
        assert self.parser._determine_account_type("Bank Loan", 1) == AccountType.LIABILITY
        assert self.parser._determine_account_type("Credit Card Debt", 1) == AccountType.LIABILITY
        assert self.parser._determine_account_type("Accrued Expenses", 1) == AccountType.LIABILITY
    
    def test_determine_account_type_top_level(self):
        """Test account type determination for top-level accounts."""
        assert self.parser._determine_account_type("Income", 0) == AccountType.REVENUE
        assert self.parser._determine_account_type("Expenses", 0) == AccountType.EXPENSE
        assert self.parser._determine_account_type("Other Category", 0) == AccountType.EXPENSE
    
    def test_generate_account_id(self):
        """Test account ID generation."""
        # Test without parent
        account_id = self.parser._generate_account_id("Service Revenue", None)
        assert account_id == "qb_service_revenue"
        
        # Test with parent
        account_id = self.parser._generate_account_id("Consulting", "qb_service_revenue")
        assert account_id == "qb_service_revenue_consulting"
        
        # Test with special characters
        account_id = self.parser._generate_account_id("Office-Rent & Utilities", None)
        assert account_id == "qb_office_rent_&_utilities"
    
    def test_generate_record_id(self):
        """Test financial record ID generation."""
        start_date = date(2020, 1, 1)
        end_date = date(2020, 1, 31)
        
        record_id = self.parser._generate_record_id(start_date, end_date)
        assert record_id == "qb_20200101_20200131"
    
    def test_parse_data_complete(self):
        """Test complete data parsing workflow."""
        financial_records, accounts, account_values = self.parser.parse_data(self.sample_data)
        
        # Check financial records
        assert len(financial_records) == 2  # Two periods
        
        record1 = financial_records[0]
        assert record1.source == SourceType.QUICKBOOKS
        assert record1.period_start == date(2020, 1, 1)
        assert record1.period_end == date(2020, 1, 31)
        assert record1.currency == "USD"
        assert record1.revenue == Decimal("15000.00")  # 10000 + 5000
        assert record1.expenses == Decimal("2000.00")
        
        record2 = financial_records[1]
        assert record2.period_start == date(2020, 2, 1)
        assert record2.period_end == date(2020, 2, 29)
        assert record2.revenue == Decimal("18000.00")  # 12000 + 6000
        assert record2.expenses == Decimal("2000.00")
        
        # Check accounts
        assert len(accounts) >= 4  # At least Income, Service Revenue, Product Sales, Office Rent
        
        # Find specific accounts
        service_account = next((a for a in accounts if a.name == "Service Revenue"), None)
        assert service_account is not None
        assert service_account.account_type == AccountType.REVENUE
        assert service_account.source == SourceType.QUICKBOOKS
        
        rent_account = next((a for a in accounts if a.name == "Office Rent"), None)
        assert rent_account is not None
        assert rent_account.account_type == AccountType.EXPENSE
        
        # Check account values
        assert len(account_values) >= 6  # At least 3 accounts × 2 periods
    
    def test_parse_account_values_empty_values(self):
        """Test parsing account values with empty or missing values."""
        account_id = "test_account"
        value_columns = [
            {"value": ""},  # Empty string
            {"value": "1000.00"},  # Valid value
            {}  # Missing value key
        ]
        
        # Set up periods
        self.parser.periods = [
            {"start_date": date(2020, 1, 1), "end_date": date(2020, 1, 31)},
            {"start_date": date(2020, 2, 1), "end_date": date(2020, 2, 29)},
            {"start_date": date(2020, 3, 1), "end_date": date(2020, 3, 31)}
        ]
        
        self.parser._parse_account_values(account_id, value_columns)
        
        # Should only create one account value for the valid entry
        assert len(self.parser.account_values) == 1
        assert self.parser.account_values[0]["value"] == Decimal("1000.00")
    
    def test_parse_account_values_invalid_decimal(self):
        """Test parsing account values with invalid decimal format."""
        account_id = "test_account"
        value_columns = [
            {"value": "invalid_number"},
            {"value": "1000.00"}
        ]
        
        # Set up periods
        self.parser.periods = [
            {"start_date": date(2020, 1, 1), "end_date": date(2020, 1, 31)},
            {"start_date": date(2020, 2, 1), "end_date": date(2020, 2, 29)}
        ]
        
        self.parser._parse_account_values(account_id, value_columns)
        
        # Should only create one account value for the valid entry
        assert len(self.parser.account_values) == 1
        assert self.parser.account_values[0]["value"] == Decimal("1000.00")
    
    def test_calculate_period_totals(self):
        """Test calculation of revenue and expense totals for a period."""
        # Set up test data
        record_id = "test_record"
        
        self.parser.accounts = {
            "rev1": {"account_type": AccountType.REVENUE},
            "rev2": {"account_type": AccountType.REVENUE},
            "exp1": {"account_type": AccountType.EXPENSE},
            "exp2": {"account_type": AccountType.EXPENSE}
        }
        
        self.parser.account_values = [
            {"account_id": "rev1", "financial_record_id": record_id, "value": Decimal("1000.00")},
            {"account_id": "rev2", "financial_record_id": record_id, "value": Decimal("2000.00")},
            {"account_id": "exp1", "financial_record_id": record_id, "value": Decimal("500.00")},
            {"account_id": "exp2", "financial_record_id": record_id, "value": Decimal("300.00")},
            {"account_id": "rev1", "financial_record_id": "other_record", "value": Decimal("9999.00")}  # Different record
        ]
        
        revenue, expenses = self.parser._calculate_period_totals(record_id)
        
        assert revenue == Decimal("3000.00")  # 1000 + 2000
        assert expenses == Decimal("800.00")   # 500 + 300
    
    def test_calculate_period_totals_negative_values(self):
        """Test calculation with negative values (should be converted to positive)."""
        record_id = "test_record"
        
        self.parser.accounts = {
            "rev1": {"account_type": AccountType.REVENUE},
            "exp1": {"account_type": AccountType.EXPENSE}
        }
        
        self.parser.account_values = [
            {"account_id": "rev1", "financial_record_id": record_id, "value": Decimal("-1000.00")},
            {"account_id": "exp1", "financial_record_id": record_id, "value": Decimal("-500.00")}
        ]
        
        revenue, expenses = self.parser._calculate_period_totals(record_id)
        
        assert revenue == Decimal("1000.00")   # abs(-1000)
        assert expenses == Decimal("500.00")   # abs(-500)
    
    def test_parse_file_success(self):
        """Test successful file parsing."""
        # Create temporary file with sample data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name
        
        try:
            financial_records, accounts, account_values = self.parser.parse_file(temp_file)
            
            assert len(financial_records) == 2
            assert len(accounts) >= 4
            assert len(account_values) >= 6
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        with pytest.raises(QuickBooksParseError) as exc_info:
            self.parser.parse_file("non_existent_file.json")
        
        assert "Failed to load file" in str(exc_info.value)
    
    def test_parse_file_invalid_json(self):
        """Test parsing file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            with pytest.raises(QuickBooksParseError) as exc_info:
                self.parser.parse_file(temp_file)
            
            assert "Failed to load file" in str(exc_info.value)
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_data_missing_structure(self):
        """Test parsing data with missing required structure."""
        invalid_data = {"invalid": "structure"}
        
        # Should not raise exception but return empty results
        financial_records, accounts, account_values = self.parser.parse_data(invalid_data)
        
        assert len(financial_records) == 0
        assert len(accounts) == 0
        assert len(account_values) == 0
    
    def test_parse_data_empty_rows(self):
        """Test parsing data with empty rows section."""
        data_with_empty_rows = {
            "data": {
                "Header": {"Currency": "EUR"},
                "Columns": {"Column": []},
                "Rows": {"Row": []}
            }
        }
        
        financial_records, accounts, account_values = self.parser.parse_data(data_with_empty_rows)
        
        assert len(financial_records) == 0
        assert len(accounts) == 0
        assert len(account_values) == 0
        assert self.parser.currency == "EUR"
    
    def test_extract_account_id_from_row(self):
        """Test extracting account ID from row header."""
        # Test with ID present
        header_with_id = {
            "ColData": [
                {"value": "Test Account", "id": "123"},
                {"value": "1000.00"}
            ]
        }
        
        account_id = self.parser._extract_account_id_from_row(header_with_id)
        assert account_id == "123"
        
        # Test without ID
        header_without_id = {
            "ColData": [
                {"value": "Test Account"},
                {"value": "1000.00"}
            ]
        }
        
        account_id = self.parser._extract_account_id_from_row(header_without_id)
        assert account_id is None
        
        # Test with empty header
        empty_header = {}
        account_id = self.parser._extract_account_id_from_row(empty_header)
        assert account_id is None
    
    def test_convenience_function(self):
        """Test the convenience function for parsing QuickBooks files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name
        
        try:
            financial_records, accounts, account_values = parse_quickbooks_file(temp_file)
            
            assert len(financial_records) == 2
            assert len(accounts) >= 4
            assert len(account_values) >= 6
            
        finally:
            os.unlink(temp_file)
    
    def test_parser_state_reset(self):
        """Test that parser state is properly reset between parse operations."""
        # First parse
        self.parser.parse_data(self.sample_data)
        first_accounts_count = len(self.parser.accounts)
        first_values_count = len(self.parser.account_values)
        
        # Second parse with different data
        smaller_data = {
            "data": {
                "Header": {"Currency": "EUR"},
                "Columns": {
                    "Column": [
                        {"ColTitle": "", "ColType": "Account"},
                        {
                            "ColTitle": "Jan 2021",
                            "ColType": "Money",
                            "MetaData": [
                                {"Name": "StartDate", "Value": "2021-01-01"},
                                {"Name": "EndDate", "Value": "2021-01-31"}
                            ]
                        }
                    ]
                },
                "Rows": {
                    "Row": [
                        {
                            "Header": {
                                "ColData": [
                                    {"value": "Single Account", "id": "1"},
                                    {"value": "100.00"}
                                ]
                            }
                        }
                    ]
                }
            }
        }
        
        financial_records, accounts, account_values = self.parser.parse_data(smaller_data)
        
        # Should have fewer accounts/values than first parse
        assert len(accounts) < first_accounts_count
        assert len(account_values) < first_values_count
        assert self.parser.currency == "EUR"  # Should be updated