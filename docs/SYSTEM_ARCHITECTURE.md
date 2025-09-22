# System Architecture Documentation

## Overview

The AI Financial Data System is a comprehensive platform built with modern Python technologies, designed for scalability, maintainability, and intelligent financial data processing. The system follows a modular architecture with clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AI Financial Data System                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   FastAPI App   │  │   AI Agent      │  │   Insights      │             │
│  │                 │  │                 │  │   Generator     │             │
│  │ • REST API      │  │ • Natural Lang  │  │                 │             │
│  │ • Endpoints     │  │ • Tool Calling  │  │ • Revenue       │             │
│  │ • Validation    │  │ • Conversation  │  │ • Expenses      │             │
│  │ • Middleware    │  │ • Multi-turn    │  │ • Cash Flow     │             │
│  └─────────────────┘  └─────────────────┘  │ • Seasonal      │             │
│                                            └─────────────────┘             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   Data Layer    │  │   Services      │  │   AI Tools      │             │
│  │                 │  │                 │  │                 │             │
│  │ • SQLAlchemy    │  │ • Ingestion     │  │ • Revenue       │             │
│  │ • Models        │  │ • Validation    │  │ • Comparison    │             │
│  │ • Migrations    │  │ • Normalization │  │ • Growth        │             │
│  │ • Connection    │  │ • Insights      │  │ • Anomaly       │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │   Parsers       │  │   Core Utils    │  │   Monitoring    │             │
│  │                 │  │                 │  │                 │             │
│  │ • QuickBooks    │  │ • Config        │  │ • Health        │             │
│  │ • Rootfi        │  │ • Logging       │  │ • Metrics       │             │
│  │ • Auto-detect   │  │ • Security      │  │ • Performance   │             │
│  │ • Validation    │  │ • Middleware    │  │ • Alerts        │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. FastAPI Application Layer (`app/main.py`)

**Responsibilities:**
- HTTP request/response handling
- API endpoint routing
- Middleware management
- Application lifecycle management
- CORS and security headers

**Key Features:**
- Async/await support for high performance
- Automatic OpenAPI documentation generation
- Request validation with Pydantic
- Comprehensive error handling
- Health monitoring integration

### 2. API Endpoints (`app/api/`)

#### Health & Monitoring (`app/api/health.py`)
- System health checks
- Performance metrics
- Database connectivity monitoring
- AI service status validation

#### Data Ingestion (`app/api/ingestion.py`)
- File upload and processing
- Batch ingestion operations
- Status tracking and monitoring
- Error reporting and recovery

#### Financial Data (`app/api/financial_data.py`)
- Financial record retrieval
- Advanced filtering and pagination
- Period-based analysis
- Account hierarchy management

#### Natural Language Query (`app/api/query.py`)
- Natural language processing
- AI agent integration
- Conversation management
- Multi-turn query support

#### AI Insights (`app/api/insights.py`)
- Revenue trend analysis
- Expense pattern analysis
- Cash flow insights
- Seasonal pattern detection

#### AI Agent Tools (`app/api/ai_agent.py`)
- Direct tool access
- Tool registry management
- Agent status monitoring
- Conversation handling

### 3. AI System (`app/ai/`)

#### Core AI Components
- **Agent (`agent.py`)**: Main AI orchestrator with tool calling
- **LLM Client (`llm_client.py`)**: Multi-provider LLM integration
- **Conversation (`conversation.py`)**: Context management and history
- **Registry (`registry.py`)**: Tool discovery and execution

#### AI Tools (`app/ai/tools/`)
- **Revenue Tools**: Revenue analysis and reporting
- **Comparison Tools**: Period-over-period comparisons
- **Growth Tools**: Growth rate calculations and trends
- **Anomaly Tools**: Statistical anomaly detection
- **Insight Tools**: AI-powered insight generation

