"""
Performance tests for concurrent user simulation and system load testing.

Tests system performance under various load conditions and concurrent usage patterns.
"""

import asyncio
import concurrent.futures
import statistics
import time
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.database.connection import create_tables, get_db_session, get_engine
from app.database.models import AccountDB, AccountValueDB, FinancialRecordDB
from app.main import app
from app.models.financial import AccountType, SourceType


@pytest.fixture(scope="function")
def setup_performance_database():
    """Set up database with larger dataset for performance testing."""
    engine = get_engine()
    from app.database.models import Base
    
    # Clean and create tables
    Base.metadata.drop_all(bind=engine)
    create_tables(engine)
    
    # Insert larger dataset for performance testing
    with get_db_session() as session:
        # Create financial records for multiple years and months
        records = []
        accounts = []
        account_values = []
        
        # Generate 2 years of monthly data (24 records per source)
        for year in [2023, 2024]:
            for month in range(1, 13):
                # Calculate period dates
                if month == 12:
                    period_start = date(year, month, 1)
                    period_end = date(year + 1, 1, 1)
                else:
                    period_start = date(year, month, 1)
                    period_end = date(year, month + 1, 1)
                
                # Generate varying financial data
                base_revenue = 100000 + (month * 5000) + (year - 2023) * 50000
                base_expenses = base_revenue * 0.8
                
                # QuickBooks record
                qb_record = FinancialRecordDB(
                    id=f"qb_{year}_{month:02d}",
                    source=SourceType.QUICKBOOKS.value,
                    period_start=period_start,
                    period_end=period_end,
                    currency="USD",
                    revenue=Decimal(str(base_revenue)),
                    expenses=Decimal(str(base_expenses)),
                    net_profit=Decimal(str(base_revenue - base_expenses)),
                    raw_data=f'{{"year": {year}, "month": {month}, "source": "quickbooks"}}'
                )
                records.append(qb_record)
                
                # Rootfi record (slightly different values)
                rf_revenue = base_revenue * 0.95
                rf_expenses = rf_revenue * 0.82
                rf_record = FinancialRecordDB(
                    id=f"rf_{year}_{month:02d}",
                    source=SourceType.ROOTFI.value,
                    period_start=period_start,
                    period_end=period_end,
                    currency="USD",
                    revenue=Decimal(str(rf_revenue)),
                    expenses=Decimal(str(rf_expenses)),
                    net_profit=Decimal(str(rf_revenue - rf_expenses)),
                    raw_data=f'{{"year": {year}, "month": {month}, "source": "rootfi"}}'
                )
                records.append(rf_record)
        
        # Create accounts (once)
        account_types = [
            ("revenue_product", "Product Revenue", AccountType.REVENUE),
            ("revenue_service", "Service Revenue", AccountType.REVENUE),
            ("revenue_other", "Other Revenue", AccountType.REVENUE),
            ("expense_operations", "Operating Expenses", AccountType.EXPENSE),
            ("expense_marketing", "Marketing Expenses", AccountType.EXPENSE),
            ("expense_payroll", "Payroll Expenses", AccountType.EXPENSE),
            ("expense_rent", "Rent Expenses", AccountType.EXPENSE),
            ("expense_utilities", "Utilities", AccountType.EXPENSE),
        ]
        
        for source in [SourceType.QUICKBOOKS, SourceType.ROOTFI]:
            for account_id, name, account_type in account_types:
                account = AccountDB(
                    account_id=f"{source.value}_{account_id}",
                    name=f"{name} ({source.value})",
                    account_type=account_type.value,
                    source=source.value,
                    description=f"{name} from {source.value}"
                )
                accounts.append(account)
        
        # Create account values for each record
        for record in records:
            source_prefix = record.source
            
            # Distribute revenue across revenue accounts
            revenue_accounts = [
                f"{source_prefix}_revenue_product",
                f"{source_prefix}_revenue_service", 
                f"{source_prefix}_revenue_other"
            ]
            revenue_distribution = [0.6, 0.3, 0.1]
            
            for i, account_id in enumerate(revenue_accounts):
                value = record.revenue * Decimal(str(revenue_distribution[i]))
                account_values.append(AccountValueDB(
                    account_id=account_id,
                    financial_record_id=record.id,
                    value=value
                ))
            
            # Distribute expenses across expense accounts
            expense_accounts = [
                f"{source_prefix}_expense_operations",
                f"{source_prefix}_expense_marketing",
                f"{source_prefix}_expense_payroll",
                f"{source_prefix}_expense_rent",
                f"{source_prefix}_expense_utilities"
            ]
            expense_distribution = [0.4, 0.2, 0.25, 0.1, 0.05]
            
            for i, account_id in enumerate(expense_accounts):
                value = record.expenses * Decimal(str(expense_distribution[i]))
                account_values.append(AccountValueDB(
                    account_id=account_id,
                    financial_record_id=record.id,
                    value=value
                ))
        
        # Bulk insert all data
        session.add_all(records)
        session.add_all(accounts)
        session.add_all(account_values)
        session.commit()
        
        print(f"Created {len(records)} financial records, {len(accounts)} accounts, {len(account_values)} account values")
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client for performance testing."""
    return TestClient(app)


class PerformanceMetrics:
    """Helper class to collect and analyze performance metrics."""
    
    def __init__(self):
        self.response_times = []
        self.success_count = 0
        self.error_count = 0
        self.status_codes = {}
    
    def record_response(self, response_time, status_code):
        """Record a response for metrics."""
        self.response_times.append(response_time)
        
        if 200 <= status_code < 300:
            self.success_count += 1
        else:
            self.error_count += 1
        
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
    
    def get_summary(self):
        """Get performance summary statistics."""
        if not self.response_times:
            return {"error": "No response times recorded"}
        
        return {
            "total_requests": len(self.response_times),
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_count / len(self.response_times) * 100,
            "avg_response_time": statistics.mean(self.response_times),
            "median_response_time": statistics.median(self.response_times),
            "min_response_time": min(self.response_times),
            "max_response_time": max(self.response_times),
            "p95_response_time": self._percentile(self.response_times, 95),
            "p99_response_time": self._percentile(self.response_times, 99),
            "status_codes": self.status_codes
        }
    
    def _percentile(self, data, percentile):
        """Calculate percentile of data."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


