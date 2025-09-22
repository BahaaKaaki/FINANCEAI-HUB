"""
API Documentation and Examples Module

This module provides comprehensive API documentation, usage examples,
and integration guides for the AI Financial Data System.
"""

from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

router = APIRouter(tags=["Documentation"])


class APIExample(BaseModel):
    """Model for API usage examples."""
    
    title: str = Field(..., description="Example title")
    description: str = Field(..., description="Example description")
    endpoint: str = Field(..., description="API endpoint")
    method: str = Field(..., description="HTTP method")
    request_example: Dict[str, Any] = Field(..., description="Example request")
    response_example: Dict[str, Any] = Field(..., description="Example response")
    curl_example: str = Field(..., description="cURL command example")


class IntegrationGuide(BaseModel):
    """Model for integration guides."""
    
    title: str = Field(..., description="Guide title")
    description: str = Field(..., description="Guide description")
    steps: List[Dict[str, str]] = Field(..., description="Integration steps")
    code_examples: Dict[str, str] = Field(..., description="Code examples by language")


@router.get("/examples", response_model=List[APIExample])
async def get_api_examples() -> List[APIExample]:
    """
    Get comprehensive API usage examples.
    
    Returns a collection of practical examples showing how to use
    various API endpoints with sample requests and responses.
    
    Returns:
        List of API examples with request/response samples
    """
    examples = [
        APIExample(
            title="Basic Financial Data Query",
            description="Retrieve financial records with basic filtering",
            endpoint="/api/v1/financial-data",
            method="GET",
            request_example={
                "url": "/api/v1/financial-data?page=1&page_size=10&source=quickbooks",
                "headers": {"Accept": "application/json"}
            },
            response_example={
                "data": [
                    {
                        "id": "qb_2024_q1",
                        "source": "quickbooks",
                        "period_start": "2024-01-01",
                        "period_end": "2024-03-31",
                        "currency": "USD",
                        "revenue": 125000.00,
                        "expenses": 85000.00,
                        "net_profit": 40000.00,
                        "created_at": "2024-04-01T10:00:00Z",
                        "updated_at": "2024-04-01T10:00:00Z"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "page_size": 10,
                    "total_pages": 5,
                    "has_next": True,
                    "has_prev": False
                },
                "total_count": 45,
                "filters_applied": {"source": "quickbooks"}
            },
            curl_example='curl -X GET "http://localhost:8000/api/v1/financial-data?source=quickbooks" -H "Accept: application/json"'
        ),
        
        APIExample(
            title="Natural Language Query",
            description="Ask questions about financial data in natural language",
            endpoint="/api/v1/query",
            method="POST",
            request_example={
                "query": "What was the total revenue in Q1 2024?",
                "conversation_id": "conv_123",
                "max_iterations": 5,
                "include_raw_data": False
            },
            response_example={
                "answer": "The total revenue in Q1 2024 was $125,000. This represents a 15% increase compared to Q4 2023 ($108,695). The revenue was primarily driven by strong performance in March ($45,000) and February ($42,000).",
                "supporting_data": {
                    "analysis_summary": {
                        "tools_executed": 2,
                        "data_sources": ["quickbooks"],
                        "date_ranges": ["2024-01-01 to 2024-03-31"],
                        "metrics_analyzed": ["revenue", "growth_rate"]
                    },
                    "data_quality": {
                        "successful_operations": 2,
                        "failed_operations": 0,
                        "data_completeness": "complete"
                    }
                },
                "conversation_id": "conv_123",
                "query_metadata": {
                    "query_id": "query_1704067200000",
                    "processing_time_seconds": 2.345,
                    "tools_used": 2,
                    "iterations": 1
                },
                "suggestions": [
                    "What were the main drivers of this revenue performance?",
                    "How does this compare to the same period last year?",
                    "What are the revenue trends over the last 6 months?"
                ]
            },
            curl_example='curl -X POST "http://localhost:8000/api/v1/query" -H "Content-Type: application/json" -d \'{"query": "What was the total revenue in Q1 2024?"}\''
        ),
        
        APIExample(
            title="Generate Revenue Insights",
            description="Get AI-powered insights about revenue trends",
            endpoint="/api/v1/insights/revenue-trends",
            method="GET",
            request_example={
                "url": "/api/v1/insights/revenue-trends?start_date=2024-01-01&end_date=2024-06-30",
                "headers": {"Accept": "application/json"}
            },
            response_example={
                "insight_type": "revenue_trends",
                "period": "2024-01-01 to 2024-06-30",
                "metric": "revenue",
                "narrative": "Revenue showed strong growth during the first half of 2024, with a total of $285,000 generated across all sources. The growth rate averaged 12% month-over-month, with particularly strong performance in March and May.",
                "key_findings": [
                    "Total revenue increased by 18% compared to the same period in 2023",
                    "March showed the highest single-month revenue at $52,000",
                    "QuickBooks data shows more consistent growth than Rootfi data",
                    "Revenue growth accelerated in Q2 with a 22% quarter-over-quarter increase"
                ],
                "recommendations": [
                    "Focus marketing efforts on replicating March's success factors",
                    "Investigate the factors driving Q2 acceleration for sustainability",
                    "Consider expanding successful revenue streams identified in the analysis"
                ],
                "data_points": {
                    "total_revenue": 285000.00,
                    "growth_rate_percent": 18.0,
                    "best_month": {"month": "March", "revenue": 52000.00},
                    "quarterly_comparison": {"Q1": 125000.00, "Q2": 160000.00}
                },
                "generated_at": "2024-07-01T14:30:00Z"
            },
            curl_example='curl -X GET "http://localhost:8000/api/v1/insights/revenue-trends?start_date=2024-01-01&end_date=2024-06-30" -H "Accept: application/json"'
        ),
        
        APIExample(
            title="Health Check",
            description="Check system health and component status",
            endpoint="/api/v1/health",
            method="GET",
            request_example={
                "url": "/api/v1/health",
                "headers": {"Accept": "application/json"}
            },
            response_example={
                "status": "healthy",
                "timestamp": 1704067200.123,
                "version": "1.0.0",
                "uptime_seconds": 3600.0,
                "checks": {
                    "database": {
                        "status": "healthy",
                        "duration_ms": 15.2,
                        "details": {
                            "connection_pool_size": 10,
                            "active_connections": 2,
                            "database_size_mb": 45.6
                        }
                    },
                    "llm_service": {
                        "status": "healthy",
                        "duration_ms": 120.5,
                        "provider": "openai",
                        "model": "gpt-4",
                        "configured": True
                    },
                    "monitoring": {
                        "status": "healthy",
                        "message": "Monitoring system operational"
                    }
                }
            },
            curl_example='curl -X GET "http://localhost:8000/api/v1/health" -H "Accept: application/json"'
        ),
        
        APIExample(
            title="Data Ingestion",
            description="Ingest financial data from JSON files",
            endpoint="/api/v1/data/ingest",
            method="POST",
            request_example={
                "source_type": "quickbooks",
                "file_path": "data_set_1.json",
                "validate_data": True,
                "overwrite_existing": False
            },
            response_example={
                "status": "success",
                "message": "Data ingestion completed successfully",
                "ingestion_id": "ing_1704067200000",
                "summary": {
                    "records_processed": 12,
                    "records_created": 10,
                    "records_updated": 2,
                    "records_failed": 0,
                    "processing_time_seconds": 5.67
                },
                "validation_results": {
                    "total_validations": 12,
                    "passed": 12,
                    "failed": 0,
                    "warnings": 1
                },
                "data_quality_score": 95.5,
                "timestamp": "2024-01-01T12:00:00Z"
            },
            curl_example='curl -X POST "http://localhost:8000/api/v1/data/ingest" -H "Content-Type: application/json" -d \'{"source_type": "quickbooks", "file_path": "data_set_1.json"}\''
        )
    ]
    
    return examples


@router.get("/integration-guides", response_model=List[IntegrationGuide])
async def get_integration_guides() -> List[IntegrationGuide]:
    """
    Get comprehensive integration guides for different programming languages.
    
    Returns step-by-step guides for integrating with the API using
    popular programming languages and frameworks.
    
    Returns:
        List of integration guides with code examples
    """
    guides = [
        IntegrationGuide(
            title="Python Integration with requests",
            description="Complete guide for integrating with the API using Python and the requests library",
            steps=[
                {
                    "step": "1",
                    "title": "Install Dependencies",
                    "description": "Install the required Python packages"
                },
                {
                    "step": "2", 
                    "title": "Set Up Base Configuration",
                    "description": "Configure the base URL and common headers"
                },
                {
                    "step": "3",
                    "title": "Implement Data Retrieval",
                    "description": "Create functions to retrieve financial data"
                },
                {
                    "step": "4",
                    "title": "Add Natural Language Queries",
                    "description": "Implement natural language query functionality"
                },
                {
                    "step": "5",
                    "title": "Handle Errors and Monitoring",
                    "description": "Add proper error handling and health checks"
                }
            ],
            code_examples={
                "installation": """pip install requests python-dateutil""",
                "basic_setup": """
import requests
from datetime import datetime, date
import json

class FinancialDataClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def health_check(self):
        \"\"\"Check API health status\"\"\"
        response = self.session.get(f"{self.base_url}/api/v1/health")
        response.raise_for_status()
        return response.json()
""",
                "data_retrieval": """
    def get_financial_data(self, source=None, start_date=None, end_date=None, page=1, page_size=20):
        \"\"\"Retrieve financial data with optional filtering\"\"\"
        params = {"page": page, "page_size": page_size}
        
        if source:
            params["source"] = source
        if start_date:
            params["period_start"] = start_date.isoformat()
        if end_date:
            params["period_end"] = end_date.isoformat()
            
        response = self.session.get(
            f"{self.base_url}/api/v1/financial-data",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_period_summary(self, period, source=None):
        \"\"\"Get aggregated data for a specific period\"\"\"
        params = {}
        if source:
            params["source"] = source
            
        response = self.session.get(
            f"{self.base_url}/api/v1/financial-data/{period}",
            params=params
        )
        response.raise_for_status()
        return response.json()
""",
                "natural_language": """
    def query_natural_language(self, query, conversation_id=None):
        \"\"\"Ask natural language questions about financial data\"\"\"
        payload = {"query": query}
        
        if conversation_id:
            payload["conversation_id"] = conversation_id
            
        response = self.session.post(
            f"{self.base_url}/api/v1/query",
            json=payload
        )
        response.raise_for_status()
        return response.json()
""",
                "insights": """
    def get_revenue_insights(self, start_date, end_date, source=None):
        \"\"\"Get AI-generated revenue insights\"\"\"
        params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        
        if source:
            params["source"] = source
            
        response = self.session.get(
            f"{self.base_url}/api/v1/insights/revenue-trends",
            params=params
        )
        response.raise_for_status()
        return response.json()
""",
                "usage_example": """
# Example usage
client = FinancialDataClient()

# Check system health
health = client.health_check()
print(f"System status: {health['status']}")

# Get financial data
data = client.get_financial_data(
    source="quickbooks",
    start_date=date(2024, 1, 1),
    end_date=date(2024, 3, 31)
)
print(f"Found {data['total_count']} records")

# Ask natural language question
result = client.query_natural_language("What was the profit in Q1 2024?")
print(f"Answer: {result['answer']}")

# Get AI insights
insights = client.get_revenue_insights(
    start_date=date(2024, 1, 1),
    end_date=date(2024, 6, 30)
)
print(f"Insight: {insights['narrative']}")
"""
            }
        ),
        
        IntegrationGuide(
            title="JavaScript/Node.js Integration",
            description="Complete guide for integrating with the API using JavaScript and Node.js",
            steps=[
                {
                    "step": "1",
                    "title": "Install Dependencies",
                    "description": "Install axios for HTTP requests"
                },
                {
                    "step": "2",
                    "title": "Create API Client Class",
                    "description": "Set up a reusable API client"
                },
                {
                    "step": "3",
                    "title": "Implement Core Methods",
                    "description": "Add methods for data retrieval and queries"
                },
                {
                    "step": "4",
                    "title": "Add Error Handling",
                    "description": "Implement proper error handling and retries"
                }
            ],
            code_examples={
                "installation": """npm install axios""",
                "client_setup": """
const axios = require('axios');

class FinancialDataClient {
    constructor(baseURL = 'http://localhost:8000') {
        this.client = axios.create({
            baseURL,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            timeout: 30000
        });
        
        // Add response interceptor for error handling
        this.client.interceptors.response.use(
            response => response,
            error => {
                console.error('API Error:', error.response?.data || error.message);
                return Promise.reject(error);
            }
        );
    }
    
    async healthCheck() {
        const response = await this.client.get('/api/v1/health');
        return response.data;
    }
}
""",
                "data_methods": """
    async getFinancialData(options = {}) {
        const { source, startDate, endDate, page = 1, pageSize = 20 } = options;
        
        const params = { page, page_size: pageSize };
        
        if (source) params.source = source;
        if (startDate) params.period_start = startDate;
        if (endDate) params.period_end = endDate;
        
        const response = await this.client.get('/api/v1/financial-data', { params });
        return response.data;
    }
    
    async queryNaturalLanguage(query, conversationId = null) {
        const payload = { query };
        if (conversationId) payload.conversation_id = conversationId;
        
        const response = await this.client.post('/api/v1/query', payload);
        return response.data;
    }
    
    async getRevenueInsights(startDate, endDate, source = null) {
        const params = { start_date: startDate, end_date: endDate };
        if (source) params.source = source;
        
        const response = await this.client.get('/api/v1/insights/revenue-trends', { params });
        return response.data;
    }
""",
                "usage_example": """
// Example usage
const client = new FinancialDataClient();

async function example() {
    try {
        // Check health
        const health = await client.healthCheck();
        console.log('System status:', health.status);
        
        // Get financial data
        const data = await client.getFinancialData({
            source: 'quickbooks',
            startDate: '2024-01-01',
            endDate: '2024-03-31'
        });
        console.log(`Found ${data.total_count} records`);
        
        // Natural language query
        const result = await client.queryNaturalLanguage('What was the profit in Q1 2024?');
        console.log('Answer:', result.answer);
        
        // Get insights
        const insights = await client.getRevenueInsights('2024-01-01', '2024-06-30');
        console.log('Insight:', insights.narrative);
        
    } catch (error) {
        console.error('Error:', error.message);
    }
}

example();
"""
            }
        ),
        
        IntegrationGuide(
            title="cURL Command Line Integration",
            description="Examples of using the API directly with cURL commands",
            steps=[
                {
                    "step": "1",
                    "title": "Basic Health Check",
                    "description": "Verify the API is running"
                },
                {
                    "step": "2",
                    "title": "Retrieve Financial Data",
                    "description": "Get structured financial records"
                },
                {
                    "step": "3",
                    "title": "Natural Language Queries",
                    "description": "Ask questions in plain English"
                },
                {
                    "step": "4",
                    "title": "Generate Insights",
                    "description": "Get AI-powered analysis"
                }
            ],
            code_examples={
                "health_check": """curl -X GET "http://localhost:8000/api/v1/health" \\
     -H "Accept: application/json" \\
     | jq '.'""",
                "get_data": """# Get all financial data with pagination
curl -X GET "http://localhost:8000/api/v1/financial-data?page=1&page_size=10" \\
     -H "Accept: application/json" \\
     | jq '.'

# Filter by source and date range
curl -X GET "http://localhost:8000/api/v1/financial-data?source=quickbooks&period_start=2024-01-01&period_end=2024-03-31" \\
     -H "Accept: application/json" \\
     | jq '.data[] | {id, revenue, expenses, net_profit}'""",
                "natural_language": """# Ask a natural language question
curl -X POST "http://localhost:8000/api/v1/query" \\
     -H "Content-Type: application/json" \\
     -H "Accept: application/json" \\
     -d '{
       "query": "What was the total revenue in Q1 2024?",
       "max_iterations": 5
     }' \\
     | jq '.answer'""",
                "insights": """# Get revenue trends insight
curl -X GET "http://localhost:8000/api/v1/insights/revenue-trends?start_date=2024-01-01&end_date=2024-06-30" \\
     -H "Accept: application/json" \\
     | jq '{narrative, key_findings, recommendations}'

# Get seasonal patterns
curl -X GET "http://localhost:8000/api/v1/insights/seasonal-patterns?metric=revenue&years[]=2023&years[]=2024" \\
     -H "Accept: application/json" \\
     | jq '.'""",
                "batch_operations": """#!/bin/bash
# Batch script for multiple operations

BASE_URL="http://localhost:8000"

echo "Checking system health..."
curl -s "$BASE_URL/api/v1/health" | jq '.status'

echo "Getting Q1 2024 summary..."
curl -s "$BASE_URL/api/v1/financial-data/2024-Q1" | jq '{total_revenue, total_expenses, net_profit}'

echo "Asking about trends..."
curl -s -X POST "$BASE_URL/api/v1/query" \\
     -H "Content-Type: application/json" \\
     -d '{"query": "Show me the revenue trend for 2024"}' \\
     | jq '.answer'
"""
            }
        )
    ]
    
    return guides


@router.get("/api-reference", response_class=HTMLResponse)
async def get_api_reference() -> str:
    """
    Get comprehensive API reference documentation in HTML format.
    
    Returns a detailed HTML page with complete API documentation,
    including all endpoints, parameters, and response formats.
    
    Returns:
        HTML documentation page
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Financial Data System - API Reference</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background: #f8f9fa; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            h2 { color: #34495e; margin-top: 30px; }
            h3 { color: #7f8c8d; }
            .endpoint { background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 15px 0; }
            .method { display: inline-block; padding: 4px 8px; border-radius: 3px; color: white; font-weight: bold; margin-right: 10px; }
            .get { background: #27ae60; }
            .post { background: #e74c3c; }
            .put { background: #f39c12; }
            .delete { background: #e67e22; }
            code { background: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-family: 'Monaco', 'Consolas', monospace; }
            pre { background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 5px; overflow-x: auto; }
            .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 20px 0; }
            .feature-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #3498db; }
            .toc { background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }
            .toc ul { list-style-type: none; padding-left: 0; }
            .toc li { margin: 5px 0; }
            .toc a { text-decoration: none; color: #3498db; }
            .toc a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 AI Financial Data System - API Reference</h1>
            
            <div class="toc">
                <h3>📋 Table of Contents</h3>
                <ul>
                    <li><a href="#overview">Overview</a></li>
                    <li><a href="#authentication">Authentication</a></li>
                    <li><a href="#endpoints">API Endpoints</a></li>
                    <li><a href="#examples">Usage Examples</a></li>
                    <li><a href="#errors">Error Handling</a></li>
                    <li><a href="#rate-limits">Rate Limits</a></li>
                </ul>
            </div>
            
            <h2 id="overview">🎯 Overview</h2>
            <p>The AI Financial Data System provides a comprehensive RESTful API for processing, analyzing, and querying financial data from multiple sources. The system combines traditional data access with AI-powered natural language processing and intelligent insights generation.</p>
            
            <div class="feature-grid">
                <div class="feature-card">
                    <h3>📊 Multi-Source Integration</h3>
                    <p>Seamlessly process QuickBooks and Rootfi financial data into a unified format.</p>
                </div>
                <div class="feature-card">
                    <h3>🗣️ Natural Language Queries</h3>
                    <p>Ask questions about your financial data in plain English and get intelligent responses.</p>
                </div>
                <div class="feature-card">
                    <h3>🧠 AI-Powered Insights</h3>
                    <p>Generate automated insights, trends analysis, and business recommendations.</p>
                </div>
                <div class="feature-card">
                    <h3>⚡ Real-time Monitoring</h3>
                    <p>Comprehensive health checks and performance monitoring for production use.</p>
                </div>
            </div>
            
            <h2 id="authentication">🔐 Authentication</h2>
            <p>Currently, this API does not require authentication. In production environments, implement appropriate authentication mechanisms such as API keys, OAuth 2.0, or JWT tokens.</p>
            
            <h2 id="endpoints">🛠️ API Endpoints</h2>
            
            <h3>Health & Monitoring</h3>
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/health</code>
                <p>Comprehensive system health check including database and AI services.</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/metrics</code>
                <p>Detailed system metrics, performance data, and active alerts.</p>
            </div>
            
            <h3>Financial Data</h3>
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/financial-data</code>
                <p>Retrieve financial records with filtering, pagination, and sorting options.</p>
                <p><strong>Parameters:</strong> page, page_size, source, period_start, period_end, currency, min_revenue, max_revenue, sort_by, sort_order</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/financial-data/{period}</code>
                <p>Get aggregated financial data for a specific period (YYYY-MM, YYYY-Q1, or YYYY).</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/accounts</code>
                <p>Retrieve account information with hierarchical relationships.</p>
            </div>
            
            <h3>Natural Language Processing</h3>
            <div class="endpoint">
                <span class="method post">POST</span><code>/api/v1/query</code>
                <p>Process natural language queries about financial data using AI.</p>
                <p><strong>Body:</strong> {"query": "What was the profit in Q1?", "conversation_id": "optional"}</p>
            </div>
            
            <h3>AI Insights</h3>
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/insights/revenue-trends</code>
                <p>Generate AI insights about revenue trends for a specified period.</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/insights/expense-analysis</code>
                <p>Analyze expense patterns and provide cost management recommendations.</p>
            </div>
            
            <div class="endpoint">
                <span class="method get">GET</span><code>/api/v1/insights/seasonal-patterns</code>
                <p>Identify seasonal patterns in financial metrics across multiple years.</p>
            </div>
            
            <h3>Data Ingestion</h3>
            <div class="endpoint">
                <span class="method post">POST</span><code>/api/v1/data/ingest</code>
                <p>Ingest financial data from JSON files with validation and processing.</p>
            </div>
            
            <h2 id="examples">💡 Usage Examples</h2>
            
            <h3>Basic Data Retrieval</h3>
            <pre><code>curl -X GET "http://localhost:8000/api/v1/financial-data?source=quickbooks&page=1&page_size=10" \\
     -H "Accept: application/json"</code></pre>
            
            <h3>Natural Language Query</h3>
            <pre><code>curl -X POST "http://localhost:8000/api/v1/query" \\
     -H "Content-Type: application/json" \\
     -d '{"query": "What was the total revenue in Q1 2024?"}'</code></pre>
            
            <h3>Generate Insights</h3>
            <pre><code>curl -X GET "http://localhost:8000/api/v1/insights/revenue-trends?start_date=2024-01-01&end_date=2024-06-30" \\
     -H "Accept: application/json"</code></pre>
            
            <h2 id="errors">⚠️ Error Handling</h2>
            <p>The API uses standard HTTP status codes and returns detailed error information:</p>
            <ul>
                <li><strong>200</strong> - Success</li>
                <li><strong>400</strong> - Bad Request (invalid parameters)</li>
                <li><strong>404</strong> - Not Found</li>
                <li><strong>422</strong> - Unprocessable Entity (validation errors)</li>
                <li><strong>500</strong> - Internal Server Error</li>
                <li><strong>503</strong> - Service Unavailable (AI service issues)</li>
            </ul>
            
            <h3>Error Response Format</h3>
            <pre><code>{
  "error": "validation_error",
  "message": "Invalid date format",
  "details": {
    "field": "start_date",
    "expected_format": "YYYY-MM-DD"
  }
}</code></pre>
            
            <h2 id="rate-limits">🚦 Rate Limits</h2>
            <p>The API implements intelligent rate limiting based on endpoint complexity:</p>
            <ul>
                <li><strong>Data endpoints:</strong> 100 requests per minute</li>
                <li><strong>AI queries:</strong> 20 requests per minute</li>
                <li><strong>Insights generation:</strong> 10 requests per minute</li>
                <li><strong>Health checks:</strong> Unlimited</li>
            </ul>
            
            <p>Rate limit headers are included in responses:</p>
            <pre><code>X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200</code></pre>
            
            <hr style="margin: 40px 0;">
            <p style="text-align: center; color: #7f8c8d;">
                📚 For more detailed information, visit the interactive API documentation at 
                <a href="/docs" style="color: #3498db;">/docs</a> or 
                <a href="/redoc" style="color: #3498db;">/redoc</a>
            </p>
        </div>
    </body>
    </html>
    """
    
    return html_content