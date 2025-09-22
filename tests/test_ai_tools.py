"""
Unit tests for AI financial analysis tools.

Tests all financial analysis tools with various scenarios including
error conditions, edge cases, and normal operations.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

from app.ai.tools import (
    get_revenue_by_period,
    compare_financial_metrics,
    calculate_growth_rate,
    detect_anomalies,
    FinancialAnalysisError,
    ValidationError,
    DataNotFoundError,
    get_available_tools,
    call_tool,
    _validate_date_string,
    _validate_date_range,
    _validate_source,
    _validate_account_type
)
from app.models.financial import SourceType, AccountType


class TestValidationFunctions:
    """Test validation helper functions."""
    
    def test_validate_date_string_valid(self):
        """Test valid date string parsing."""
        result = _validate_date_string("2024-01-15", "test_date")
        assert result == date(2024, 1, 15)
    
    def test_validate_date_string_invalid(self):
        """Test invalid date string parsing."""
        with pytest.raises(ValidationError, match="Invalid test_date format"):
            _validate_date_string("invalid-date", "test_date")
    
    def test_validate_date_range_valid(self):
        """Test valid date range."""
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        _validate_date_range(start, end)  # Should not raise
    
    def test_validate_date_range_invalid(self):
        """Test invalid date range."""
        start = date(2024, 1, 31)
        end = date(2024, 1, 1)
        with pytest.raises(ValidationError, match="End date .* must be after start date"):
            _validate_date_range(start, end)
    
    def test_validate_source_valid(self):
        """Test valid source validation."""
        result = _validate_source("quickbooks")
        assert result == SourceType.QUICKBOOKS
        
        result = _validate_source("ROOTFI")
        assert result == SourceType.ROOTFI
        
        result = _validate_source(None)
        assert result is None
    
    def test_validate_source_invalid(self):
        """Test invalid source validation."""
        with pytest.raises(ValidationError, match="Invalid source"):
            _validate_source("invalid_source")
    
    def test_validate_account_type_valid(self):
        """Test valid account type validation."""
        result = _validate_account_type("revenue")
        assert result == AccountType.REVENUE
        
        result = _validate_account_type(None)
        assert result is None
    
    def test_validate_account_type_invalid(self):
        """Test invalid account type validation."""
        with pytest.raises(ValidationError, match="Invalid account_type"):
            _validate_account_type("invalid_type")


class TestGetRevenueByPeriod:
    """Test get_revenue_by_period tool."""
    
    @patch('app.ai.revenue_tools.get_db_session')
    def test_get_revenue_by_period_success(self, mock_session):
        """Test successful revenue retrieval."""
        # Mock database records
        mock_record1 = Mock()
        mock_record1.revenue = Decimal('1000.00')
        mock_record1.source = 'quickbooks'
        
        mock_record2 = Mock()
        mock_record2.revenue = Decimal('1500.00')
        mock_record2.source = 'rootfi'
        
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = [
            mock_record1, mock_record2
        ]
        
        result = get_revenue_by_period("2024-01-01", "2024-01-31")
        
        assert result["total_revenue"] == 2500.0
        assert result["record_count"] == 2
        assert result["period_start"] == "2024-01-01"
        assert result["period_end"] == "2024-01-31"
        assert "quickbooks" in result["source_breakdown"]
        assert "rootfi" in result["source_breakdown"]
    
    def test_get_revenue_by_period_invalid_date(self):
        """Test invalid date format."""
        with pytest.raises(ValidationError, match="Invalid start_date format"):
            get_revenue_by_period("invalid-date", "2024-01-31")
    
    def test_get_revenue_by_period_invalid_date_range(self):
        """Test invalid date range."""
        with pytest.raises(ValidationError, match="End date .* must be after start date"):
            get_revenue_by_period("2024-01-31", "2024-01-01")
    
    @patch('app.ai.revenue_tools.get_db_session')
    def test_get_revenue_by_period_no_data(self, mock_session):
        """Test no data found scenario."""
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(DataNotFoundError, match="No financial records found"):
            get_revenue_by_period("2024-01-01", "2024-01-31")
    
    def test_get_revenue_by_period_invalid_source(self):
        """Test invalid source parameter."""
        with pytest.raises(ValidationError, match="Invalid source"):
            get_revenue_by_period("2024-01-01", "2024-01-31", source="invalid_source")


class TestCompareFinancialMetrics:
    """Test compare_financial_metrics tool."""
    
    @patch('app.ai.comparison_tools.get_db_session')
    def test_compare_financial_metrics_success(self, mock_session):
        """Test successful metrics comparison."""
        # Mock database records for period 1
        mock_record1 = Mock()
        mock_record1.revenue = Decimal('1000.00')
        mock_record1.expenses = Decimal('800.00')
        mock_record1.net_profit = Decimal('200.00')
        
        # Mock database records for period 2
        mock_record2 = Mock()
        mock_record2.revenue = Decimal('1200.00')
        mock_record2.expenses = Decimal('900.00')
        mock_record2.net_profit = Decimal('300.00')
        
        # Configure mock to return different results for different calls
        mock_query = mock_session.return_value.__enter__.return_value.query.return_value.filter
        mock_query.return_value.all.side_effect = [[mock_record1], [mock_record2]]
        
        result = compare_financial_metrics(
            "2024-01-01", "2024-01-31",
            "2024-02-01", "2024-02-29",
            ["revenue", "expenses", "net_profit"]
        )
        
        assert "period1" in result
        assert "period2" in result
        assert "comparison" in result
        assert "summary" in result
        
        # Check revenue comparison
        revenue_comp = result["comparison"]["revenue"]
        assert revenue_comp["period1_value"] == 1000.0
        assert revenue_comp["period2_value"] == 1200.0
        assert revenue_comp["absolute_change"] == 200.0
        assert revenue_comp["percentage_change"] == 20.0
    
    def test_compare_financial_metrics_invalid_metrics(self):
        """Test invalid metrics parameter."""
        with pytest.raises(ValidationError, match="Invalid metrics"):
            compare_financial_metrics(
                "2024-01-01", "2024-01-31",
                "2024-02-01", "2024-02-29",
                ["invalid_metric"]
            )
    
    @patch('app.ai.comparison_tools.get_db_session')
    def test_compare_financial_metrics_no_data(self, mock_session):
        """Test no data found scenario."""
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(DataNotFoundError, match="No financial records found for either period"):
            compare_financial_metrics(
                "2024-01-01", "2024-01-31",
                "2024-02-01", "2024-02-29",
                ["revenue"]
            )


class TestCalculateGrowthRate:
    """Test calculate_growth_rate tool."""
    
    @patch('app.ai.growth_tools.get_db_session')
    def test_calculate_growth_rate_success(self, mock_session):
        """Test successful growth rate calculation."""
        # Mock database records for different periods
        mock_records = [
            [Mock(revenue=Decimal('1000.00'))],  # Period 1
            [Mock(revenue=Decimal('1100.00'))],  # Period 2
            [Mock(revenue=Decimal('1200.00'))]   # Period 3
        ]
        
        mock_query = mock_session.return_value.__enter__.return_value.query.return_value.filter
        mock_query.return_value.all.side_effect = mock_records
        
        periods = [
            {"start": "2024-01-01", "end": "2024-01-31"},
            {"start": "2024-02-01", "end": "2024-02-29"},
            {"start": "2024-03-01", "end": "2024-03-31"}
        ]
        
        result = calculate_growth_rate("revenue", periods)
        
        assert result["metric"] == "revenue"
        assert len(result["period_values"]) == 3
        assert len(result["growth_rates"]) == 2
        assert "average_growth_rate" in result
        assert "trend_direction" in result
        assert "volatility" in result
        
        # Check growth rate calculations
        assert result["growth_rates"][0]["growth_rate"] == 10.0  # (1100-1000)/1000 * 100
        assert result["growth_rates"][1]["growth_rate"] == pytest.approx(9.09, rel=1e-2)  # (1200-1100)/1100 * 100
    
    def test_calculate_growth_rate_invalid_metric(self):
        """Test invalid metric parameter."""
        periods = [
            {"start": "2024-01-01", "end": "2024-01-31"},
            {"start": "2024-02-01", "end": "2024-02-29"}
        ]
        
        with pytest.raises(ValidationError, match="Invalid metric"):
            calculate_growth_rate("invalid_metric", periods)
    
    def test_calculate_growth_rate_insufficient_periods(self):
        """Test insufficient periods."""
        periods = [{"start": "2024-01-01", "end": "2024-01-31"}]
        
        with pytest.raises(ValidationError, match="At least 2 periods are required"):
            calculate_growth_rate("revenue", periods)
    
    def test_calculate_growth_rate_invalid_period_format(self):
        """Test invalid period format."""
        periods = [
            {"start": "2024-01-01"},  # Missing 'end'
            {"start": "2024-02-01", "end": "2024-02-29"}
        ]
        
        with pytest.raises(ValidationError, match="must be a dictionary with 'start' and 'end' keys"):
            calculate_growth_rate("revenue", periods)


class TestDetectAnomalies:
    """Test detect_anomalies tool."""
    
    @patch('app.ai.anomaly_tools.get_db_session')
    @patch('app.ai.anomaly_tools.datetime')
    def test_detect_anomalies_success(self, mock_datetime, mock_session):
        """Test successful anomaly detection."""
        # Mock current date
        mock_datetime.now.return_value.date.return_value = date(2024, 12, 31)
        
        # Mock database records with one anomaly
        mock_records = []
        for i in range(10):
            record = Mock()
            record.revenue = Decimal('1000.00') if i != 5 else Decimal('2000.00')  # Anomaly at index 5
            record.period_start = date(2024, i+1, 1)
            record.period_end = date(2024, i+1, 28)
            mock_records.append(record)
        
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_records
        
        result = detect_anomalies("revenue", threshold=0.2)
        
        assert isinstance(result, list)
        assert len(result) > 0  # Should detect the anomaly
        
        # Check anomaly structure
        anomaly = result[0]
        assert "period" in anomaly
        assert "metric_value" in anomaly
        assert "expected_range" in anomaly
        assert "deviation_percentage" in anomaly
        assert "anomaly_type" in anomaly
        assert "severity" in anomaly
    
    def test_detect_anomalies_invalid_metric(self):
        """Test invalid metric parameter."""
        with pytest.raises(ValidationError, match="Invalid metric"):
            detect_anomalies("invalid_metric")
    
    def test_detect_anomalies_invalid_threshold(self):
        """Test invalid threshold parameter."""
        with pytest.raises(ValidationError, match="Threshold must be between 0 and 1"):
            detect_anomalies("revenue", threshold=1.5)
    
    def test_detect_anomalies_invalid_lookback(self):
        """Test invalid lookback months parameter."""
        with pytest.raises(ValidationError, match="Lookback months must be at least 3"):
            detect_anomalies("revenue", lookback_months=2)
    
    @patch('app.ai.anomaly_tools.get_db_session')
    @patch('app.ai.anomaly_tools.datetime')
    def test_detect_anomalies_insufficient_data(self, mock_datetime, mock_session):
        """Test insufficient data scenario."""
        mock_datetime.now.return_value.date.return_value = date(2024, 12, 31)
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        with pytest.raises(DataNotFoundError, match="Insufficient data for anomaly detection"):
            detect_anomalies("revenue")


class TestToolRegistry:
    """Test tool registry functions."""
    
    def test_get_available_tools(self):
        """Test getting available tools."""
        tools = get_available_tools()
        
        expected_tools = [
            'get_revenue_by_period',
            'compare_financial_metrics',
            'calculate_growth_rate',
            'detect_anomalies'
        ]
        
        for tool in expected_tools:
            assert tool in tools
    
    @patch('app.ai.revenue_tools.get_db_session')
    def test_call_tool_success(self, mock_session):
        """Test successful tool calling."""
        # Mock for get_revenue_by_period
        mock_record = Mock()
        mock_record.revenue = Decimal('1000.00')
        mock_record.source = 'quickbooks'
        
        mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.all.return_value = [mock_record]
        
        result = call_tool('get_revenue_by_period', start_date="2024-01-01", end_date="2024-01-31")
        
        assert result["total_revenue"] == 1000.0
    
    def test_call_tool_invalid_name(self):
        """Test calling invalid tool name."""
        with pytest.raises(ValidationError, match="Unknown tool"):
            call_tool('invalid_tool_name')


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @patch('app.ai.revenue_tools.get_db_session')
    def test_database_error_handling(self, mock_session):
        """Test database error handling."""
        # Mock database exception
        mock_session.return_value.__enter__.side_effect = Exception("Database connection failed")
        
        with pytest.raises(FinancialAnalysisError, match="Failed to retrieve revenue data"):
            get_revenue_by_period("2024-01-01", "2024-01-31")
    
    @patch('app.ai.revenue_tools.get_db_session')
    def test_unexpected_error_handling(self, mock_session):
        """Test unexpected error handling."""
        # Mock unexpected exception during processing
        mock_session.return_value.__enter__.return_value.query.side_effect = RuntimeError("Unexpected error")
        
        with pytest.raises(FinancialAnalysisError):
            get_revenue_by_period("2024-01-01", "2024-01-31")


if __name__ == "__main__":
    pytest.main([__file__])