class TestFinancialDataPerformance:
    """Performance tests for financial data endpoints."""
    
    def test_financial_data_single_user_performance(self, client, setup_performance_database):
        """Test financial data endpoint performance for single user."""
        metrics = PerformanceMetrics()
        
        # Test various endpoint calls
        endpoints = [
            "/api/v1/financial-data",
            "/api/v1/financial-data?source=quickbooks",
            "/api/v1/financial-data?start_date=2024-01-01&end_date=2024-12-31",
            "/api/v1/financial-data?limit=10&offset=0",
            "/api/v1/accounts",
            "/api/v1/accounts?account_type=revenue"
        ]
        
        # Make multiple requests to each endpoint
        for endpoint in endpoints:
            for _ in range(10):  # 10 requests per endpoint
                start_time = time.time()
                response = client.get(endpoint)
                end_time = time.time()
                
                response_time = end_time - start_time
                metrics.record_response(response_time, response.status_code)
        
        summary = metrics.get_summary()
        
        # Performance assertions
        assert summary["success_rate"] >= 95.0, f"Success rate too low: {summary['success_rate']}%"
        assert summary["avg_response_time"] < 1.0, f"Average response time too high: {summary['avg_response_time']}s"
        assert summary["p95_response_time"] < 2.0, f"95th percentile too high: {summary['p95_response_time']}s"
        assert summary["max_response_time"] < 5.0, f"Max response time too high: {summary['max_response_time']}s"
        
        print(f"Single user performance summary: {summary}")
    
    def test_financial_data_concurrent_users(self, client, setup_performance_database):
        """Test financial data endpoint with concurrent users."""
        metrics = PerformanceMetrics()
        
        def make_request(endpoint):
            """Make a single request and return timing info."""
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            return end_time - start_time, response.status_code
        
        # Test with 20 concurrent users
        endpoints = [
            "/api/v1/financial-data",
            "/api/v1/financial-data?source=quickbooks",
            "/api/v1/financial-data?source=rootfi",
            "/api/v1/accounts",
            "/api/v1/financial-data?start_date=2024-01-01&end_date=2024-06-30"
        ]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Submit 100 requests (20 concurrent users, 5 requests each)
            futures = []
            for _ in range(20):  # 20 users
                for endpoint in endpoints:  # 5 requests per user
                    future = executor.submit(make_request, endpoint)
                    futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                response_time, status_code = future.result()
                metrics.record_response(response_time, status_code)
        
        summary = metrics.get_summary()
        
        # Concurrent performance assertions (more lenient than single user)
        assert summary["success_rate"] >= 90.0, f"Concurrent success rate too low: {summary['success_rate']}%"
        assert summary["avg_response_time"] < 2.0, f"Concurrent avg response time too high: {summary['avg_response_time']}s"
        assert summary["p95_response_time"] < 5.0, f"Concurrent 95th percentile too high: {summary['p95_response_time']}s"
        
        print(f"Concurrent users performance summary: {summary}")
    
    def test_large_dataset_pagination_performance(self, client, setup_performance_database):
        """Test pagination performance with large datasets."""
        metrics = PerformanceMetrics()
        
        # Test pagination through large dataset
        page_size = 50
        max_pages = 10
        
        for page in range(max_pages):
            offset = page * page_size
            endpoint = f"/api/v1/financial-data?limit={page_size}&offset={offset}"
            
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = end_time - start_time
            metrics.record_response(response_time, response.status_code)
            
            # Verify we got data
            if response.status_code == 200:
                data = response.json()
                assert "records" in data
                # Later pages might have fewer records
                assert len(data["records"]) <= page_size
        
        summary = metrics.get_summary()
        
        # Pagination should maintain consistent performance
        assert summary["success_rate"] == 100.0, "Pagination should not fail"
        assert summary["max_response_time"] < 3.0, f"Pagination max time too high: {summary['max_response_time']}s"
        
        # Response times should be relatively consistent
        time_variance = max(metrics.response_times) - min(metrics.response_times)
        assert time_variance < 2.0, f"Pagination response time variance too high: {time_variance}s"
        
        print(f"Pagination performance summary: {summary}")