#### LLM Providers (`app/ai/providers/`)
- **OpenAI Provider**: GPT-4 and GPT-3.5 integration
- **Anthropic Provider**: Claude model support
- **Groq Provider**: Fast inference with open models
- **Base Provider**: Abstract interface for extensibility

### 4. Data Processing Layer

#### Parsers (`app/parsers/`)
- **QuickBooks Parser**: P&L JSON format processing
- **Rootfi Parser**: Hierarchical financial data parsing
- **Auto-detection**: Intelligent source type identification
- **Validation**: Data integrity and format validation

#### Services (`app/services/`)
- **Ingestion Service**: Orchestrates data processing pipeline
- **Validation Service**: Comprehensive data quality checks
- **Normalization Service**: Unified data model conversion
- **Insights Service**: AI-powered insight generation

#### Database Layer (`app/database/`)
- **Models**: SQLAlchemy ORM models
- **Connection**: Database connection management
- **Migrations**: Schema version control
- **Initialization**: Database setup and seeding

### 5. Core Infrastructure (`app/core/`)

#### Configuration (`config.py`)
- Environment-based configuration
- LLM provider settings
- Database configuration
- Security and performance settings

#### Logging (`logging.py`)
- Structured JSON logging
- Multiple log levels and handlers
- Request tracing and correlation
- Performance monitoring integration

#### Middleware (`middleware.py`)
- Request monitoring and metrics
- Error handling and recovery
- Performance tracking
- Security headers and CORS

#### Monitoring (`monitoring.py`)
- Health check framework
- Performance metrics collection
- System status tracking
- Alert generation

## Data Flow Architecture

### 1. Data Ingestion Flow

```
File Upload → Auto-Detection → Parser Selection → Data Extraction → 
Validation → Normalization → Database Storage → Status Update
```

**Detailed Steps:**
1. **File Reception**: API receives file via upload or file path
2. **Source Detection**: Analyzes file structure to determine QuickBooks vs Rootfi
3. **Parser Invocation**: Routes to appropriate parser (QuickBooks/Rootfi)
4. **Data Extraction**: Extracts financial records, accounts, and values
5. **Validation**: Runs comprehensive validation rules and quality scoring
6. **Normalization**: Converts to unified data models
7. **Conflict Resolution**: Handles duplicate data from multiple sources
8. **Database Storage**: Persists normalized data with audit trails
9. **Status Reporting**: Updates processing status and metrics

### 2. Query Processing Flow

```
Natural Language Query → AI Agent → Tool Selection → Data Retrieval → 
AI Analysis → Response Generation → Conversation Update
```

**Detailed Steps:**
1. **Query Reception**: API receives natural language query
2. **Context Loading**: Retrieves conversation history if available
3. **AI Processing**: LLM analyzes query and determines required tools
4. **Tool Execution**: Executes selected financial analysis tools
5. **Data Analysis**: AI processes tool results and generates insights
6. **Response Formatting**: Creates structured response with data and narrative
7. **Conversation Update**: Saves context for follow-up queries

### 3. Insights Generation Flow

```
Data Query → Pattern Analysis → AI Processing → Insight Generation → 
Recommendation Creation → Response Formatting → Caching
```

**Detailed Steps:**
1. **Data Retrieval**: Queries financial data based on parameters
2. **Pattern Detection**: Identifies trends, anomalies, and patterns
3. **AI Analysis**: LLM processes patterns and generates insights
4. **Narrative Creation**: Generates human-readable analysis
5. **Recommendation Generation**: Creates actionable business recommendations
6. **Response Assembly**: Combines insights, data, and recommendations
7. **Caching**: Stores results for performance optimization

## Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework with automatic API documentation
- **Uvicorn**: ASGI server for high-performance async applications
- **Pydantic**: Data validation and serialization with type hints

### Database & ORM
- **SQLAlchemy**: Powerful ORM with async support
- **SQLite**: Development database (easily replaceable with PostgreSQL)
- **Alembic**: Database migration management

