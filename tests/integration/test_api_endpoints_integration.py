"""
Integration tests for API endpoints with various input scenarios.

Tests all API endpoints with realistic data, error conditions, and edge cases.
"""

import json
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
def setup_test_database():
    """Set up test database with comprehensive financial data."""
    engine = get_engine()
    from app.database.models import Base
    
    # Clean and create tables
    Base.metadata.drop_all(bind=engine)
    create_tables(engine)
    
    # Insert comprehensive test data
    with get_db_session() as session:
        # Create financial records for multiple periods and sources
        records = [
            FinancialRecordDB(
                id="record_2024_q1_qb",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 3, 31),
                currency="USD",
                revenue=Decimal('300000.00'),
                expenses=Decimal('250000.00'),
                net_profit=Decimal('50000.00'),
                raw_data='{"source": "quickbooks", "period": "Q1"}'
            ),
            FinancialRecordDB(
                id="record_2024_q2_qb",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 4, 1),
                period_end=date(2024, 6, 30),
                currency="USD",
                revenue=Decimal('350000.00'),
                expenses=Decimal('280000.00'),
                net_profit=Decimal('70000.00'),
                raw_data='{"source": "quickbooks", "period": "Q2"}'
            ),
            FinancialRecordDB(
                id="record_2024_q1_rf",
                source=SourceType.ROOTFI.value,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 3, 31),
                currency="USD",
                revenue=Decimal('295000.00'),
                expenses=Decimal('245000.00'),
                net_profit=Decimal('50000.00'),
                raw_data='{"source": "rootfi", "period": "Q1"}'
            ),
            # Monthly records for detailed analysis
            FinancialRecordDB(
                id="record_2024_01",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                currency="USD",
                revenue=Decimal('95000.00'),
                expenses=Decimal('80000.00'),
                net_profit=Decimal('15000.00'),
                raw_data='{"source": "quickbooks", "period": "Jan"}'
            ),
            FinancialRecordDB(
                id="record_2024_02",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 2, 1),
                period_end=date(2024, 2, 29),
                currency="USD",
                revenue=Decimal('100000.00'),
                expenses=Decimal('85000.00'),
                net_profit=Decimal('15000.00'),
                raw_data='{"source": "quickbooks", "period": "Feb"}'
            ),
            FinancialRecordDB(
                id="record_2024_03",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 3, 1),
                period_end=date(2024, 3, 31),
                currency="USD",
                revenue=Decimal('105000.00'),
                expenses=Decimal('85000.00'),
                net_profit=Decimal('20000.00'),
                raw_data='{"source": "quickbooks", "period": "Mar"}'
            )
        ]
        
        for record in records:
            session.add(record)
        
        # Create accounts with detailed hierarchy
        accounts = [
            AccountDB(
                account_id="revenue_product_sales",
                name="Product Sales",
                account_type=AccountType.REVENUE.value,
                source=SourceType.QUICKBOOKS.value,
                description="Revenue from product sales"
            ),
            AccountDB(
                account_id="revenue_service_sales",
                name="Service Sales",
                account_type=AccountType.REVENUE.value,
                source=SourceType.QUICKBOOKS.value,
                description="Revenue from service sales"
            ),
            AccountDB(
                account_id="expense_operations",
                name="Operating Expenses",
                account_type=AccountType.EXPENSE.value,
                source=SourceType.QUICKBOOKS.value,
                description="General operating expenses"
            ),
            AccountDB(
                account_id="expense_marketing",
                name="Marketing Expenses",
                account_type=AccountType.EXPENSE.value,
                parent_account_id="expense_operations",
                source=SourceType.QUICKBOOKS.value,
                description="Marketing and advertising expenses"
            ),
            AccountDB(
                account_id="expense_payroll",
                name="Payroll Expenses",
                account_type=AccountType.EXPENSE.value,
                parent_account_id="expense_operations",
                source=SourceType.QUICKBOOKS.value,
                description="Employee payroll expenses"
            ),
            # Rootfi accounts
            AccountDB(
                account_id="rf_revenue_main",
                name="Main Revenue",
                account_type=AccountType.REVENUE.value,
                source=SourceType.ROOTFI.value,
                description="Primary revenue stream"
            ),
            AccountDB(
                account_id="rf_expense_main",
                name="Main Expenses",
                account_type=AccountType.EXPENSE.value,
                source=SourceType.ROOTFI.value,
                description="Primary expense categories"
            )
        ]
        
        for account in accounts:
            session.add(account)
        
        # Create account values
        account_values = [
            # Q1 QB values
            AccountValueDB(account_id="revenue_product_sales", financial_record_id="record_2024_q1_qb", value=Decimal('200000.00')),
            AccountValueDB(account_id="revenue_service_sales", financial_record_id="record_2024_q1_qb", value=Decimal('100000.00')),
            AccountValueDB(account_id="expense_operations", financial_record_id="record_2024_q1_qb", value=Decimal('250000.00')),
            AccountValueDB(account_id="expense_marketing", financial_record_id="record_2024_q1_qb", value=Decimal('75000.00')),
            AccountValueDB(account_id="expense_payroll", financial_record_id="record_2024_q1_qb", value=Decimal('125000.00')),
            
            # Q2 QB values
            AccountValueDB(account_id="revenue_product_sales", financial_record_id="record_2024_q2_qb", value=Decimal('230000.00')),
            AccountValueDB(account_id="revenue_service_sales", financial_record_id="record_2024_q2_qb", value=Decimal('120000.00')),
            AccountValueDB(account_id="expense_operations", financial_record_id="record_2024_q2_qb", value=Decimal('280000.00')),
            AccountValueDB(account_id="expense_marketing", financial_record_id="record_2024_q2_qb", value=Decimal('90000.00')),
            AccountValueDB(account_id="expense_payroll", financial_record_id="record_2024_q2_qb", value=Decimal('140000.00')),
            
            # Rootfi values
            AccountValueDB(account_id="rf_revenue_main", financial_record_id="record_2024_q1_rf", value=Decimal('295000.00')),
            AccountValueDB(account_id="rf_expense_main", financial_record_id="record_2024_q1_rf", value=Decimal('245000.00')),
            
            # Monthly values
            AccountValueDB(account_id="revenue_product_sales", financial_record_id="record_2024_01", value=Decimal('60000.00')),
            AccountValueDB(account_id="revenue_product_sales", financial_record_id="record_2024_02", value=Decimal('65000.00')),
            AccountValueDB(account_id="revenue_product_sales", financial_record_id="record_2024_03", value=Decimal('70000.00'))
        ]
        
        for account_value in account_values:
            session.add(account_value)
        
        session.commit()
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client for API endpoints."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health and monitoring endpoints."""
    
    def test_root_endpoint(self, client, setup_test_database):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "AI Financial Data System" in data["message"]
    
    def test_basic_health_endpoint(self, client, setup_test_database):
        """Test basic health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert data["service"] == "ai_financial_data_system"
    
    def test_detailed_health_endpoint(self, client, setup_test_database):
        """Test detailed health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "system_info" in data
        assert "timestamp" in data
        
        # Verify health checks
        checks = data["checks"]
        assert "database" in checks
        assert checks["database"]["status"] in ["healthy", "unhealthy"]


