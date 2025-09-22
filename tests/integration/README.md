# Integration Tests for AI Financial Data System

This directory contains comprehensive integration tests that validate the complete functionality of the AI Financial Data System. These tests ensure all components work together correctly under realistic conditions.

## Test Suites

### 1. End-to-End Ingestion Tests (`test_end_to_end_ingestion.py`)
Tests the complete data ingestion workflow from raw files to database storage.

**Coverage:**
- Complete QuickBooks data ingestion workflow
- Complete Rootfi data ingestion workflow  
- Batch ingestion of multiple files
- Error handling and recovery scenarios
- Duplicate data handling
- Auto source type detection
- Ingestion status tracking and logging

**Key Scenarios:**
- Valid data processing with perfect quality scores
- Invalid data handling with appropriate error messages
- Mixed batch processing with partial failures
- Database transaction integrity

### 2. AI Agent Integration Tests (`test_ai_agent_integration.py`)
Tests the AI agent's natural language processing and tool calling capabilities.

**Coverage:**
- Agent initialization and configuration
- Simple revenue queries with tool execution
- Complex comparison queries with multiple tool calls
- Growth rate analysis with time series data
- Conversation context management
- Tool execution error handling
- Maximum iteration limits
- Multi-step reasoning workflows

**Key Scenarios:**
- Single tool calls for basic queries
- Multi-tool workflows for complex analysis
- Error recovery and graceful degradation
- Conversation continuity across multiple queries

### 3. API Endpoints Integration Tests (`test_api_endpoints_integration.py`)
Tests all API endpoints with various input scenarios and error conditions.

**Coverage:**
- Health and monitoring endpoints
- Financial data retrieval with filtering
- Account hierarchy navigation
- Natural language query processing
- Data ingestion API endpoints
- AI insights generation
- Concurrent request handling

**Key Scenarios:**
- Valid requests with expected responses
- Invalid input validation and error handling
- Pagination and large dataset handling
- Authentication and authorization (when implemented)
- Rate limiting and throttling

### 4. Performance & Concurrency Tests (`test_performance_concurrent.py`)
Tests system performance under load and concurrent user scenarios.

**Coverage:**
- Single user performance benchmarks
- Concurrent user simulation (up to 25 users)
- Database connection pool performance
- Memory usage under load
- Mixed workload scenarios (API + queries)
- Response time distribution analysis

**Key Metrics:**
- Average response time < 2s for API calls
- 95th percentile response time < 5s
- Success rate > 90% under concurrent load
- Memory usage growth < 100MB during tests
- Database connection pool efficiency

### 5. Data Quality Validation Tests (`test_data_quality_validation.py`)
Tests comprehensive data validation with real financial data samples.

**Coverage:**
- Perfect data quality scoring (score = 1.0)
- Warning-level issues (negative revenue, uncommon currency)
- Error-level issues (invalid dates, missing parents)
- Balance equation validation
- Account hierarchy validation
- Currency format validation
- Extreme value handling

**Real-World Scenarios:**
- Small business financial data
- Seasonal business patterns
- Multi-currency operations
- Startup business models (high expenses, low revenue)
- Enterprise-level data volumes

## Running the Tests

### Prerequisites

1. **Database Setup**: Tests require a clean SQLite database
2. **Dependencies**: Install test dependencies
   ```bash
   pip install pytest pytest-asyncio pytest-mock
   ```

3. **Environment**: Set up test environment variables if needed

### Running All Integration Tests

```bash
# Run all integration tests
python tests/integration/run_integration_tests.py

# Run with verbose output
python tests/integration/run_integration_tests.py -v

# Run with parallel execution (requires pytest-xdist)
python tests/integration/run_integration_tests.py -p
```

### Running Individual Test Suites

```bash
# Run specific test file
pytest tests/integration/test_end_to_end_ingestion.py -v

# Run specific test class
pytest tests/integration/test_ai_agent_integration.py::TestAIAgentIntegration -v

# Run specific test method
pytest tests/integration/test_api_endpoints_integration.py::TestQueryEndpoint::test_basic_query_processing -v
```

