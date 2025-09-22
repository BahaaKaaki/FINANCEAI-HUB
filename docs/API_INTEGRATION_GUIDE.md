# AI Financial Data System - API Integration Guide

## Overview

This comprehensive guide provides everything you need to integrate with the AI Financial Data System API. The system offers powerful financial data processing, natural language querying, and AI-powered insights through a clean RESTful API.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [API Versioning](#api-versioning)
4. [Core Endpoints](#core-endpoints)
5. [Integration Examples](#integration-examples)
6. [Error Handling](#error-handling)
7. [Best Practices](#best-practices)
8. [SDKs and Libraries](#sdks-and-libraries)

## Quick Start

### 1. Verify API Availability

```bash
curl -X GET "http://localhost:8000/api/v1/health" \
     -H "Accept: application/json"
```

Expected response:
```json
{
    "status": "healthy",
    "timestamp": 1704067200.123,
    "version": "1.0.0",
    "uptime_seconds": 3600.0
}
```

### 2. Retrieve Financial Data

```bash
curl -X GET "http://localhost:8000/api/v1/financial-data?page=1&page_size=5" \
     -H "Accept: application/json"
```

### 3. Ask a Natural Language Question

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What was the total revenue in Q1 2024?"}'
```

## Authentication

Currently, the API does not require authentication. In production environments, implement appropriate authentication mechanisms:

- **API Keys**: Add `X-API-Key` header
- **OAuth 2.0**: Use Bearer tokens
- **JWT**: Include JWT tokens in Authorization header

Example with API key:
```bash
curl -X GET "http://localhost:8000/api/v1/financial-data" \
     -H "X-API-Key: your-api-key-here" \
     -H "Accept: application/json"
```

## API Versioning

The API uses URL path versioning with the current version being `v1`. All endpoints are prefixed with `/api/v1/`.

### Current Version: v1
```
GET /api/v1/financial-data
POST /api/v1/query
GET /api/v1/health
```

### Version Headers
The API includes version information in response headers:
- `X-API-Version`: Current API version
- `X-API-Latest-Version`: Latest available version

## Core Endpoints

### Health & Monitoring

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Comprehensive health check |
| `/api/v1/metrics` | GET | System metrics and performance |
| `/api/v1/health/database` | GET | Database-specific health check |
| `/api/v1/health/llm` | GET | AI service health check |

### Financial Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/financial-data` | GET | Retrieve financial records |
| `/api/v1/financial-data/{period}` | GET | Get period summary |
| `/api/v1/accounts` | GET | List accounts |
| `/api/v1/accounts/{id}` | GET | Get specific account |
| `/api/v1/accounts/{id}/hierarchy` | GET | Get account hierarchy |

### Natural Language Processing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/query` | POST | Process natural language queries |

### AI Insights

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/insights/revenue-trends` | GET | Revenue trend analysis |
| `/api/v1/insights/expense-analysis` | GET | Expense pattern analysis |
| `/api/v1/insights/cash-flow` | GET | Cash flow insights |
| `/api/v1/insights/seasonal-patterns` | GET | Seasonal pattern analysis |

### Data Ingestion

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/data/ingest` | POST | Ingest financial data |
| `/api/v1/data/status` | GET | Check ingestion status |

## Integration Examples

### Python with requests

```python
import requests
from datetime import date, datetime
import json

class FinancialDataClient:
    def __init__(self, base_url="http://localhost:8000", api_key=None):
        self.base_url = base_url
        self.session = requests.Session()
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Version": "v1"
        }
        
        if api_key:
            headers["X-API-Key"] = api_key
            
        self.session.headers.update(headers)
    
    def health_check(self):
        """Check API health status"""
        response = self.session.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()
    
    def get_financial_data(self, **filters):
        """Retrieve financial data with optional filtering"""
        response = self.session.get(
            f"{self.base_url}/api/v1/financial-data",
            params=filters
        )
        response.raise_for_status()
        return response.json()
    
    def query_natural_language(self, query, conversation_id=None):
        """Ask natural language questions"""
        payload = {"query": query}
        if conversation_id:
            payload["conversation_id"] = conversation_id
            
        response = self.session.post(
            f"{self.base_url}/api/v1/query",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    def get_insights(self, insight_type, **params):
        """Get AI-generated insights"""
        response = self.session.get(
            f"{self.base_url}/api/v1/insights/{insight_type}",
            params=params
        )
        response.raise_for_status()
        return response.json()

# Usage example
client = FinancialDataClient()

# Check system health
health = client.health_check()
print(f"System status: {health['status']}")

# Get Q1 2024 data
data = client.get_financial_data(
    source="quickbooks",
    period_start="2024-01-01",
    period_end="2024-03-31"
)
print(f"Found {data['total_count']} records")

# Ask a question
result = client.query_natural_language("What was the profit margin in Q1?")
print(f"Answer: {result['answer']}")

# Get revenue insights
insights = client.get_insights(
    "revenue-trends",
    start_date="2024-01-01",
    end_date="2024-06-30"
)
print(f"Key findings: {insights['key_findings']}")
```

### JavaScript/Node.js with axios

```javascript
const axios = require('axios');

class FinancialDataClient {
    constructor(baseURL = 'http://localhost:8000', apiKey = null) {
        this.client = axios.create({
            baseURL,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-API-Version': 'v1',
                ...(apiKey && { 'X-API-Key': apiKey })
            },
            timeout: 30000
        });
        
        // Add response interceptor for error handling
        this.client.interceptors.response.use(
            response => response,
            error => {
                console.error('API Error:', error.response?.data || error.message);
                throw error;
            }
        );
    }
    
    async healthCheck() {
        const response = await this.client.get('/api/v1/health');
        return response.data;
    }
    
    async getFinancialData(filters = {}) {
        const response = await this.client.get('/api/v1/financial-data', {
            params: filters
        });
        return response.data;
    }
    
    async queryNaturalLanguage(query, conversationId = null) {
        const payload = { query };
        if (conversationId) payload.conversation_id = conversationId;
        
        const response = await this.client.post('/api/v1/query', payload);
        return response.data;
    }
    
    async getInsights(insightType, params = {}) {
        const response = await this.client.get(`/api/v1/insights/${insightType}`, {
            params
        });
        return response.data;
    }
}

// Usage example
async function example() {
    const client = new FinancialDataClient();
    
    try {
        // Check health
        const health = await client.healthCheck();
        console.log('System status:', health.status);
        
        // Get financial data
        const data = await client.getFinancialData({
            source: 'quickbooks',
            page: 1,
            page_size: 10
        });
        console.log(`Found ${data.total_count} records`);
        
        // Natural language query
        const result = await client.queryNaturalLanguage(
            'What was the revenue growth rate in 2024?'
        );
        console.log('Answer:', result.answer);
        
        // Get insights
        const insights = await client.getInsights('revenue-trends', {
            start_date: '2024-01-01',
            end_date: '2024-06-30'
        });
        console.log('Insights:', insights.narrative);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

example();
```

### cURL Examples

#### Basic Data Retrieval
```bash
# Get all financial data
curl -X GET "http://localhost:8000/api/v1/financial-data" \
     -H "Accept: application/json"

# Filter by source and date range
curl -X GET "http://localhost:8000/api/v1/financial-data?source=quickbooks&period_start=2024-01-01&period_end=2024-03-31" \
     -H "Accept: application/json"

# Get period summary
curl -X GET "http://localhost:8000/api/v1/financial-data/2024-Q1" \
     -H "Accept: application/json"
```

#### Natural Language Queries
```bash
# Simple query
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What was the total profit in Q1 2024?"}'

# Query with conversation context
curl -X POST "http://localhost:8000/api/v1/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "How does that compare to Q2?",
       "conversation_id": "conv_123",
       "max_iterations": 5
     }'
```

#### AI Insights
```bash
# Revenue trends
curl -X GET "http://localhost:8000/api/v1/insights/revenue-trends?start_date=2024-01-01&end_date=2024-06-30" \
     -H "Accept: application/json"

# Seasonal patterns
curl -X GET "http://localhost:8000/api/v1/insights/seasonal-patterns?metric=revenue&years[]=2023&years[]=2024" \
     -H "Accept: application/json"

# Expense analysis
curl -X GET "http://localhost:8000/api/v1/insights/expense-analysis?start_date=2024-01-01&end_date=2024-12-31" \
     -H "Accept: application/json"
```

## Error Handling

The API uses standard HTTP status codes and provides detailed error information:

### Status Codes
- **200** - Success
- **400** - Bad Request (invalid parameters)
- **401** - Unauthorized (authentication required)
- **403** - Forbidden (insufficient permissions)
- **404** - Not Found
- **422** - Unprocessable Entity (validation errors)
- **429** - Too Many Requests (rate limited)
- **500** - Internal Server Error
- **503** - Service Unavailable (AI service issues)

### Error Response Format
```json
{
    "error": "validation_error",
    "message": "Invalid date format. Use YYYY-MM-DD format.",
    "details": {
        "field": "start_date",
        "provided_value": "2024/01/01",
        "expected_format": "YYYY-MM-DD"
    },
    "fallback_response": "Please check your date format and try again."
}
```

### Error Handling Best Practices

#### Python Example
```python
import requests
from requests.exceptions import RequestException, HTTPError, Timeout

def safe_api_call(client, endpoint, **kwargs):
    try:
        response = client.get(endpoint, **kwargs)
        response.raise_for_status()
        return response.json()
        
    except HTTPError as e:
        if e.response.status_code == 400:
            error_data = e.response.json()
            print(f"Bad request: {error_data.get('message')}")
            return None
        elif e.response.status_code == 503:
            print("Service temporarily unavailable, trying fallback...")
            return {"status": "unavailable"}
        else:
            raise
            
    except Timeout:
        print("Request timed out, retrying...")
        # Implement retry logic
        return None
        
    except RequestException as e:
        print(f"Network error: {e}")
        return None
```

#### JavaScript Example
```javascript
async function safeApiCall(client, endpoint, options = {}) {
    try {
        const response = await client.get(endpoint, options);
        return response.data;
        
    } catch (error) {
        if (error.response) {
            const status = error.response.status;
            const errorData = error.response.data;
            
            switch (status) {
                case 400:
                    console.error('Bad request:', errorData.message);
                    break;
                case 503:
                    console.warn('Service unavailable, using fallback');
                    return { status: 'unavailable' };
                case 429:
                    console.warn('Rate limited, waiting...');
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    return safeApiCall(client, endpoint, options); // Retry
                default:
                    console.error('API error:', errorData);
            }
        } else {
            console.error('Network error:', error.message);
        }
        return null;
    }
}
```

## Best Practices

### 1. Use Appropriate Timeouts
```python
# Python
session = requests.Session()
session.timeout = (5, 30)  # 5s connect, 30s read

# JavaScript
const client = axios.create({
    timeout: 30000  // 30 seconds
});
```

### 2. Implement Retry Logic
```python
import time
from functools import wraps

def retry_on_failure(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            return None
        return wrapper
    return decorator

@retry_on_failure(max_retries=3)
def get_financial_data(client, **params):
    return client.get_financial_data(**params)
```

### 3. Cache Responses When Appropriate
```python
import time
from functools import lru_cache

class CachedFinancialClient:
    def __init__(self, client):
        self.client = client
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    def get_with_cache(self, endpoint, params=None):
        cache_key = f"{endpoint}:{str(params)}"
        now = time.time()
        
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if now - timestamp < self._cache_ttl:
                return data
        
        # Fetch fresh data
        data = self.client.get(endpoint, params=params)
        self._cache[cache_key] = (data, now)
        return data
```

### 4. Handle Rate Limits Gracefully
```python
def handle_rate_limit(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        print(f"Rate limited. Waiting {retry_after} seconds...")
        time.sleep(retry_after)
        return True
    return False
```

### 5. Monitor API Health
```python
def monitor_api_health(client):
    try:
        health = client.health_check()
        if health['status'] != 'healthy':
            print(f"API health warning: {health['status']}")
            # Log to monitoring system
        return health['status'] == 'healthy'
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
```

## SDKs and Libraries

### Official SDKs (Planned)
- **Python SDK**: `pip install financial-data-sdk`
- **JavaScript SDK**: `npm install @financial-data/sdk`
- **Go SDK**: `go get github.com/financial-data/go-sdk`

### Community Libraries
- **financial-data-python**: Unofficial Python wrapper
- **financial-data-js**: JavaScript/TypeScript client
- **financial-data-cli**: Command-line interface

### SDK Example (Python)
```python
from financial_data_sdk import FinancialDataClient

# Initialize client
client = FinancialDataClient(
    base_url="http://localhost:8000",
    api_key="your-api-key",
    timeout=30
)

# Use high-level methods
with client:
    # Get quarterly summary
    q1_summary = client.quarters.get_summary("2024-Q1")
    
    # Ask natural language questions
    answer = client.ai.ask("What drove the revenue increase in March?")
    
    # Get insights with caching
    insights = client.insights.revenue_trends(
        start_date="2024-01-01",
        end_date="2024-06-30",
        cache=True
    )
    
    # Batch operations
    results = client.batch([
        client.data.get_financial_records(source="quickbooks"),
        client.ai.ask("Summarize Q1 performance"),
        client.insights.expense_analysis(period="2024-Q1")
    ])
```

## Support and Resources

### Documentation
- **Interactive API Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **API Reference**: `http://localhost:8000/api/v1/docs/api-reference`

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Community Forum**: Ask questions and share solutions
- **Email Support**: support@example.com

### Useful Links
- **API Status Page**: Monitor system status
- **Changelog**: Track API updates and changes
- **Migration Guides**: Version upgrade instructions
- **Code Examples**: Additional integration examples

---

This guide provides a comprehensive foundation for integrating with the AI Financial Data System API. For the most up-to-date information, always refer to the interactive API documentation at `/docs`.