class TestFinancialDataEndpoints:
    """Test financial data API endpoints."""
    
    def test_get_financial_data_basic(self, client, setup_test_database):
        """Test basic financial data retrieval."""
        response = client.get("/api/v1/financial-data")
        assert response.status_code == 200
        data = response.json()
        
        assert "records" in data
        assert "pagination" in data
        assert "summary" in data
        
        records = data["records"]
        assert len(records) > 0
        
        # Verify record structure
        record = records[0]
        assert "id" in record
        assert "source" in record
        assert "period_start" in record
        assert "period_end" in record
        assert "currency" in record
        assert "revenue" in record
        assert "expenses" in record
        assert "net_profit" in record
    
    def test_get_financial_data_with_filters(self, client, setup_test_database):
        """Test financial data with various filters."""
        # Test source filter
        response = client.get("/api/v1/financial-data?source=quickbooks")
        assert response.status_code == 200
        data = response.json()
        
        records = data["records"]
        for record in records:
            assert record["source"] == "quickbooks"
        
        # Test date range filter
        response = client.get(
            "/api/v1/financial-data?start_date=2024-01-01&end_date=2024-03-31"
        )
        assert response.status_code == 200
        data = response.json()
        
        records = data["records"]
        for record in records:
            period_start = datetime.fromisoformat(record["period_start"]).date()
            period_end = datetime.fromisoformat(record["period_end"]).date()
            assert period_start >= date(2024, 1, 1)
            assert period_end <= date(2024, 3, 31)
        
        # Test pagination
        response = client.get("/api/v1/financial-data?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["records"]) <= 2
        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["offset"] == 0
    
    def test_get_financial_data_by_period(self, client, setup_test_database):
        """Test financial data retrieval for specific period."""
        response = client.get("/api/v1/financial-data/2024-Q1")
        assert response.status_code == 200
        data = response.json()
        
        assert "records" in data
        assert "period_summary" in data
        
        records = data["records"]
        assert len(records) > 0
        
        # Verify all records are within Q1 2024
        for record in records:
            period_start = datetime.fromisoformat(record["period_start"]).date()
            assert period_start >= date(2024, 1, 1)
            assert period_start <= date(2024, 3, 31)
    
    def test_get_accounts_basic(self, client, setup_test_database):
        """Test basic accounts retrieval."""
        response = client.get("/api/v1/accounts")
        assert response.status_code == 200
        data = response.json()
        
        assert "accounts" in data
        assert "summary" in data
        
        accounts = data["accounts"]
        assert len(accounts) > 0
        
        # Verify account structure
        account = accounts[0]
        assert "account_id" in account
        assert "name" in account
        assert "account_type" in account
        assert "source" in account
    
    def test_get_accounts_with_hierarchy(self, client, setup_test_database):
        """Test accounts retrieval with hierarchy."""
        response = client.get("/api/v1/accounts?include_hierarchy=true")
        assert response.status_code == 200
        data = response.json()
        
        accounts = data["accounts"]
        
        # Find parent and child accounts
        parent_account = next(
            (acc for acc in accounts if acc["account_id"] == "expense_operations"), None
        )
        child_account = next(
            (acc for acc in accounts if acc["account_id"] == "expense_marketing"), None
        )
        
        assert parent_account is not None
        assert child_account is not None
        assert child_account["parent_account_id"] == "expense_operations"
    
    def test_get_account_by_id(self, client, setup_test_database):
        """Test specific account retrieval."""
        response = client.get("/api/v1/accounts/revenue_product_sales")
        assert response.status_code == 200
        data = response.json()
        
        assert "account" in data
        assert "values" in data
        assert "summary" in data
        
        account = data["account"]
        assert account["account_id"] == "revenue_product_sales"
        assert account["name"] == "Product Sales"
        assert account["account_type"] == "revenue"
        
        # Verify account values are included
        values = data["values"]
        assert len(values) > 0
        
        value = values[0]
        assert "financial_record_id" in value
        assert "value" in value
        assert "period_start" in value
        assert "period_end" in value
    
    def test_financial_data_error_handling(self, client, setup_test_database):
        """Test error handling for financial data endpoints."""
        # Test invalid date format
        response = client.get("/api/v1/financial-data?start_date=invalid-date")
        assert response.status_code == 422
        
        # Test invalid source
        response = client.get("/api/v1/financial-data?source=invalid_source")
        assert response.status_code == 422
        
        # Test non-existent account
        response = client.get("/api/v1/accounts/non_existent_account")
        assert response.status_code == 404
        
        # Test invalid period format
        response = client.get("/api/v1/financial-data/invalid-period")
        assert response.status_code == 422


class TestQueryEndpoint:
    """Test natural language query endpoint."""
    
    @patch('app.ai.agent.get_financial_agent')
    def test_basic_query_processing(self, mock_get_agent, client, setup_test_database):
        """Test basic natural language query processing."""
        # Mock agent response
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        mock_agent.process_query.return_value = {
            "response": "Q1 2024 revenue was $300,000 from QuickBooks data.",
            "conversation_id": "test_conv_123",
            "tool_calls_made": [
                {
                    "tool": "get_revenue_by_period",
                    "arguments": {"start_date": "2024-01-01", "end_date": "2024-03-31"},
                    "success": True
                }
            ],
            "data_used": {
                "tools_used": ["get_revenue_by_period"],
                "date_ranges_analyzed": ["2024-01-01 to 2024-03-31"],
                "metrics_analyzed": ["revenue"],
                "sources_accessed": ["quickbooks"]
            },
            "iterations": 1
        }
        mock_get_agent.return_value = mock_agent
        
        # Test query
        query_data = {
            "query": "What was the total revenue in Q1 2024?",
            "max_iterations": 5,
            "include_raw_data": False
        }
        
        response = client.post("/api/v1/query", json=query_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "answer" in data
        assert "supporting_data" in data
        assert "conversation_id" in data
        assert "query_metadata" in data
        
        # Verify response content
        assert "300,000" in data["answer"]
        assert data["conversation_id"] == "test_conv_123"
        
        # Verify supporting data
        supporting_data = data["supporting_data"]
        assert "analysis_summary" in supporting_data
        assert "data_quality" in supporting_data
        assert "tools_used" in supporting_data
        
        # Verify query metadata
        metadata = data["query_metadata"]
        assert "query_id" in metadata
        assert "processing_time_seconds" in metadata
        assert "tools_used" in metadata
        assert metadata["tools_used"] == 1
    
    @patch('app.ai.agent.get_financial_agent')
    def test_query_with_conversation_context(self, mock_get_agent, client, setup_test_database):
        """Test query with conversation context."""
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        mock_agent.process_query.return_value = {
            "response": "Q2 2024 revenue was $350,000, showing a 16.7% increase from Q1.",
            "conversation_id": "existing_conv_456",
            "tool_calls_made": [],
            "data_used": {"tools_used": [], "date_ranges_analyzed": [], "metrics_analyzed": [], "sources_accessed": []},
            "iterations": 1
        }
        mock_get_agent.return_value = mock_agent
        
        query_data = {
            "query": "What about Q2?",
            "conversation_id": "existing_conv_456",
            "max_iterations": 5
        }
        
        response = client.post("/api/v1/query", json=query_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["conversation_id"] == "existing_conv_456"
        assert "Q2" in data["answer"]
        assert "16.7%" in data["answer"]
    
    @patch('app.ai.agent.get_financial_agent')
    def test_query_with_raw_data(self, mock_get_agent, client, setup_test_database):
        """Test query with raw data inclusion."""
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        mock_agent.process_query.return_value = {
            "response": "Analysis complete.",
            "conversation_id": "test_conv_789",
            "tool_calls_made": [
                {
                    "tool": "compare_financial_metrics",
                    "arguments": {"period1_start": "2024-01-01", "period1_end": "2024-03-31"},
                    "success": True,
                    "result": {"comparison": "data"}
                }
            ],
            "data_used": {"raw_analysis": "detailed_data"},
            "iterations": 1
        }
        mock_get_agent.return_value = mock_agent
        
        query_data = {
            "query": "Compare Q1 and Q2 performance",
            "include_raw_data": True
        }
        
        response = client.post("/api/v1/query", json=query_data)
        assert response.status_code == 200
        
        data = response.json()
        supporting_data = data["supporting_data"]
        
        # Verify raw data is included
        assert "raw_tool_calls" in supporting_data
        assert "raw_data_used" in supporting_data
        assert supporting_data["raw_data_used"]["raw_analysis"] == "detailed_data"
    
    def test_query_validation_errors(self, client, setup_test_database):
        """Test query validation errors."""
        # Test empty query
        response = client.post("/api/v1/query", json={"query": ""})
        assert response.status_code == 422
        
        # Test query too long
        long_query = "x" * 1001
        response = client.post("/api/v1/query", json={"query": long_query})
        assert response.status_code == 422
        
        # Test invalid max_iterations
        response = client.post("/api/v1/query", json={
            "query": "test query",
            "max_iterations": 0
        })
        assert response.status_code == 422
        
        response = client.post("/api/v1/query", json={
            "query": "test query", 
            "max_iterations": 15
        })
        assert response.status_code == 422
    
    @patch('app.ai.agent.get_financial_agent')
    def test_query_llm_not_configured(self, mock_get_agent, client, setup_test_database):
        """Test query when LLM is not configured."""
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": False}
        mock_get_agent.return_value = mock_agent
        
        query_data = {"query": "What was the revenue?"}
        
        response = client.post("/api/v1/query", json=query_data)
        assert response.status_code == 503
        
        data = response.json()
        assert data["detail"]["error"] == "service_unavailable"
        assert "fallback_response" in data["detail"]
    
    @patch('app.ai.agent.get_financial_agent')
    def test_query_processing_error(self, mock_get_agent, client, setup_test_database):
        """Test query processing errors."""
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        mock_agent.process_query.side_effect = Exception("Processing failed")
        mock_get_agent.return_value = mock_agent
        
        query_data = {"query": "What was the revenue?"}
        
        response = client.post("/api/v1/query", json=query_data)
        assert response.status_code == 500
        
        data = response.json()
        assert data["detail"]["error"] == "internal_error"
        assert "fallback_response" in data["detail"]


class TestIngestionEndpoints:
    """Test data ingestion endpoints."""
    
    @patch('app.services.ingestion.DataIngestionService')
    def test_trigger_ingestion(self, mock_service_class, client, setup_test_database):
        """Test triggering data ingestion."""
        # Mock ingestion service
        mock_service = Mock()
        mock_service.ingest_batch.return_value = Mock(
            batch_id="batch_123",
            status="completed",
            files_processed=2,
            files_successful=2,
            files_failed=0,
            total_records_processed=10,
            total_records_created=8,
            total_records_updated=2,
            processing_duration_seconds=5.5,
            file_results=[]
        )
        mock_service_class.return_value = mock_service
        
        ingestion_data = {
            "file_paths": ["/path/to/file1.json", "/path/to/file2.json"],
            "source_types": ["quickbooks", "rootfi"]
        }
        
        response = client.post("/api/v1/data/ingest", json=ingestion_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "batch_id" in data
        assert "status" in data
        assert data["batch_id"] == "batch_123"
        assert data["status"] == "completed"
    
    @patch('app.services.ingestion.DataIngestionService')
    def test_get_ingestion_status(self, mock_service_class, client, setup_test_database):
        """Test getting ingestion status."""
        mock_service = Mock()
        mock_service.get_ingestion_status.return_value = {
            "recent_ingestions": [
                {
                    "id": 1,
                    "source": "quickbooks",
                    "filename": "test.json",
                    "status": "completed",
                    "records_processed": 5,
                    "records_created": 5,
                    "started_at": "2024-01-01T10:00:00",
                    "completed_at": "2024-01-01T10:01:00"
                }
            ],
            "total_logs": 1
        }
        mock_service_class.return_value = mock_service
        
        response = client.get("/api/v1/data/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "recent_ingestions" in data
        assert "total_logs" in data
        assert data["total_logs"] == 1


class TestInsightsEndpoints:
    """Test AI insights endpoints."""
    
    @patch('app.ai.insights.get_insights_generator')
    def test_get_insights_for_period(self, mock_get_generator, client, setup_test_database):
        """Test getting AI insights for a specific period."""
        mock_generator = Mock()
        mock_generator.generate_period_insights.return_value = {
            "period": "2024-Q1",
            "insights": [
                {
                    "type": "revenue_trend",
                    "title": "Strong Revenue Growth",
                    "description": "Revenue increased by 15% compared to previous quarter",
                    "confidence": 0.9,
                    "supporting_data": {"growth_rate": 15.0}
                }
            ],
            "summary": "Q1 2024 showed strong performance with consistent growth.",
            "recommendations": [
                "Continue current growth strategies",
                "Monitor expense growth to maintain profitability"
            ]
        }
        mock_get_generator.return_value = mock_generator
        
        response = client.get("/api/v1/insights/2024-Q1")
        assert response.status_code == 200
        
        data = response.json()
        assert "period" in data
        assert "insights" in data
        assert "summary" in data
        assert "recommendations" in data
        
        insights = data["insights"]
        assert len(insights) > 0
        
        insight = insights[0]
        assert "type" in insight
        assert "title" in insight
        assert "description" in insight
        assert "confidence" in insight


class TestConcurrentRequests:
    """Test concurrent request handling."""
    
    def test_concurrent_financial_data_requests(self, client, setup_test_database):
        """Test handling multiple concurrent financial data requests."""
        import concurrent.futures
        import threading
        
        def make_request():
            return client.get("/api/v1/financial-data")
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "records" in data
            assert len(data["records"]) > 0
    
    @patch('app.ai.agent.get_financial_agent')
    def test_concurrent_query_requests(self, mock_get_agent, client, setup_test_database):
        """Test handling multiple concurrent query requests."""
        import concurrent.futures
        
        # Mock agent for concurrent testing
        mock_agent = Mock()
        mock_agent.get_agent_status.return_value = {"llm_configured": True}
        
        def mock_process_query(query, **kwargs):
            import time
            time.sleep(0.1)  # Simulate processing time
            return {
                "response": f"Processed: {query}",
                "conversation_id": f"conv_{hash(query)}",
                "tool_calls_made": [],
                "data_used": {"tools_used": [], "date_ranges_analyzed": [], "metrics_analyzed": [], "sources_accessed": []},
                "iterations": 1
            }
        
        mock_agent.process_query.side_effect = mock_process_query
        mock_get_agent.return_value = mock_agent
        
        def make_query_request(query_num):
            query_data = {"query": f"What was the revenue for query {query_num}?"}
            return client.post("/api/v1/query", json=query_data)
        
        # Make 5 concurrent query requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_query_request, i) for i in range(5)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "Processed:" in data["answer"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])