class TestQueryPerformance:
    """Performance tests for natural language query endpoint."""
    
    @patch('app.ai.agent.get_financial_agent')
    def test_query_single_user_performance(self, mock_get_agent, client, setup_performance_database):
        """Test query endpoint performance for single user."""
        # Mock agent with realistic response times
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        
        def mock_process_query(query, **kwargs):
            # Simulate realistic processing time
            time.sleep(0.1 + len(query) * 0.001)  # Base time + complexity
            return {
                "response": f"Analysis complete for: {query[:50]}...",
                "conversation_id": f"conv_{hash(query)}",
                "tool_calls_made": [
                    {
                        "tool": "get_revenue_by_period",
                        "arguments": {"start_date": "2024-01-01", "end_date": "2024-12-31"},
                        "success": True
                    }
                ],
                "data_used": {
                    "tools_used": ["get_revenue_by_period"],
                    "date_ranges_analyzed": ["2024-01-01 to 2024-12-31"],
                    "metrics_analyzed": ["revenue"],
                    "sources_accessed": ["quickbooks"]
                },
                "iterations": 1
            }
        
        mock_agent.process_query.side_effect = mock_process_query
        mock_get_agent.return_value = mock_agent
        
        metrics = PerformanceMetrics()
        
        # Test various query types
        queries = [
            "What was the total revenue in 2024?",
            "Compare Q1 and Q2 2024 performance",
            "Show me expense trends for the last 6 months",
            "What are the top revenue sources?",
            "Analyze profit margins by quarter",
            "How did marketing expenses change over time?",
            "What was the growth rate in 2024?",
            "Compare QuickBooks and Rootfi data for Q1",
            "Show seasonal patterns in revenue",
            "What were the biggest expense categories?"
        ]
        
        # Make multiple requests with different queries
        for query in queries:
            for _ in range(3):  # 3 requests per query type
                query_data = {"query": query, "max_iterations": 5}
                
                start_time = time.time()
                response = client.post("/api/v1/query", json=query_data)
                end_time = time.time()
                
                response_time = end_time - start_time
                metrics.record_response(response_time, response.status_code)
        
        summary = metrics.get_summary()
        
        # Query performance assertions
        assert summary["success_rate"] >= 95.0, f"Query success rate too low: {summary['success_rate']}%"
        assert summary["avg_response_time"] < 3.0, f"Query avg response time too high: {summary['avg_response_time']}s"
        assert summary["p95_response_time"] < 5.0, f"Query 95th percentile too high: {summary['p95_response_time']}s"
        
        print(f"Query single user performance summary: {summary}")
    
    @patch('app.ai.agent.get_financial_agent')
    def test_query_concurrent_users(self, mock_get_agent, client, setup_performance_database):
        """Test query endpoint with concurrent users."""
        # Mock agent for concurrent testing
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        
        def mock_process_query(query, **kwargs):
            # Simulate processing with some variation
            import random
            time.sleep(0.05 + random.uniform(0, 0.1))
            return {
                "response": f"Concurrent analysis: {query[:30]}...",
                "conversation_id": f"conv_{hash(query)}_{time.time()}",
                "tool_calls_made": [],
                "data_used": {"tools_used": [], "date_ranges_analyzed": [], "metrics_analyzed": [], "sources_accessed": []},
                "iterations": 1
            }
        
        mock_agent.process_query.side_effect = mock_process_query
        mock_get_agent.return_value = mock_agent
        
        metrics = PerformanceMetrics()
        
        def make_query_request(query_id):
            """Make a query request."""
            query_data = {"query": f"What was the revenue for analysis {query_id}?"}
            
            start_time = time.time()
            response = client.post("/api/v1/query", json=query_data)
            end_time = time.time()
            
            return end_time - start_time, response.status_code
        
        # Test with 10 concurrent users making 5 requests each
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for user_id in range(10):
                for request_id in range(5):
                    query_id = f"user_{user_id}_req_{request_id}"
                    future = executor.submit(make_query_request, query_id)
                    futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                response_time, status_code = future.result()
                metrics.record_response(response_time, status_code)
        
        summary = metrics.get_summary()
        
        # Concurrent query performance assertions
        assert summary["success_rate"] >= 85.0, f"Concurrent query success rate too low: {summary['success_rate']}%"
        assert summary["avg_response_time"] < 5.0, f"Concurrent query avg time too high: {summary['avg_response_time']}s"
        assert summary["p95_response_time"] < 10.0, f"Concurrent query 95th percentile too high: {summary['p95_response_time']}s"
        
        print(f"Query concurrent users performance summary: {summary}")


