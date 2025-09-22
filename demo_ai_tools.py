#!/usr/bin/env python3
"""
Demonstration script for AI financial analysis tools.

This script shows how to use the financial analysis tools that have been
implemented for the AI agent.
"""

import json
from datetime import date
from decimal import Decimal

from app.ai.tools import (
    get_revenue_by_period,
    compare_financial_metrics,
    calculate_growth_rate,
    detect_anomalies,
    get_available_tools,
    call_tool,
    ValidationError,
    DataNotFoundError,
    FinancialAnalysisError
)
from app.database.connection import get_db_session, create_tables, get_engine
from app.database.models import FinancialRecordDB
from app.models.financial import SourceType


def setup_demo_data():
    """Set up some demo financial data for testing the tools."""
    print("Setting up demo financial data...")
    
    # Create tables
    engine = get_engine()
    create_tables(engine)
    
    # Create sample financial records
    demo_records = [
        FinancialRecordDB(
            id="demo_q1_2024",
            source=SourceType.QUICKBOOKS.value,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 3, 31),
            currency="USD",
            revenue=Decimal('150000.00'),
            expenses=Decimal('120000.00'),
            net_profit=Decimal('30000.00'),
            raw_data='{"demo": "Q1 2024 data"}'
        ),
        FinancialRecordDB(
            id="demo_q2_2024",
            source=SourceType.ROOTFI.value,
            period_start=date(2024, 4, 1),
            period_end=date(2024, 6, 30),
            currency="USD",
            revenue=Decimal('180000.00'),
            expenses=Decimal('140000.00'),
            net_profit=Decimal('40000.00'),
            raw_data='{"demo": "Q2 2024 data"}'
        ),
        FinancialRecordDB(
            id="demo_q3_2024",
            source=SourceType.QUICKBOOKS.value,
            period_start=date(2024, 7, 1),
            period_end=date(2024, 9, 30),
            currency="USD",
            revenue=Decimal('165000.00'),
            expenses=Decimal('130000.00'),
            net_profit=Decimal('35000.00'),
            raw_data='{"demo": "Q3 2024 data"}'
        ),
        # Add an anomalous record
        FinancialRecordDB(
            id="demo_q4_2024",
            source=SourceType.QUICKBOOKS.value,
            period_start=date(2024, 10, 1),
            period_end=date(2024, 12, 31),
            currency="USD",
            revenue=Decimal('300000.00'),  # Anomalously high
            expenses=Decimal('135000.00'),
            net_profit=Decimal('165000.00'),
            raw_data='{"demo": "Q4 2024 data - holiday boost"}'
        )
    ]
    
    with get_db_session() as session:
        for record in demo_records:
            # Check if record already exists
            existing = session.query(FinancialRecordDB).filter_by(id=record.id).first()
            if not existing:
                session.add(record)
        session.commit()
    
    print("Demo data setup complete!")


def demo_get_revenue_by_period():
    """Demonstrate the get_revenue_by_period tool."""
    print("\n" + "="*60)
    print("DEMO: Get Revenue by Period")
    print("="*60)
    
    try:
        # Get revenue for Q1 2024
        result = get_revenue_by_period("2024-01-01", "2024-03-31")
        print(f"Q1 2024 Revenue Analysis:")
        print(f"  Total Revenue: ${result['total_revenue']:,.2f}")
        print(f"  Record Count: {result['record_count']}")
        print(f"  Source Breakdown:")
        for source, amount in result['source_breakdown'].items():
            print(f"    {source}: ${amount:,.2f}")
        
        # Get revenue for entire year with source filter
        result = get_revenue_by_period("2024-01-01", "2024-12-31", source="quickbooks")
        print(f"\n2024 QuickBooks Revenue:")
        print(f"  Total Revenue: ${result['total_revenue']:,.2f}")
        print(f"  Record Count: {result['record_count']}")
        
    except Exception as e:
        print(f"Error: {e}")


def demo_compare_financial_metrics():
    """Demonstrate the compare_financial_metrics tool."""
    print("\n" + "="*60)
    print("DEMO: Compare Financial Metrics")
    print("="*60)
    
    try:
        # Compare Q1 vs Q2 2024
        result = compare_financial_metrics(
            "2024-01-01", "2024-03-31",  # Q1
            "2024-04-01", "2024-06-30",  # Q2
            ["revenue", "expenses", "net_profit"]
        )
        
        print("Q1 vs Q2 2024 Comparison:")
        print(f"  Q1 Revenue: ${result['period1']['metrics']['revenue']:,.2f}")
        print(f"  Q2 Revenue: ${result['period2']['metrics']['revenue']:,.2f}")
        
        revenue_change = result['comparison']['revenue']['percentage_change']
        print(f"  Revenue Change: {revenue_change:+.1f}%")
        
        print(f"\nSummary: {result['summary']}")
        
    except Exception as e:
        print(f"Error: {e}")


