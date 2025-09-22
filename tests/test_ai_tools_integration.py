"""
Integration tests for AI financial analysis tools.

Tests the tools with real database data to ensure they work correctly
in a realistic environment.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from app.ai.tools import (
    get_revenue_by_period,
    compare_financial_metrics,
    calculate_growth_rate,
    detect_anomalies,
    DataNotFoundError,
    ValidationError
)
from app.database.connection import get_db_session, create_tables, get_engine
from app.database.models import FinancialRecordDB, AccountDB, AccountValueDB
from app.models.financial import SourceType, AccountType


@pytest.fixture(scope="function")
def setup_test_data():
    """Set up test data in the database."""
    # Create tables and clear existing data
    engine = get_engine()
    from app.database.models import Base
    Base.metadata.drop_all(bind=engine)
    create_tables(engine)
    
    # Insert test financial records
    with get_db_session() as session:
        # Create test records for different periods
        records = [
            FinancialRecordDB(
                id="test_record_1",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                currency="USD",
                revenue=Decimal('10000.00'),
                expenses=Decimal('8000.00'),
                net_profit=Decimal('2000.00'),
                raw_data='{"test": "data1"}'
            ),
            FinancialRecordDB(
                id="test_record_2",
                source=SourceType.ROOTFI.value,
                period_start=date(2024, 2, 1),
                period_end=date(2024, 2, 29),
                currency="USD",
                revenue=Decimal('12000.00'),
                expenses=Decimal('9000.00'),
                net_profit=Decimal('3000.00'),
                raw_data='{"test": "data2"}'
            ),
            FinancialRecordDB(
                id="test_record_3",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 3, 1),
                period_end=date(2024, 3, 31),
                currency="USD",
                revenue=Decimal('11000.00'),
                expenses=Decimal('8500.00'),
                net_profit=Decimal('2500.00'),
                raw_data='{"test": "data3"}'
            ),
            # Add an anomaly record
            FinancialRecordDB(
                id="test_record_4",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 4, 1),
                period_end=date(2024, 4, 30),
                currency="USD",
                revenue=Decimal('25000.00'),  # Anomalously high
                expenses=Decimal('8000.00'),
                net_profit=Decimal('17000.00'),
                raw_data='{"test": "data4"}'
            )
        ]
        
        for record in records:
            session.add(record)
        
        # Create test accounts
        accounts = [
            AccountDB(
                account_id="revenue_001",
                name="Sales Revenue",
                account_type=AccountType.REVENUE.value,
                source=SourceType.QUICKBOOKS.value,
                description="Primary sales revenue"
            ),
            AccountDB(
                account_id="expense_001",
                name="Operating Expenses",
                account_type=AccountType.EXPENSE.value,
                source=SourceType.QUICKBOOKS.value,
                description="General operating expenses"
            )
        ]
        
        for account in accounts:
            session.add(account)
        
        # Create account values
        account_values = [
            AccountValueDB(
                account_id="revenue_001",
                financial_record_id="test_record_1",
                value=Decimal('10000.00')
            ),
            AccountValueDB(
                account_id="expense_001",
                financial_record_id="test_record_1",
                value=Decimal('8000.00')
            ),
            AccountValueDB(
                account_id="revenue_001",
                financial_record_id="test_record_2",
                value=Decimal('12000.00')
            )
        ]
        
        for account_value in account_values:
            session.add(account_value)
        
        session.commit()
    
    yield
    
    # Cleanup - drop tables after test
    from app.database.models import Base
    Base.metadata.drop_all(bind=engine)


class TestGetRevenueByPeriodIntegration:
    """Integration tests for get_revenue_by_period."""
    
    def test_get_revenue_by_period_with_real_data(self, setup_test_data):
        """Test revenue retrieval with real database data."""
        result = get_revenue_by_period("2024-01-01", "2024-03-31")
        
        assert result["total_revenue"] == 33000.0  # 10000 + 12000 + 11000
        assert result["record_count"] == 3
        assert result["currency"] == "mixed"
        assert "quickbooks" in result["source_breakdown"]
        assert "rootfi" in result["source_breakdown"]
        assert result["source_breakdown"]["quickbooks"] == 21000.0  # 10000 + 11000
        assert result["source_breakdown"]["rootfi"] == 12000.0
    
    def test_get_revenue_by_period_with_source_filter(self, setup_test_data):
        """Test revenue retrieval with source filter."""
        result = get_revenue_by_period("2024-01-01", "2024-03-31", source="quickbooks")
        
        assert result["total_revenue"] == 21000.0  # Only QuickBooks records
        assert result["record_count"] == 2
        assert len(result["source_breakdown"]) == 1
        assert "quickbooks" in result["source_breakdown"]
    
    def test_get_revenue_by_period_with_account_breakdown(self, setup_test_data):
        """Test revenue retrieval with account breakdown."""
        result = get_revenue_by_period("2024-01-01", "2024-02-29", account_type="revenue")
        
        assert result["total_revenue"] == 22000.0  # 10000 + 12000
        assert "account_breakdown" in result
        assert "Sales Revenue" in result["account_breakdown"]
        assert result["account_breakdown"]["Sales Revenue"] == 22000.0
    
    def test_get_revenue_by_period_no_data_period(self, setup_test_data):
        """Test revenue retrieval for period with no data."""
        with pytest.raises(DataNotFoundError):
            get_revenue_by_period("2025-01-01", "2025-01-31")


class TestCompareFinancialMetricsIntegration:
    """Integration tests for compare_financial_metrics."""
    
    def test_compare_financial_metrics_with_real_data(self, setup_test_data):
        """Test financial metrics comparison with real data."""
        result = compare_financial_metrics(
            "2024-01-01", "2024-01-31",  # Period 1: Jan
            "2024-02-01", "2024-02-29",  # Period 2: Feb
            ["revenue", "expenses", "net_profit"]
        )
        
        assert result["period1"]["metrics"]["revenue"] == 10000.0
        assert result["period2"]["metrics"]["revenue"] == 12000.0
        
        # Check revenue comparison
        revenue_comp = result["comparison"]["revenue"]
        assert revenue_comp["absolute_change"] == 2000.0
        assert revenue_comp["percentage_change"] == 20.0
        
        # Check that summary is generated
        assert "summary" in result
        assert "increased" in result["summary"].lower()
    
    def test_compare_financial_metrics_multiple_periods(self, setup_test_data):
        """Test comparison with multiple records in periods."""
        result = compare_financial_metrics(
            "2024-01-01", "2024-02-29",  # Period 1: Jan-Feb (2 records)
            "2024-03-01", "2024-03-31",  # Period 2: Mar (1 record)
            ["revenue", "net_profit"]
        )
        
        assert result["period1"]["metrics"]["revenue"] == 22000.0  # 10000 + 12000
        assert result["period2"]["metrics"]["revenue"] == 11000.0
        
        # Revenue should decrease from period 1 to period 2
        revenue_comp = result["comparison"]["revenue"]
        assert revenue_comp["absolute_change"] == -11000.0
        assert revenue_comp["percentage_change"] == -50.0


class TestCalculateGrowthRateIntegration:
    """Integration tests for calculate_growth_rate."""
    
    def test_calculate_growth_rate_with_real_data(self, setup_test_data):
        """Test growth rate calculation with real data."""
        periods = [
            {"start": "2024-01-01", "end": "2024-01-31"},  # 10000
            {"start": "2024-02-01", "end": "2024-02-29"},  # 12000
            {"start": "2024-03-01", "end": "2024-03-31"}   # 11000
        ]
        
        result = calculate_growth_rate("revenue", periods)
        
        assert result["metric"] == "revenue"
        assert len(result["period_values"]) == 3
        assert len(result["growth_rates"]) == 2
        
        # Check period values
        assert result["period_values"][0]["value"] == 10000.0
        assert result["period_values"][1]["value"] == 12000.0
        assert result["period_values"][2]["value"] == 11000.0
        
        # Check growth rates
        assert result["growth_rates"][0]["growth_rate"] == 20.0  # (12000-10000)/10000 * 100
        assert result["growth_rates"][1]["growth_rate"] == pytest.approx(-8.33, rel=1e-2)  # (11000-12000)/12000 * 100
        
        # Check average growth rate
        expected_avg = (20.0 + (-8.33)) / 2
        assert result["average_growth_rate"] == pytest.approx(expected_avg, rel=1e-1)
    
    def test_calculate_growth_rate_expenses(self, setup_test_data):
        """Test growth rate calculation for expenses."""
        periods = [
            {"start": "2024-01-01", "end": "2024-01-31"},  # 8000
            {"start": "2024-02-01", "end": "2024-02-29"},  # 9000
            {"start": "2024-03-01", "end": "2024-03-31"}   # 8500
        ]
        
        result = calculate_growth_rate("expenses", periods)
        
        assert result["metric"] == "expenses"
        assert result["period_values"][0]["value"] == 8000.0
        assert result["period_values"][1]["value"] == 9000.0
        assert result["period_values"][2]["value"] == 8500.0


class TestDetectAnomaliesIntegration:
    """Integration tests for detect_anomalies."""
    
    def test_detect_anomalies_validation(self, setup_test_data):
        """Test anomaly detection input validation."""
        # Test invalid metric
        with pytest.raises(ValidationError, match="Invalid metric"):
            detect_anomalies("invalid_metric")
        
        # Test invalid threshold
        with pytest.raises(ValidationError, match="Threshold must be between 0 and 1"):
            detect_anomalies("revenue", threshold=1.5)
        
        # Test invalid lookback months
        with pytest.raises(ValidationError, match="Lookback months must be at least 3"):
            detect_anomalies("revenue", lookback_months=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])