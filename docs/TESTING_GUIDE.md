# Testing Guide

## Overview

The AI Financial Data System includes a comprehensive testing suite covering unit tests, integration tests, API tests, and end-to-end testing scenarios. This guide covers all aspects of testing the system.

## Table of Contents

1. [Test Structure](#test-structure)
2. [Running Tests](#running-tests)
3. [Unit Testing](#unit-testing)
4. [Integration Testing](#integration-testing)
5. [API Testing](#api-testing)
6. [AI Agent Testing](#ai-agent-testing)
7. [Performance Testing](#performance-testing)
8. [Test Data Management](#test-data-management)
9. [Continuous Integration](#continuous-integration)
10. [Test Coverage](#test-coverage)

## Test Structure

### Directory Organization

```
tests/
├── unit/                           # Unit tests
│   ├── test_parsers.py            # Parser unit tests
│   ├── test_validation.py         # Validation service tests
│   ├── test_normalization.py      # Normalization service tests
│   ├── test_ai_tools.py           # AI tools unit tests
│   └── test_models.py             # Data model tests
├── integration/                    # Integration tests
│   ├── test_end_to_end_ingestion.py
│   ├── test_ai_agent_integration.py
│   ├── test_data_quality_validation.py
│   ├── test_performance_concurrent.py
│   └── test_api_endpoints_integration.py
├── api/                           # API endpoint tests
│   ├── test_health_endpoints.py
│   ├── test_ingestion_endpoints.py
│   ├── test_financial_data_endpoints.py
│   ├── test_query_endpoints.py
│   └── test_insights_endpoints.py
├── fixtures/                      # Test data and fixtures
│   ├── sample_quickbooks_data.json
│   ├── sample_rootfi_data.json
│   └── test_database.py
├── conftest.py                    # Pytest configuration
└── README.md                      # Testing documentation
```

### Test Categories

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **API Tests**: Test REST API endpoints
4. **End-to-End Tests**: Test complete workflows
5. **Performance Tests**: Test system performance and scalability
6. **AI Tests**: Test AI agent and tool functionality

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Set test environment variables
export TEST_DATABASE_URL=sqlite:///./test_financial_data.db
export OPENAI_API_KEY=test_key_or_real_key_for_ai_tests
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_parsers.py

# Run specific test function
pytest tests/unit/test_parsers.py::test_quickbooks_parser_basic

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run tests in parallel
pytest -n auto
```

### Test Categories

```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run only API tests
pytest tests/api/

# Run tests by marker
pytest -m "not slow"
pytest -m "ai_tests"
pytest -m "database"
```

### Test Configuration

```python
# conftest.py
import pytest
import asyncio
from httpx import AsyncClient
from app.main import app
from app.database.connection import get_session, create_tables
from app.core.config import settings

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_app():
    """Create test application instance."""
    # Override settings for testing
    settings.DATABASE_URL = "sqlite:///./test_financial_data.db"
    settings.DEBUG = True
    
    # Create test database
    create_tables()
    
    yield app

@pytest.fixture
async def client(test_app):
    """Create test client."""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def test_session():
    """Create test database session."""
    session = get_session()
    try:
        yield session
    finally:
        session.close()
```

## Unit Testing

### Parser Testing

```python
# tests/unit/test_parsers.py
import pytest
from decimal import Decimal
from app.parsers.quickbooks_parser import QuickBooksParser
from app.parsers.rootfi_parser import RootfiParser

class TestQuickBooksParser:
    def setup_method(self):
        self.parser = QuickBooksParser()
    
    def test_parse_header_basic(self):
        """Test basic header parsing."""
        header_data = {
            "Currency": "USD",
            "ReportBasis": "Accrual"
        }
        
        result = self.parser._parse_header(header_data)
        
        assert result["currency"] == "USD"
        assert result["report_basis"] == "Accrual"
    
    def test_parse_columns_with_dates(self):
        """Test column parsing with date metadata."""
        columns_data = [
            {
                "ColTitle": "Jan 2024",
                "ColType": "Money",
                "MetaData": [
                    {"Name": "StartDate", "Value": "2024-01-01"},
                    {"Name": "EndDate", "Value": "2024-01-31"}
                ]
            }
        ]
        
        result = self.parser._parse_columns(columns_data)
        
        assert len(result) == 1
        assert result[0]["title"] == "Jan 2024"
        assert result[0]["start_date"] == "2024-01-01"
        assert result[0]["end_date"] == "2024-01-31"
    
    def test_classify_account_type(self):
        """Test account type classification."""
        test_cases = [
            ("Service Revenue", "revenue"),
            ("Office Expenses", "expense"),
            ("Cash Account", "asset"),
            ("Accounts Payable", "liability")
        ]
        
        for account_name, expected_type in test_cases:
            result = self.parser._classify_account_type(account_name)
            assert result == expected_type
    
    @pytest.mark.parametrize("value,expected", [
        ("1000.00", Decimal("1000.00")),
        ("", Decimal("0.00")),
        ("invalid", Decimal("0.00")),
        ("-500.50", Decimal("-500.50"))
    ])
    def test_parse_decimal_value(self, value, expected):
        """Test decimal value parsing with various inputs."""
        result = self.parser._parse_decimal_value(value)
        assert result == expected

class TestRootfiParser:
    def setup_method(self):
        self.parser = RootfiParser()
    
    def test_parse_period_record(self):
        """Test period record parsing."""
        period_data = {
            "period_start": "2024-01-01",
            "period_end": "2024-01-31",
            "currency_id": "USD",
            "revenue": [
                {
                    "name": "Professional Services",
                    "value": 25000.00
                }
            ]
        }
        
        result = self.parser._parse_period_record(period_data)
        
        assert result["period_start"] == "2024-01-01"
        assert result["period_end"] == "2024-01-31"
        assert result["currency"] == "USD"
        assert len(result["revenue_items"]) == 1
    
    def test_process_line_items_nested(self):
        """Test nested line item processing."""
        line_items = [
            {
                "name": "Professional Services",
                "value": 25000.00,
                "line_items": [
                    {
                        "name": "Consulting",
                        "value": 15000.00
                    },
                    {
                        "name": "Development",
                        "value": 10000.00
                    }
                ]
            }
        ]
        
        accounts, values = self.parser._process_line_items(
            line_items, "revenue", "test_record_id"
        )
        
        assert len(accounts) == 3  # Parent + 2 children
        assert len(values) == 3
        
        # Check parent account
        parent_account = next(a for a in accounts if a.name == "Professional Services")
        assert parent_account.account_type == "revenue"
        
        # Check child accounts
        child_accounts = [a for a in accounts if a.parent_account_id is not None]
        assert len(child_accounts) == 2
```

### Service Testing

```python
# tests/unit/test_validation.py
import pytest
from decimal import Decimal
from datetime import date
from app.services.validation import FinancialDataValidator, ValidationIssue
from app.models.financial import FinancialRecord, Account, AccountValue

class TestFinancialDataValidator:
    def setup_method(self):
        self.validator = FinancialDataValidator()
    
    def test_validate_financial_accuracy_negative_revenue(self):
        """Test validation of negative revenue."""
        record = FinancialRecord(
            id="test_record",
            source="quickbooks",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            currency="USD",
            revenue=Decimal("-1000.00"),  # Negative revenue
            expenses=Decimal("500.00"),
            net_profit=Decimal("-1500.00"),
            raw_data={}
        )
        
        issues = self.validator._validate_financial_accuracy([record])
        
        assert len(issues) == 1
        assert issues[0].severity == "WARNING"
        assert "negative revenue" in issues[0].message.lower()
    
    def test_validate_balance_equation(self):
        """Test balance equation validation."""
        record = FinancialRecord(
            id="test_record",
            source="quickbooks",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            currency="USD",
            revenue=Decimal("1000.00"),
            expenses=Decimal("600.00"),
            net_profit=Decimal("500.00"),  # Should be 400.00
            raw_data={}
        )
        
        issues = self.validator._validate_balance_equations([record])
        
        assert len(issues) == 1
        assert issues[0].severity == "ERROR"
        assert "balance equation" in issues[0].message.lower()
    
    def test_validate_date_consistency(self):
        """Test date consistency validation."""
        record = FinancialRecord(
            id="test_record",
            source="quickbooks",
            period_start=date(2024, 1, 31),  # End before start
            period_end=date(2024, 1, 1),
            currency="USD",
            revenue=Decimal("1000.00"),
            expenses=Decimal("600.00"),
            net_profit=Decimal("400.00"),
            raw_data={}
        )
        
        issues = self.validator._validate_date_consistency([record])
        
        assert len(issues) == 1
        assert issues[0].severity == "ERROR"
        assert "period end" in issues[0].message.lower()
    
    def test_calculate_quality_score(self):
        """Test quality score calculation."""
        issues = [
            ValidationIssue(severity="INFO", code="INFO_001", message="Info message"),
            ValidationIssue(severity="WARNING", code="WARN_001", message="Warning message"),
            ValidationIssue(severity="ERROR", code="ERR_001", message="Error message")
        ]
        
        score = self.validator._calculate_quality_score(issues)
        
        # Expected: 1.0 - 0.05 (INFO) - 0.15 (WARNING) - 0.35 (ERROR) = 0.45
        assert score == 0.45
    
    @pytest.mark.parametrize("currency,expected_valid", [
        ("USD", True),
        ("EUR", True),
        ("GBP", True),
        ("INVALID", False),
        ("US", False),
        ("", False)
    ])
    def test_validate_currency_codes(self, currency, expected_valid):
        """Test currency code validation."""
        record = FinancialRecord(
            id="test_record",
            source="quickbooks",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            currency=currency,
            revenue=Decimal("1000.00"),
            expenses=Decimal("600.00"),
            net_profit=Decimal("400.00"),
            raw_data={}
        )
        
        issues = self.validator._validate_currency_codes([record])
        
        if expected_valid:
            # Should have no ERROR issues for valid currencies
            error_issues = [i for i in issues if i.severity == "ERROR"]
            assert len(error_issues) == 0
        else:
            # Should have ERROR issues for invalid currencies
            error_issues = [i for i in issues if i.severity == "ERROR"]
            assert len(error_issues) > 0
```

### AI Tools Testing

```python
# tests/unit/test_ai_tools.py
import pytest
from unittest.mock import Mock, patch
from app.ai.tools.revenue_tools import get_revenue_by_period
from app.ai.tools.comparison_tools import compare_financial_metrics
from app.ai.exceptions import DataNotFoundError, ValidationError

class TestRevenueTool:
    @patch('app.ai.tools.revenue_tools.get_session')
    def test_get_revenue_by_period_success(self, mock_get_session):
        """Test successful revenue retrieval."""
        # Mock database session and query results
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        
        mock_records = [
            Mock(period_start="2024-01-01", period_end="2024-01-31", 
                 revenue=1000.00, source="quickbooks"),
            Mock(period_start="2024-02-01", period_end="2024-02-29", 
                 revenue=1200.00, source="quickbooks")
        ]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_records
        
        result = get_revenue_by_period("2024-01-01", "2024-02-29")
        
        assert result["total_revenue"] == 2200.00
        assert result["period_count"] == 2
        assert len(result["monthly_breakdown"]) == 2
    
    @patch('app.ai.tools.revenue_tools.get_session')
    def test_get_revenue_by_period_no_data(self, mock_get_session):
        """Test revenue retrieval with no data."""
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        with pytest.raises(DataNotFoundError):
            get_revenue_by_period("2024-01-01", "2024-01-31")
    
    def test_get_revenue_by_period_invalid_dates(self):
        """Test revenue retrieval with invalid dates."""
        with pytest.raises(ValidationError):
            get_revenue_by_period("invalid-date", "2024-01-31")
        
        with pytest.raises(ValidationError):
            get_revenue_by_period("2024-01-31", "2024-01-01")  # End before start

class TestComparisonTool:
    @patch('app.ai.tools.comparison_tools.get_session')
    def test_compare_financial_metrics_success(self, mock_get_session):
        """Test successful financial metrics comparison."""
        mock_session = Mock()
        mock_get_session.return_value = mock_session
        
        # Mock data for two periods
        period1_data = [Mock(revenue=1000.00, expenses=600.00, net_profit=400.00)]
        period2_data = [Mock(revenue=1200.00, expenses=700.00, net_profit=500.00)]
        
        mock_session.query.return_value.filter.return_value.all.side_effect = [
            period1_data, period2_data
        ]
        
        result = compare_financial_metrics(
            "2024-01-01", "2024-01-31",
            "2024-02-01", "2024-02-29",
            ["revenue", "expenses", "net_profit"]
        )
        
        assert result["period1"]["total_revenue"] == 1000.00
        assert result["period2"]["total_revenue"] == 1200.00
        assert result["comparison"]["revenue_change_percent"] == 20.0
        assert result["comparison"]["revenue_change_amount"] == 200.00
```

## Integration Testing

### End-to-End Ingestion Testing

```python
# tests/integration/test_end_to_end_ingestion.py
import pytest
import tempfile
import json
from app.services.ingestion import DataIngestionService
from app.database.connection import get_session
from app.database.models import FinancialRecord, Account, AccountValue

class TestEndToEndIngestion:
    def setup_method(self):
        self.ingestion_service = DataIngestionService()
        self.session = get_session()
    
    def test_quickbooks_ingestion_complete_workflow(self):
        """Test complete QuickBooks ingestion workflow."""
        # Create test data file
        test_data = {
            "Header": {"Currency": "USD"},
            "Columns": [
                {
                    "ColTitle": "Jan 2024",
                    "MetaData": [
                        {"Name": "StartDate", "Value": "2024-01-01"},
                        {"Name": "EndDate", "Value": "2024-01-31"}
                    ]
                }
            ],
            "Rows": [
                {
                    "ColData": [{"value": "Revenue"}],
                    "group": "Income",
                    "Rows": [
                        {
                            "ColData": [
                                {"value": "Service Revenue"},
                                {"value": "15000.00"}
                            ]
                        }
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_file_path = f.name
        
        try:
            # Perform ingestion
            result = self.ingestion_service.ingest_file(temp_file_path, "quickbooks")
            
            # Verify ingestion result
            assert result.status == "completed"
            assert result.records_processed > 0
            assert result.validation_result.is_valid
            
            # Verify database records
            financial_records = self.session.query(FinancialRecord).all()
            assert len(financial_records) > 0
            
            accounts = self.session.query(Account).all()
            assert len(accounts) > 0
            
            account_values = self.session.query(AccountValue).all()
            assert len(account_values) > 0
            
            # Verify data integrity
            record = financial_records[0]
            assert record.source == "quickbooks"
            assert record.currency == "USD"
            assert record.revenue > 0
            
        finally:
            import os
            os.unlink(temp_file_path)
    
    def test_batch_ingestion_multiple_sources(self):
        """Test batch ingestion with multiple data sources."""
        # Create QuickBooks test file
        qb_data = {
            "Header": {"Currency": "USD"},
            "Columns": [{"ColTitle": "Jan 2024", "MetaData": [
                {"Name": "StartDate", "Value": "2024-01-01"},
                {"Name": "EndDate", "Value": "2024-01-31"}
            ]}],
            "Rows": [{"ColData": [{"value": "Revenue"}], "group": "Income", "Rows": [
                {"ColData": [{"value": "Service Revenue"}, {"value": "10000.00"}]}
            ]}]
        }
        
        # Create Rootfi test file
        rootfi_data = {
            "data": [
                {
                    "period_start": "2024-01-01",
                    "period_end": "2024-01-31",
                    "currency_id": "USD",
                    "revenue": [
                        {"name": "Professional Services", "value": 12000.00}
                    ]
                }
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as qb_file:
            json.dump(qb_data, qb_file)
            qb_file_path = qb_file.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as rf_file:
            json.dump(rootfi_data, rf_file)
            rf_file_path = rf_file.name
        
        try:
            # Perform batch ingestion
            result = self.ingestion_service.ingest_batch(
                [qb_file_path, rf_file_path],
                ["quickbooks", "rootfi"]
            )
            
            # Verify batch result
            assert result.status == "completed"
            assert result.files_successful == 2
            assert result.files_failed == 0
            assert result.total_records_processed > 0
            
            # Verify both sources are represented
            financial_records = self.session.query(FinancialRecord).all()
            sources = {record.source for record in financial_records}
            assert "quickbooks" in sources
            assert "rootfi" in sources
            
        finally:
            import os
            os.unlink(qb_file_path)
            os.unlink(rf_file_path)
```

### AI Agent Integration Testing

```python
# tests/integration/test_ai_agent_integration.py
import pytest
from unittest.mock import Mock, patch
from app.ai.agent import FinancialAgent
from app.ai.conversation import ConversationManager

class TestAIAgentIntegration:
    def setup_method(self):
        self.agent = FinancialAgent()
        self.conversation_manager = ConversationManager()
    
    @patch('app.ai.llm_client.LLMClient.chat_completion')
    def test_agent_revenue_query_integration(self, mock_chat_completion):
        """Test AI agent integration with revenue query."""
        # Mock LLM response
        mock_chat_completion.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "I'll help you get the revenue data.",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "function": {
                                    "name": "get_revenue_by_period",
                                    "arguments": '{"start_date": "2024-01-01", "end_date": "2024-01-31"}'
                                }
                            }
                        ]
                    }
                }
            ]
        }
        
        # Mock tool execution
        with patch('app.ai.registry.call_tool') as mock_call_tool:
            mock_call_tool.return_value = {
                "total_revenue": 15000.00,
                "period_count": 1,
                "monthly_breakdown": [
                    {"month": "2024-01", "revenue": 15000.00}
                ]
            }
            
            # Process query
            result = self.agent.process_query("What was the revenue in January 2024?")
            
            # Verify tool was called
            mock_call_tool.assert_called_once_with(
                "get_revenue_by_period",
                start_date="2024-01-01",
                end_date="2024-01-31"
            )
            
            # Verify response structure
            assert "conversation_id" in result
            assert "tool_calls_made" in result
            assert len(result["tool_calls_made"]) == 1
            assert result["tool_calls_made"][0]["tool_name"] == "get_revenue_by_period"
    
    def test_conversation_context_preservation(self):
        """Test conversation context preservation across multiple queries."""
        conversation_id = "test_conversation"
        
        # First query
        with patch('app.ai.llm_client.LLMClient.chat_completion') as mock_chat:
            mock_chat.return_value = {
                "choices": [{"message": {"content": "The revenue was $15,000."}}]
            }
            
            result1 = self.agent.process_query(
                "What was the revenue last month?",
                conversation_id=conversation_id
            )
            
            assert result1["conversation_id"] == conversation_id
        
        # Follow-up query
        with patch('app.ai.llm_client.LLMClient.chat_completion') as mock_chat:
            mock_chat.return_value = {
                "choices": [{"message": {"content": "That's a 20% increase from the previous month."}}]
            }
            
            result2 = self.agent.process_query(
                "How does that compare to the previous month?",
                conversation_id=conversation_id
            )
            
            assert result2["conversation_id"] == conversation_id
            
            # Verify conversation history was passed to LLM
            call_args = mock_chat.call_args[1]
            messages = call_args["messages"]
            assert len(messages) > 2  # System prompt + previous messages
```

## API Testing

### Endpoint Testing

```python
# tests/api/test_financial_data_endpoints.py
import pytest
from httpx import AsyncClient
from app.main import app

class TestFinancialDataEndpoints:
    @pytest.mark.asyncio
    async def test_get_financial_data_basic(self):
        """Test basic financial data retrieval."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/financial-data")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "data" in data
            assert "pagination" in data
            assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_get_financial_data_with_filters(self):
        """Test financial data retrieval with filters."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/financial-data",
                params={
                    "source": "quickbooks",
                    "period_start": "2024-01-01",
                    "period_end": "2024-12-31",
                    "page_size": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify filters were applied
            if data["data"]:
                for record in data["data"]:
                    assert record["source"] == "quickbooks"
                    assert record["period_start"] >= "2024-01-01"
                    assert record["period_end"] <= "2024-12-31"
    
    @pytest.mark.asyncio
    async def test_get_period_summary(self):
        """Test period summary endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/financial-data/2024-Q1")
            
            assert response.status_code in [200, 404]  # 404 if no data
            
            if response.status_code == 200:
                data = response.json()
                assert "period" in data
                assert "summary" in data
                assert data["period"] == "2024-Q1"
    
    @pytest.mark.asyncio
    async def test_get_accounts(self):
        """Test accounts endpoint."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/financial-data/accounts")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "data" in data
            assert "pagination" in data
            assert isinstance(data["data"], list)
    
    @pytest.mark.asyncio
    async def test_invalid_period_format(self):
        """Test invalid period format handling."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/financial-data/invalid-period")
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
```

### Query Endpoint Testing

```python
# tests/api/test_query_endpoints.py
import pytest
from unittest.mock import patch
from httpx import AsyncClient
from app.main import app

class TestQueryEndpoints:
    @pytest.mark.asyncio
    @patch('app.ai.agent.FinancialAgent.process_query')
    async def test_natural_language_query(self, mock_process_query):
        """Test natural language query endpoint."""
        # Mock agent response
        mock_process_query.return_value = {
            "answer": "The total revenue in Q1 2024 was $45,000.",
            "conversation_id": "test_conversation",
            "tool_calls_made": [
                {
                    "tool_name": "get_revenue_by_period",
                    "parameters": {"start_date": "2024-01-01", "end_date": "2024-03-31"}
                }
            ],
            "confidence_score": 0.95
        }
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/query",
                json={"query": "What was the total revenue in Q1 2024?"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "answer" in data
            assert "conversation_id" in data
            assert "tool_calls_made" in data
            assert data["answer"] == "The total revenue in Q1 2024 was $45,000."
    
    @pytest.mark.asyncio
    async def test_query_validation(self):
        """Test query input validation."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Empty query
            response = await client.post("/api/v1/query", json={"query": ""})
            assert response.status_code == 422
            
            # Missing query field
            response = await client.post("/api/v1/query", json={})
            assert response.status_code == 422
            
            # Query too long
            long_query = "x" * 2000
            response = await client.post("/api/v1/query", json={"query": long_query})
            assert response.status_code == 422
```

## Performance Testing

### Load Testing

```python
# tests/performance/test_load.py
import pytest
import asyncio
import time
from httpx import AsyncClient
from app.main import app

class TestPerformance:
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test system performance under concurrent load."""
        async def make_request(client):
            start_time = time.time()
            response = await client.get("/api/v1/health")
            end_time = time.time()
            return response.status_code, end_time - start_time
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Create 50 concurrent requests
            tasks = [make_request(client) for _ in range(50)]
            results = await asyncio.gather(*tasks)
            
            # Analyze results
            status_codes = [result[0] for result in results]
            response_times = [result[1] for result in results]
            
            # All requests should succeed
            assert all(code == 200 for code in status_codes)
            
            # Average response time should be reasonable
            avg_response_time = sum(response_times) / len(response_times)
            assert avg_response_time < 1.0  # Less than 1 second
            
            # No request should take too long
            max_response_time = max(response_times)
            assert max_response_time < 5.0  # Less than 5 seconds
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self):
        """Test memory usage stability under load."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make many requests
            for _ in range(100):
                await client.get("/api/v1/health")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024
```

### Database Performance Testing

```python
# tests/performance/test_database.py
import pytest
import time
from app.database.connection import get_session
from app.database.models import FinancialRecord

class TestDatabasePerformance:
    def test_query_performance(self):
        """Test database query performance."""
        session = get_session()
        
        # Test simple query performance
        start_time = time.time()
        records = session.query(FinancialRecord).limit(100).all()
        end_time = time.time()
        
        query_time = end_time - start_time
        assert query_time < 1.0  # Should complete in less than 1 second
        
        # Test filtered query performance
        start_time = time.time()
        filtered_records = session.query(FinancialRecord)\
            .filter(FinancialRecord.source == "quickbooks")\
            .limit(50).all()
        end_time = time.time()
        
        filtered_query_time = end_time - start_time
        assert filtered_query_time < 1.0  # Should complete in less than 1 second
```

## Test Data Management

### Test Fixtures

```python
# tests/fixtures/test_data.py
import json
from decimal import Decimal
from datetime import date

def create_sample_quickbooks_data():
    """Create sample QuickBooks data for testing."""
    return {
        "Header": {
            "Currency": "USD",
            "ReportBasis": "Accrual"
        },
        "Columns": [
            {
                "ColTitle": "Jan 2024",
                "ColType": "Money",
                "MetaData": [
                    {"Name": "StartDate", "Value": "2024-01-01"},
                    {"Name": "EndDate", "Value": "2024-01-31"}
                ]
            }
        ],
        "Rows": [
            {
                "ColData": [{"value": "Revenue"}],
                "group": "Income",
                "Rows": [
                    {
                        "ColData": [
                            {"value": "Service Revenue"},
                            {"value": "15000.00"}
                        ]
                    }
                ]
            }
        ]
    }

def create_sample_rootfi_data():
    """Create sample Rootfi data for testing."""
    return {
        "data": [
            {
                "period_start": "2024-01-01",
                "period_end": "2024-01-31",
                "currency_id": "USD",
                "revenue": [
                    {
                        "name": "Professional Services",
                        "value": 25000.00,
                        "line_items": [
                            {"name": "Consulting", "value": 15000.00},
                            {"name": "Development", "value": 10000.00}
                        ]
                    }
                ]
            }
        ]
    }

def create_sample_financial_record():
    """Create sample FinancialRecord for testing."""
    from app.models.financial import FinancialRecord
    
    return FinancialRecord(
        id="test_record_001",
        source="quickbooks",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 1, 31),
        currency="USD",
        revenue=Decimal("15000.00"),
        expenses=Decimal("8500.00"),
        net_profit=Decimal("6500.00"),
        raw_data={"test": True}
    )
```

### Database Test Setup

```python
# tests/fixtures/test_database.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.models import Base
from app.database.connection import get_session

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine("sqlite:///./test_financial_data.db", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)

@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()

@pytest.fixture
def populated_test_session(test_session):
    """Create test session with sample data."""
    from tests.fixtures.test_data import create_sample_financial_record
    
    # Add sample data
    record = create_sample_financial_record()
    test_session.add(record)
    test_session.commit()
    
    yield test_session
```

## Continuous Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_financial_data
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio pytest-cov
    
    - name: Run unit tests
      run: |
        pytest tests/unit/ -v --cov=app --cov-report=xml
      env:
        DATABASE_URL: sqlite:///./test_financial_data.db
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    
    - name: Run integration tests
      run: |
        pytest tests/integration/ -v
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_financial_data
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    
    - name: Run API tests
      run: |
        pytest tests/api/ -v
      env:
        DATABASE_URL: sqlite:///./test_financial_data.db
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]
  
  - repo: local
    hooks:
      - id: pytest-check
        name: pytest-check
        entry: pytest tests/unit/ -x -v
        language: system
        pass_filenames: false
        always_run: true
```

## Test Coverage

### Coverage Configuration

```ini
# .coveragerc
[run]
source = app
omit = 
    app/main.py
    app/core/config.py
    */tests/*
    */venv/*
    */__pycache__/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod

[html]
directory = htmlcov
```

### Coverage Targets

- **Overall Coverage**: > 90%
- **Core Services**: > 95%
- **API Endpoints**: > 85%
- **AI Tools**: > 90%
- **Parsers**: > 95%

### Running Coverage Reports

```bash
# Generate coverage report
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Generate XML report for CI
pytest --cov=app --cov-report=xml
```

This comprehensive testing guide ensures the AI Financial Data System maintains high quality, reliability, and performance across all components and use cases.