### AI & Machine Learning
- **OpenAI API**: GPT-4 and GPT-3.5 for natural language processing
- **Anthropic API**: Claude models for advanced reasoning
- **Groq API**: Fast inference for open-source models

### Data Processing
- **Pandas**: Data manipulation and analysis
- **Decimal**: Precise financial calculations
- **JSON**: Native JSON processing for financial data formats

### Monitoring & Observability
- **Structured Logging**: JSON-formatted logs with correlation IDs
- **Health Checks**: Comprehensive system health monitoring
- **Performance Metrics**: Request timing and system resource tracking
- **Error Tracking**: Detailed error logging and recovery

### Development & Testing
- **Pytest**: Comprehensive test suite with async support
- **HTTPx**: Async HTTP client for testing
- **Black**: Code formatting
- **Type Hints**: Full type annotation coverage

## Security Architecture

### API Security
- **Input Validation**: Pydantic models validate all inputs
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Configurable cross-origin resource sharing
- **Security Headers**: Comprehensive security header middleware

### Data Security
- **Environment Variables**: Sensitive configuration in environment
- **API Key Management**: Secure storage of LLM provider keys
- **Data Sanitization**: Input sanitization and output encoding
- **Audit Trails**: Complete logging of data access and modifications

### Infrastructure Security
- **Error Handling**: Secure error messages without sensitive data exposure
- **Rate Limiting**: Configurable request rate limiting (planned)
- **Authentication**: Extensible authentication framework (planned)
- **Authorization**: Role-based access control (planned)

## Performance Architecture

### Scalability Features
- **Async Processing**: Non-blocking I/O for high concurrency
- **Connection Pooling**: Efficient database connection management
- **Caching**: Intelligent caching for insights and frequently accessed data
- **Batch Processing**: Efficient handling of multiple file processing

### Performance Optimizations
- **Database Indexing**: Optimized queries with proper indexing
- **Lazy Loading**: Efficient data loading strategies
- **Response Compression**: Automatic response compression
- **Request Monitoring**: Performance tracking and optimization

### Resource Management
- **Memory Efficiency**: Streaming processing for large files
- **CPU Optimization**: Efficient algorithms and data structures
- **I/O Optimization**: Async file operations and database queries
- **Garbage Collection**: Proper resource cleanup and management

## Deployment Architecture

### Development Environment
- **Local Development**: SQLite database with hot reload
- **Environment Configuration**: `.env` file for local settings
- **Debug Mode**: Enhanced logging and error reporting
- **Test Suite**: Comprehensive testing with coverage reporting

### Production Considerations
- **Database**: PostgreSQL for production workloads
- **Container Support**: Docker containerization ready
- **Load Balancing**: Horizontal scaling support
- **Monitoring**: Production monitoring and alerting integration

### Configuration Management
- **Environment-based**: Different configs for dev/staging/production
- **Secret Management**: Secure handling of API keys and credentials
- **Feature Flags**: Configurable feature enablement
- **Health Checks**: Comprehensive health monitoring for deployment

## Extension Points

### Adding New Data Sources
1. Create parser in `app/parsers/`
2. Implement data extraction logic
3. Add validation rules
4. Update auto-detection logic
5. Add tests and documentation

### Adding New AI Tools
1. Create tool function in `app/ai/tools/`
2. Define tool schema
3. Register in tool registry
4. Add to AI agent system prompt
5. Test with AI agent integration

### Adding New LLM Providers
1. Implement provider class in `app/ai/providers/`
2. Add configuration settings
3. Update LLM client routing
4. Add provider-specific optimizations
5. Test with existing tools

### Adding New Insights
1. Create insight generation logic in `app/services/insights.py`
2. Add API endpoint in `app/api/insights.py`
3. Create AI tool wrapper if needed
4. Add caching and performance optimization
5. Document and test new insights

This architecture provides a solid foundation for a scalable, maintainable, and extensible AI-powered financial data processing system.