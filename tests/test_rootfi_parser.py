"""
Unit tests for Rootfi parser.

Tests the parsing functionality for Rootfi financial data JSON format including
hierarchical line items, account extraction, and error handling.
"""

import json
import pytest
import tempfile
import os
from datetime import date
from decimal import Decimal
from unittest.mock import patch, mock_open

from app.parsers.rootfi_parser import (
    RootfiParser, RootfiParseError, parse_rootfi_file
)
from app.models.financial import SourceType, AccountType


class TestRootfiParser:
    """Test cases for Rootfi parser functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = RootfiParser()
        
        # Sample Rootfi data structure
        self.sample_data = {
            "data": [
                {
                    "rootfi_id": 12345,
                    "rootfi_created_at": "2025-01-08T16:49:47.359Z",
                    "rootfi_updated_at": "2025-03-06T23:22:41.000Z",
                    "rootfi_company_id": 15151,
                    "platform_id": "2022-08-01_2022-08-31",
                    "currency_id": "USD",
                    "period_end": "2022-08-31",
                    "period_start": "2022-08-01",
                    "revenue": [
                        {
                            "name": "Business Revenue",
                            "value": 100000.00,
                            "line_items": [
                                {
                                    "name": "Professional Income",
                                    "value": 80000.00,
                                    "account_id": "ACC_001",
                                    "line_items": [
                                        {
                                            "name": "Technical Service",
                                            "value": 50000.00,
                                            "account_id": "ACC_001_1"
                                        },
                                        {
                                            "name": "Consulting",
                                            "value": 30000.00,
                                            "account_id": "ACC_001_2"
                                        }
                                    ]
                                },
                                {
                                    "name": "Other Revenue",
                                    "value": 20000.00,
                                    "account_id": "ACC_002"
                                }
                            ]
                        }
                    ],
                    "cost_of_goods_sold": [
                        {
                            "name": "Cost of Products Sold",
                            "value": 10000.00,
                            "line_items": [
                                {
                                    "name": "Materials",
                                    "value": 10000.00,
                                    "account_id": "ACC_COGS_001"
                                }
                            ]
                        }
                    ],
                    "gross_profit": 90000.00,
                    "operating_expenses": [
                        {
                            "name": "Business Expenses",
                            "value": 50000.00,
                            "line_items": [
                                {
                                    "name": "Salaries",
                                    "value": 30000.00,
                                    "account_id": "ACC_EXP_001"
                                },
                                {
                                    "name": "Office Rent",
                                    "value": 20000.00,
                                    "account_id": "ACC_EXP_002"
                                }
                            ]
                        }
                    ],
                    "operating_profit": 40000.00,
                    "non_operating_revenue": [
                        {
                            "name": "Interest Income",
                            "value": 5000.00,
                            "line_items": [
                                {
                                    "name": "Bank Interest",
                                    "value": 5000.00,
                                    "account_id": "ACC_NON_REV_001"
                                }
                            ]
                        }
                    ],
                    "non_operating_expenses": [
                        {
                            "name": "Interest Expense",
                            "value": 2000.00,
                            "line_items": [
                                {
                                    "name": "Loan Interest",
                                    "value": 2000.00,
                                    "account_id": "ACC_NON_EXP_001"
                                }
                            ]
                        }
                    ],
                    "net_profit": 43000.00
                },
                {
                    "rootfi_id": 12346,
                    "rootfi_created_at": "2025-01-08T16:49:47.359Z",
                    "rootfi_updated_at": "2025-03-06T23:22:41.000Z",
                    "rootfi_company_id": 15151,
                    "platform_id": "2022-09-01_2022-09-30",
                    "currency_id": "USD",
                    "period_end": "2022-09-30",
                    "period_start": "2022-09-01",
                    "revenue": [
                        {
                            "name": "Business Revenue",
                            "value": 120000.00,
                            "line_items": [
                                {
                                    "name": "Professional Income",
                                    "value": 120000.00,
                                    "account_id": "ACC_001"
                                }
                            ]
                        }
                    ],
                    "cost_of_goods_sold": [],
                    "gross_profit": 120000.00,
                    "operating_expenses": [
                        {
                            "name": "Business Expenses",
                            "value": 60000.00,
                            "line_items": [
                                {
                                    "name": "Salaries",
                                    "value": 35000.00,
                                    "account_id": "ACC_EXP_001"
                                },
                                {
                                    "name": "Office Rent",
                                    "value": 25000.00,
                                    "account_id": "ACC_EXP_002"
                                }
                            ]
                        }
                    ],
                    "operating_profit": 60000.00,
                    "non_operating_revenue": [],
                    "non_operating_expenses": [],
                    "net_profit": 60000.00
                }
            ]
        }
    
    def test_parse_period_record_complete(self):
        """Test parsing a complete period record."""
        record_data = self.sample_data["data"][0]
        financial_record = self.parser._parse_period_record(record_data)
        
        assert financial_record is not None
        assert financial_record.source == SourceType.ROOTFI
        assert financial_record.period_start == date(2022, 8, 1)
        assert financial_record.period_end == date(2022, 8, 31)
        assert financial_record.currency == "USD"
        assert financial_record.revenue == Decimal("105000.00")  # 100000 + 5000 (non-operating)
        assert financial_record.expenses == Decimal("62000.00")   # 10000 + 50000 + 2000
        assert financial_record.raw_data["rootfi_id"] == 12345
        assert financial_record.raw_data["platform_id"] == "2022-08-01_2022-08-31"
    
    def test_parse_period_record_missing_dates(self):
        """Test parsing record with missing period dates."""
        record_data = {
            "rootfi_id": 12345,
            "currency_id": "USD",
            # Missing period_start and period_end
            "revenue": [],
            "operating_expenses": []
        }
        
        financial_record = self.parser._parse_period_record(record_data)
        assert financial_record is None
    
    def test_parse_period_record_invalid_dates(self):
        """Test parsing record with invalid date format."""
        record_data = {
            "rootfi_id": 12345,
            "period_start": "invalid-date",
            "period_end": "2022-08-31",
            "currency_id": "USD",
            "revenue": [],
            "operating_expenses": []
        }
        
        financial_record = self.parser._parse_period_record(record_data)
        assert financial_record is None
    
    def test_parse_period_record_default_currency(self):
        """Test parsing record with missing currency defaults to USD."""
        record_data = {
            "rootfi_id": 12345,
            "period_start": "2022-08-01",
            "period_end": "2022-08-31",
            "currency_id": None,  # Null currency
            "revenue": [],
            "operating_expenses": []
        }
        
        financial_record = self.parser._parse_period_record(record_data)
        assert financial_record is not None
        assert financial_record.currency == "USD"
    
    def test_parse_line_items_revenue(self):
        """Test parsing revenue line items."""
        line_items = [
            {
                "name": "Service Revenue",
                "value": 50000.00,
                "account_id": "REV_001",
                "line_items": [
                    {
                        "name": "Consulting",
                        "value": 30000.00,
                        "account_id": "REV_001_1"
                    },
                    {
                        "name": "Support",
                        "value": 20000.00,
                        "account_id": "REV_001_2"
                    }
                ]
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.REVENUE, "test_record", "revenue"
        )
        
        assert total_value == Decimal("50000.00")
        
        # Check accounts were created
        assert "REV_001" in self.parser.accounts
        assert "REV_001_1" in self.parser.accounts
        assert "REV_001_2" in self.parser.accounts
        
        # Check account properties
        service_account = self.parser.accounts["REV_001"]
        assert service_account["name"] == "Service Revenue"
        assert service_account["account_type"] == AccountType.REVENUE
        assert service_account["source"] == SourceType.ROOTFI
        assert service_account["parent_account_id"] is None
        
        consulting_account = self.parser.accounts["REV_001_1"]
        assert consulting_account["name"] == "Consulting"
        assert consulting_account["parent_account_id"] == "REV_001"
        
        # Check account values were created
        revenue_values = [av for av in self.parser.account_values if av["account_id"] == "REV_001"]
        assert len(revenue_values) == 1
        assert revenue_values[0]["value"] == Decimal("50000.00")
    
    def test_parse_line_items_expenses(self):
        """Test parsing expense line items."""
        line_items = [
            {
                "name": "Operating Expenses",
                "value": 30000.00,
                "line_items": [
                    {
                        "name": "Salaries",
                        "value": 20000.00,
                        "account_id": "EXP_001"
                    },
                    {
                        "name": "Rent",
                        "value": 10000.00,
                        "account_id": "EXP_002"
                    }
                ]
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.EXPENSE, "test_record", "operating_expenses"
        )
        
        assert total_value == Decimal("30000.00")
        
        # Check accounts were created with correct types
        operating_account_id = self.parser._generate_account_id("Operating Expenses", "operating_expenses")
        assert operating_account_id in self.parser.accounts
        assert self.parser.accounts[operating_account_id]["account_type"] == AccountType.EXPENSE
        
        assert "EXP_001" in self.parser.accounts
        assert self.parser.accounts["EXP_001"]["account_type"] == AccountType.EXPENSE
    
    def test_parse_line_items_zero_values(self):
        """Test parsing line items with zero values."""
        line_items = [
            {
                "name": "Zero Revenue",
                "value": 0,
                "account_id": "ZERO_001"
            },
            {
                "name": "Positive Revenue",
                "value": 1000.00,
                "account_id": "POS_001"
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.REVENUE, "test_record", "revenue"
        )
        
        assert total_value == Decimal("1000.00")
        
        # Both accounts should be created
        assert "ZERO_001" in self.parser.accounts
        assert "POS_001" in self.parser.accounts
        
        # But only non-zero value should be stored
        zero_values = [av for av in self.parser.account_values if av["account_id"] == "ZERO_001"]
        pos_values = [av for av in self.parser.account_values if av["account_id"] == "POS_001"]
        
        assert len(zero_values) == 0  # Zero values not stored
        assert len(pos_values) == 1
        assert pos_values[0]["value"] == Decimal("1000.00")
    
    def test_parse_line_items_negative_values(self):
        """Test parsing line items with negative values."""
        line_items = [
            {
                "name": "Negative Adjustment",
                "value": -500.00,
                "account_id": "NEG_001"
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.EXPENSE, "test_record", "expenses"
        )
        
        assert total_value == Decimal("-500.00")  # Total preserves sign
        
        # Account value should be stored as absolute value
        neg_values = [av for av in self.parser.account_values if av["account_id"] == "NEG_001"]
        assert len(neg_values) == 1
        assert neg_values[0]["value"] == Decimal("500.00")  # Stored as positive
    
    def test_parse_line_items_invalid_values(self):
        """Test parsing line items with invalid values."""
        line_items = [
            {
                "name": "Invalid Value",
                "value": "not_a_number"
            },
            {
                "name": "Valid Value",
                "value": 1000.00,
                "account_id": "VALID_001"
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.REVENUE, "test_record", "revenue"
        )
        
        assert total_value == Decimal("1000.00")  # Only valid value counted
        
        # Only valid account should be created
        invalid_account_id = self.parser._generate_account_id("Invalid Value", "revenue")
        assert invalid_account_id not in self.parser.accounts
        assert "VALID_001" in self.parser.accounts
    
    def test_parse_line_items_empty_name(self):
        """Test parsing line items with empty names."""
        line_items = [
            {
                "name": "",  # Empty name
                "value": 1000.00,
                "account_id": "EMPTY_001"
            },
            {
                "name": "   ",  # Whitespace only
                "value": 2000.00,
                "account_id": "SPACE_001"
            },
            {
                "name": "Valid Name",
                "value": 3000.00,
                "account_id": "VALID_001"
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.REVENUE, "test_record", "revenue"
        )
        
        assert total_value == Decimal("3000.00")  # Only valid item counted
        
        # Only valid account should be created
        assert "EMPTY_001" not in self.parser.accounts
        assert "SPACE_001" not in self.parser.accounts
        assert "VALID_001" in self.parser.accounts
    
    def test_generate_account_id(self):
        """Test account ID generation."""
        # Test without parent
        account_id = self.parser._generate_account_id("Service Revenue", "revenue")
        assert account_id == "rootfi_revenue_service_revenue"
        
        # Test with parent
        account_id = self.parser._generate_account_id("Consulting", "revenue", "rootfi_revenue_service")
        assert account_id == "rootfi_revenue_service_consulting"
        
        # Test with special characters
        account_id = self.parser._generate_account_id("Office-Rent & Utilities", "expenses")
        assert account_id == "rootfi_expenses_office_rent_and_utilities"
        
        # Test with numbers and mixed case
        account_id = self.parser._generate_account_id("Account 123 Test", "revenue")
        assert account_id == "rootfi_revenue_account_123_test"
    
    def test_generate_record_id(self):
        """Test financial record ID generation."""
        start_date = date(2022, 8, 1)
        end_date = date(2022, 8, 31)
        
        # Without rootfi_id
        record_id = self.parser._generate_record_id(start_date, end_date)
        assert record_id == "rootfi_20220801_20220831"
        
        # With rootfi_id
        record_id = self.parser._generate_record_id(start_date, end_date, 12345)
        assert record_id == "rootfi_20220801_20220831_12345"
    
    def test_parse_data_complete(self):
        """Test complete data parsing workflow."""
        financial_records, accounts, account_values = self.parser.parse_data(self.sample_data)
        
        # Check financial records
        assert len(financial_records) == 2  # Two periods
        
        # Check first record
        record1 = financial_records[0]
        assert record1.source == SourceType.ROOTFI
        assert record1.period_start == date(2022, 8, 1)
        assert record1.period_end == date(2022, 8, 31)
        assert record1.currency == "USD"
        assert record1.revenue == Decimal("105000.00")  # 100000 + 5000
        assert record1.expenses == Decimal("62000.00")   # 10000 + 50000 + 2000
        
        # Check second record
        record2 = financial_records[1]
        assert record2.period_start == date(2022, 9, 1)
        assert record2.period_end == date(2022, 9, 30)
        assert record2.revenue == Decimal("120000.00")
        assert record2.expenses == Decimal("60000.00")
        
        # Check accounts were created
        assert len(accounts) > 0
        
        # Find specific accounts
        professional_accounts = [a for a in accounts if a.name == "Professional Income"]
        assert len(professional_accounts) == 1
        assert professional_accounts[0].account_type == AccountType.REVENUE
        assert professional_accounts[0].source == SourceType.ROOTFI
        
        salary_accounts = [a for a in accounts if a.name == "Salaries"]
        assert len(salary_accounts) == 1
        assert salary_accounts[0].account_type == AccountType.EXPENSE
        
        # Check account values
        assert len(account_values) > 0
        
        # Verify specific account values
        professional_values = [av for av in account_values if av.account_id == "ACC_001"]
        assert len(professional_values) == 2  # Two periods
    
    def test_parse_data_empty_data_array(self):
        """Test parsing with empty data array."""
        empty_data = {"data": []}
        
        financial_records, accounts, account_values = self.parser.parse_data(empty_data)
        
        assert len(financial_records) == 0
        assert len(accounts) == 0
        assert len(account_values) == 0
    
    def test_parse_data_missing_data_key(self):
        """Test parsing with missing data key returns empty results."""
        invalid_data = {"invalid": "structure"}
        
        financial_records, accounts, account_values = self.parser.parse_data(invalid_data)
        
        # Should return empty results when data key is missing
        assert len(financial_records) == 0
        assert len(accounts) == 0
        assert len(account_values) == 0
    
    def test_parse_data_non_array_data(self):
        """Test parsing with non-array data field."""
        invalid_data = {"data": "not_an_array"}
        
        with pytest.raises(RootfiParseError) as exc_info:
            self.parser.parse_data(invalid_data)
        
        assert "Expected 'data' to be an array" in str(exc_info.value)
    
    def test_parse_file_success(self):
        """Test successful file parsing."""
        # Create temporary file with sample data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name
        
        try:
            financial_records, accounts, account_values = self.parser.parse_file(temp_file)
            
            assert len(financial_records) == 2
            assert len(accounts) > 0
            assert len(account_values) > 0
            
        finally:
            os.unlink(temp_file)
    
    def test_parse_file_not_found(self):
        """Test parsing non-existent file."""
        with pytest.raises(RootfiParseError) as exc_info:
            self.parser.parse_file("non_existent_file.json")
        
        assert "Failed to load file" in str(exc_info.value)
    
    def test_parse_file_invalid_json(self):
        """Test parsing file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json content")
            temp_file = f.name
        
        try:
            with pytest.raises(RootfiParseError) as exc_info:
                self.parser.parse_file(temp_file)
            
            assert "Failed to load file" in str(exc_info.value)
            
        finally:
            os.unlink(temp_file)
    
    def test_convenience_function(self):
        """Test the convenience function for parsing Rootfi files."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.sample_data, f)
            temp_file = f.name
        
        try:
            financial_records, accounts, account_values = parse_rootfi_file(temp_file)
            
            assert len(financial_records) == 2
            assert len(accounts) > 0
            assert len(account_values) > 0
            
        finally:
            os.unlink(temp_file)
    
    def test_parser_state_reset(self):
        """Test that parser state is properly reset between parse operations."""
        # First parse
        self.parser.parse_data(self.sample_data)
        first_accounts_count = len(self.parser.accounts)
        first_values_count = len(self.parser.account_values)
        
        # Second parse with smaller data
        smaller_data = {
            "data": [
                {
                    "rootfi_id": 99999,
                    "period_start": "2023-01-01",
                    "period_end": "2023-01-31",
                    "currency_id": "EUR",
                    "revenue": [
                        {
                            "name": "Single Revenue",
                            "value": 1000.00,
                            "account_id": "SINGLE_REV"
                        }
                    ],
                    "operating_expenses": [],
                    "cost_of_goods_sold": [],
                    "non_operating_revenue": [],
                    "non_operating_expenses": []
                }
            ]
        }
        
        financial_records, accounts, account_values = self.parser.parse_data(smaller_data)
        
        # Should have fewer accounts/values than first parse
        assert len(accounts) < first_accounts_count
        assert len(account_values) < first_values_count
        assert self.parser.currency == "USD"  # Should be reset to default
        
        # Check the single record
        assert len(financial_records) == 1
        assert financial_records[0].currency == "EUR"
        assert financial_records[0].revenue == Decimal("1000.00")
        assert financial_records[0].expenses == Decimal("0.00")
    
    def test_parse_line_items_nested_hierarchy(self):
        """Test parsing deeply nested line item hierarchies."""
        line_items = [
            {
                "name": "Level 1",
                "value": 1000.00,
                "line_items": [
                    {
                        "name": "Level 2A",
                        "value": 600.00,
                        "account_id": "L2A",
                        "line_items": [
                            {
                                "name": "Level 3A",
                                "value": 300.00,
                                "account_id": "L3A"
                            },
                            {
                                "name": "Level 3B",
                                "value": 300.00,
                                "account_id": "L3B"
                            }
                        ]
                    },
                    {
                        "name": "Level 2B",
                        "value": 400.00,
                        "account_id": "L2B"
                    }
                ]
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.REVENUE, "test_record", "revenue"
        )
        
        assert total_value == Decimal("1000.00")
        
        # Check all accounts were created with proper hierarchy
        level1_id = self.parser._generate_account_id("Level 1", "revenue")
        assert level1_id in self.parser.accounts
        assert self.parser.accounts[level1_id]["parent_account_id"] is None
        
        assert "L2A" in self.parser.accounts
        assert self.parser.accounts["L2A"]["parent_account_id"] == level1_id
        
        assert "L3A" in self.parser.accounts
        assert self.parser.accounts["L3A"]["parent_account_id"] == "L2A"
        
        assert "L2B" in self.parser.accounts
        assert self.parser.accounts["L2B"]["parent_account_id"] == level1_id
    
    def test_parse_line_items_mixed_account_ids(self):
        """Test parsing line items with mixed presence of account IDs."""
        line_items = [
            {
                "name": "With Account ID",
                "value": 1000.00,
                "account_id": "EXPLICIT_001"
            },
            {
                "name": "Without Account ID",
                "value": 2000.00
                # No account_id provided
            }
        ]
        
        total_value = self.parser._parse_line_items(
            line_items, AccountType.REVENUE, "test_record", "revenue"
        )
        
        assert total_value == Decimal("3000.00")
        
        # Both accounts should be created
        assert "EXPLICIT_001" in self.parser.accounts
        
        generated_id = self.parser._generate_account_id("Without Account ID", "revenue")
        assert generated_id in self.parser.accounts
        
        # Check account properties
        explicit_account = self.parser.accounts["EXPLICIT_001"]
        assert explicit_account["name"] == "With Account ID"
        
        generated_account = self.parser.accounts[generated_id]
        assert generated_account["name"] == "Without Account ID"