### Running Tests by Category

```bash
# Run only database-related tests
pytest -m database

# Run only performance tests
pytest -m performance

# Run only AI-related tests
pytest -m ai
```

## Test Reports

The integration test runner generates comprehensive reports:

### JSON Report
- Detailed test results with timing information
- System information and environment details
- Error messages and stack traces
- Performance metrics and statistics

### HTML Report
- Visual dashboard with test results
- Interactive charts and graphs
- Drill-down capability for detailed analysis
- Export functionality for sharing

### JUnit XML Reports
- Compatible with CI/CD systems
- Individual reports for each test suite
- Integration with build pipelines
- Historical trend analysis

## Performance Benchmarks

### Expected Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| API Response Time (avg) | < 1.0s | Single user, simple queries |
| API Response Time (95th) | < 2.0s | Single user, complex queries |
| Query Processing (avg) | < 3.0s | AI agent with tool calls |
| Query Processing (95th) | < 5.0s | Complex multi-tool queries |
| Concurrent Success Rate | > 90% | 20 concurrent users |
| Database Query Time | < 500ms | Simple data retrieval |
| Memory Usage Growth | < 100MB | During full test suite |

### Load Testing Scenarios

1. **Light Load**: 5 concurrent users, 50 requests total
2. **Medium Load**: 15 concurrent users, 150 requests total  
3. **Heavy Load**: 25 concurrent users, 250 requests total
4. **Mixed Workload**: 70% API calls, 30% AI queries
5. **Database Stress**: 50 concurrent database-intensive requests

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Ensure database is properly initialized
   - Check connection string configuration
   - Verify database permissions

2. **AI Agent Test Failures**
   - Verify LLM API keys are configured
   - Check network connectivity to AI services
   - Review mock configurations for offline testing

3. **Performance Test Failures**
   - Adjust performance targets for your hardware
   - Check system resources (CPU, memory)
   - Review concurrent user limits

4. **Memory Issues**
   - Monitor test execution with memory profiling
   - Check for memory leaks in long-running tests
   - Adjust test data sizes if needed

### Debug Mode

Run tests with debug logging:

```bash
pytest tests/integration/ -v -s --log-cli-level=DEBUG
```

### Test Data Cleanup

Clean test databases between runs:

```bash
# Remove test database files
rm -f test_*.db

# Clear test cache
pytest --cache-clear
```

## Contributing

When adding new integration tests:

1. **Follow Naming Conventions**: Use descriptive test names
2. **Add Proper Documentation**: Include docstrings and comments
3. **Use Appropriate Fixtures**: Leverage existing database fixtures
4. **Include Error Scenarios**: Test both success and failure cases
5. **Add Performance Assertions**: Include timing and resource checks
6. **Update This README**: Document new test scenarios

### Test Structure Template

```python
class TestNewFeature:
    """Test new feature integration."""
    
    def test_basic_functionality(self, setup_database):
        """Test basic feature functionality."""
        # Arrange
        # Act  
        # Assert
        
    def test_error_handling(self, setup_database):
        """Test error handling scenarios."""
        # Test various error conditions
        
    def test_performance(self, setup_database):
        """Test performance characteristics."""
        # Include timing assertions
```

## Continuous Integration

These integration tests are designed to run in CI/CD pipelines:

### GitHub Actions Example

```yaml
name: Integration Tests
on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.9
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run integration tests
        run: python tests/integration/run_integration_tests.py
      - name: Upload test reports
        uses: actions/upload-artifact@v2
        with:
          name: test-reports
          path: test_reports/
```

## Monitoring and Alerts

Set up monitoring for integration test results:

1. **Test Success Rate**: Alert if < 95%
2. **Performance Degradation**: Alert if response times increase > 50%
3. **Memory Usage**: Alert if memory growth > 200MB
4. **Database Performance**: Alert if query times > 1s

This ensures the system maintains high quality and performance standards over time.