def demo_calculate_growth_rate():
    """Demonstrate the calculate_growth_rate tool."""
    print("\n" + "="*60)
    print("DEMO: Calculate Growth Rate")
    print("="*60)
    
    try:
        # Calculate revenue growth across all quarters
        periods = [
            {"start": "2024-01-01", "end": "2024-03-31"},  # Q1
            {"start": "2024-04-01", "end": "2024-06-30"},  # Q2
            {"start": "2024-07-01", "end": "2024-09-30"},  # Q3
            {"start": "2024-10-01", "end": "2024-12-31"}   # Q4
        ]
        
        result = calculate_growth_rate("revenue", periods)
        
        print("Revenue Growth Analysis:")
        print(f"  Metric: {result['metric']}")
        print(f"  Average Growth Rate: {result['average_growth_rate']:.1f}%")
        print(f"  Trend Direction: {result['trend_direction']}")
        print(f"  Volatility: {result['volatility']:.1f}%")
        
        print("\nPeriod Values:")
        for period_data in result['period_values']:
            print(f"  {period_data['period']}: ${period_data['value']:,.2f}")
        
        print("\nGrowth Rates:")
        for growth_data in result['growth_rates']:
            print(f"  {growth_data['from_period']} → {growth_data['to_period']}: {growth_data['growth_rate']:+.1f}%")
        
        print(f"\nAnalysis: {result['analysis_summary']}")
        
    except Exception as e:
        print(f"Error: {e}")


def demo_detect_anomalies():
    """Demonstrate the detect_anomalies tool."""
    print("\n" + "="*60)
    print("DEMO: Detect Anomalies")
    print("="*60)
    
    try:
        # Detect revenue anomalies with a moderate threshold
        result = detect_anomalies("revenue", threshold=0.3, lookback_months=12)
        
        if result:
            print(f"Found {len(result)} anomalies:")
            for anomaly in result:
                print(f"\nAnomaly in {anomaly['period']}:")
                print(f"  Metric Value: ${anomaly['metric_value']:,.2f}")
                print(f"  Anomaly Type: {anomaly['anomaly_type']}")
                print(f"  Severity: {anomaly['severity']}")
                print(f"  Deviation: {anomaly['deviation_percentage']:.1f}%")
                print(f"  Description: {anomaly['description']}")
        else:
            print("No anomalies detected with current threshold.")
        
    except DataNotFoundError as e:
        print(f"Insufficient data for anomaly detection: {e}")
    except Exception as e:
        print(f"Error: {e}")


def demo_tool_registry():
    """Demonstrate the tool registry functionality."""
    print("\n" + "="*60)
    print("DEMO: Tool Registry")
    print("="*60)
    
    # Show available tools
    tools = get_available_tools()
    print("Available Financial Analysis Tools:")
    for i, tool in enumerate(tools, 1):
        print(f"  {i}. {tool}")
    
    # Demonstrate calling a tool by name
    print("\nCalling tool by name:")
    try:
        result = call_tool('get_revenue_by_period', 
                          start_date="2024-01-01", 
                          end_date="2024-03-31")
        print(f"  Tool result: Total revenue = ${result['total_revenue']:,.2f}")
    except Exception as e:
        print(f"  Error: {e}")


def demo_error_handling():
    """Demonstrate error handling in the tools."""
    print("\n" + "="*60)
    print("DEMO: Error Handling")
    print("="*60)
    
    # Test various error conditions
    error_tests = [
        ("Invalid date format", lambda: get_revenue_by_period("invalid-date", "2024-01-31")),
        ("Invalid date range", lambda: get_revenue_by_period("2024-01-31", "2024-01-01")),
        ("Invalid source", lambda: get_revenue_by_period("2024-01-01", "2024-01-31", source="invalid")),
        ("Invalid metric", lambda: compare_financial_metrics("2024-01-01", "2024-01-31", "2024-02-01", "2024-02-29", ["invalid_metric"])),
        ("Invalid tool name", lambda: call_tool("invalid_tool_name")),
    ]
    
    for test_name, test_func in error_tests:
        try:
            test_func()
            print(f"  {test_name}: No error (unexpected)")
        except ValidationError as e:
            print(f"  {test_name}: ValidationError - {e}")
        except DataNotFoundError as e:
            print(f"  {test_name}: DataNotFoundError - {e}")
        except FinancialAnalysisError as e:
            print(f"  {test_name}: FinancialAnalysisError - {e}")
        except Exception as e:
            print(f"  {test_name}: {type(e).__name__} - {e}")


def main():
    """Run all demonstrations."""
    print("AI Financial Analysis Tools Demonstration")
    print("=" * 60)
    
    # Set up demo data
    setup_demo_data()
    
    # Run demonstrations
    demo_get_revenue_by_period()
    demo_compare_financial_metrics()
    demo_calculate_growth_rate()
    demo_detect_anomalies()
    demo_tool_registry()
    demo_error_handling()
    
    print("\n" + "="*60)
    print("Demonstration Complete!")
    print("="*60)
    print("\nThese tools are now ready to be used by an AI agent for")
    print("financial data analysis and natural language query processing.")


if __name__ == "__main__":
    main()