class TestSystemLoadPerformance:
    """System-wide load testing."""
    
    @patch('app.ai.agent.get_financial_agent')
    def test_mixed_workload_performance(self, mock_get_agent, client, setup_performance_database):
        """Test system performance with mixed API and query workload."""
        # Mock agent
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        mock_agent.process_query.return_value = {
            "response": "Mixed workload analysis complete",
            "conversation_id": "mixed_conv",
            "tool_calls_made": [],
            "data_used": {"tools_used": [], "date_ranges_analyzed": [], "metrics_analyzed": [], "sources_accessed": []},
            "iterations": 1
        }
        mock_get_agent.return_value = mock_agent
        
        metrics = PerformanceMetrics()
        
        def make_api_request():
            """Make a financial data API request."""
            endpoints = [
                "/api/v1/financial-data",
                "/api/v1/financial-data?source=quickbooks",
                "/api/v1/accounts",
                "/api/v1/health"
            ]
            import random
            endpoint = random.choice(endpoints)
            
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            return end_time - start_time, response.status_code, "api"
        
        def make_query_request():
            """Make a query request."""
            queries = [
                "What was the revenue?",
                "Show expense trends",
                "Compare performance",
                "Analyze growth"
            ]
            import random
            query = random.choice(queries)
            query_data = {"query": query}
            
            start_time = time.time()
            response = client.post("/api/v1/query", json=query_data)
            end_time = time.time()
            
            return end_time - start_time, response.status_code, "query"
        
        # Mixed workload: 70% API requests, 30% queries
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = []
            
            # Submit mixed requests
            for _ in range(70):  # API requests
                future = executor.submit(make_api_request)
                futures.append(future)
            
            for _ in range(30):  # Query requests
                future = executor.submit(make_query_request)
                futures.append(future)
            
            # Collect results
            api_metrics = PerformanceMetrics()
            query_metrics = PerformanceMetrics()
            
            for future in concurrent.futures.as_completed(futures):
                response_time, status_code, request_type = future.result()
                
                if request_type == "api":
                    api_metrics.record_response(response_time, status_code)
                else:
                    query_metrics.record_response(response_time, status_code)
                
                metrics.record_response(response_time, status_code)
        
        # Overall system performance
        overall_summary = metrics.get_summary()
        api_summary = api_metrics.get_summary()
        query_summary = query_metrics.get_summary()
        
        # System load assertions
        assert overall_summary["success_rate"] >= 85.0, f"System success rate too low: {overall_summary['success_rate']}%"
        assert api_summary["avg_response_time"] < 2.0, f"API avg response time too high under load: {api_summary['avg_response_time']}s"
        assert query_summary["avg_response_time"] < 8.0, f"Query avg response time too high under load: {query_summary['avg_response_time']}s"
        
        print(f"Mixed workload overall summary: {overall_summary}")
        print(f"API requests summary: {api_summary}")
        print(f"Query requests summary: {query_summary}")
    
    def test_database_connection_pool_performance(self, client, setup_performance_database):
        """Test database connection pool under load."""
        metrics = PerformanceMetrics()
        
        def make_db_intensive_request():
            """Make a database-intensive request."""
            # Request with complex filtering that requires database work
            endpoint = "/api/v1/financial-data?start_date=2023-01-01&end_date=2024-12-31&source=quickbooks"
            
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            return end_time - start_time, response.status_code
        
        # Test with many concurrent database requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(make_db_intensive_request) for _ in range(50)]
            
            for future in concurrent.futures.as_completed(futures):
                response_time, status_code = future.result()
                metrics.record_response(response_time, status_code)
        
        summary = metrics.get_summary()
        
        # Database pool performance assertions
        assert summary["success_rate"] >= 90.0, f"DB pool success rate too low: {summary['success_rate']}%"
        assert summary["avg_response_time"] < 3.0, f"DB pool avg response time too high: {summary['avg_response_time']}s"
        
        # No single request should take too long (connection pool working)
        assert summary["max_response_time"] < 10.0, f"DB pool max response time too high: {summary['max_response_time']}s"
        
        print(f"Database connection pool performance summary: {summary}")
    
    def test_memory_usage_under_load(self, client, setup_performance_database):
        """Test memory usage patterns under load."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Generate load
        def make_request():
            return client.get("/api/v1/financial-data?limit=100")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            
            # Wait for all requests to complete
            for future in concurrent.futures.as_completed(futures):
                response = future.result()
                assert response.status_code == 200
        
        # Check memory usage after load
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory usage: Initial={initial_memory:.1f}MB, Final={final_memory:.1f}MB, Increase={memory_increase:.1f}MB")
        
        # Memory increase should be reasonable (less than 100MB for this test)
        assert memory_increase < 100, f"Memory increase too high: {memory_increase:.1f}MB"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])