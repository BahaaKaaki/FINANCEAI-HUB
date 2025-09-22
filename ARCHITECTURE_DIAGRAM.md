# AI Financial Data System - Architecture Diagram

## Complete System Architecture

```mermaid
graph TB
    subgraph "External Data Sources"
        QB[QuickBooks<br/>data_set_1.json<br/>P&L Format]
        RF[RootFi<br/>data_set_2.json<br/>Transaction Format]
    end
    
    subgraph "API Gateway Layer"
        API[FastAPI Application<br/>Port 8000<br/>Auto-Generated Docs]
        
        subgraph "Core API Endpoints"
            QUERY[ /api/v1/query<br/>Natural Language AI<br/>POST - Main Feature]
            DATA[ /api/v1/financial-data<br/>Structured Data Access<br/>GET - Data Retrieval]
            INGEST[ /api/v1/ingestion<br/>Data Processing<br/>POST - File Upload]
            HEALTH[ /api/v1/health<br/>System Monitoring<br/>GET - Health Checks]
            INSIGHTS[ /api/v1/insights<br/>AI Analytics<br/>GET - Optional Feature]
        end
    end
    
    subgraph "AI Engine Core"
        LLM[LLM Client<br/>Multi-Provider Support<br/>OpenAI • Anthropic • Groq]
        AGENT[Financial Agent<br/>Query Orchestration<br/>Tool Selection & Execution]
        TOOLS[AI Tools Registry<br/>13 Financial Tools<br/>Revenue • Expenses • Trends]
        CONV[Conversation Manager<br/>Context Handling<br/>Multi-turn Conversations]
    end
    
    subgraph "Data Processing Pipeline"
        PARSERS[Data Parsers<br/>QB Parser • RootFi Parser<br/>Format Detection]
        VALIDATOR[Data Validation<br/>Quality Scoring<br/>Error Detection]
        NORMALIZER[Data Normalizer<br/>Unified Schema<br/>Conflict Resolution]
    end
    
    subgraph "Business Logic Services"
        INGESTION_SVC[Ingestion Service<br/>File Processing<br/>Batch Operations]
        INSIGHTS_SVC[Insights Service<br/>AI Analytics<br/>Trend Analysis]
    end
    
    subgraph "Data Storage Layer"
        DB[(SQLite Database<br/>financial_data.db)]
        
        subgraph "Database Tables"
            RECORDS[financial_records<br/>Unified Financial Data]
            ACCOUNTS[accounts<br/>Account Hierarchies]
            VALUES[account_values<br/>Time-series Values]
        end
    end
    
    subgraph "Infrastructure & Monitoring"
        MIDDLEWARE[Middleware Stack<br/>CORS • Monitoring • Security]
        LOGGING[Logging System<br/>Structured Logs<br/>Performance Metrics]
        CONFIG[Configuration<br/>Environment Variables<br/>LLM Provider Settings]
    end
    
    %% Data Flow - Ingestion Path
    QB --> INGEST
    RF --> INGEST
    INGEST --> INGESTION_SVC
    INGESTION_SVC --> PARSERS
    PARSERS --> VALIDATOR
    VALIDATOR --> NORMALIZER
    NORMALIZER --> DB
    DB --> RECORDS
    DB --> ACCOUNTS
    DB --> VALUES
    
    %% API Flow - Request Handling
    API --> QUERY
    API --> DATA
    API --> INGEST
    API --> HEALTH
    API --> INSIGHTS
    API --> MIDDLEWARE
    MIDDLEWARE --> LOGGING
    
    %% AI Flow - Natural Language Processing
    QUERY --> AGENT
    AGENT --> LLM
    AGENT --> TOOLS
    AGENT --> CONV
    TOOLS --> RECORDS
    TOOLS --> ACCOUNTS
    TOOLS --> VALUES
    
    %% Service Integration
    DATA --> RECORDS
    DATA --> ACCOUNTS
    INSIGHTS --> INSIGHTS_SVC
    INSIGHTS_SVC --> TOOLS
    
    %% Configuration Flow
    CONFIG --> LLM
    CONFIG --> API
    CONFIG --> DB
    
    %% Styling
    classDef ai fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef data fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef api fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef storage fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef infra fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    
    class LLM,AGENT,TOOLS,CONV,QUERY,INSIGHTS ai
    class QB,RF,PARSERS,VALIDATOR,NORMALIZER data
    class API,DATA,INGEST,HEALTH api
    class DB,RECORDS,ACCOUNTS,VALUES storage
    class MIDDLEWARE,LOGGING,CONFIG infra
```

## Data Flow Explanation

### **1. Data Ingestion Flow**
```
QuickBooks/RootFi JSON → Ingestion API → Parser → Validator → Normalizer → Database
```

### **2. Natural Language Query Flow**
```
User Query → API → Financial Agent → LLM + Tools → Database → AI Response
```

### **3. Structured Data Access Flow**
```
API Request → Financial Data Endpoint → Database Query → Formatted Response
```

### **4. AI Insights Generation Flow**
```
Insights Request → Insights Service → AI Tools → Data Analysis → Generated Insights
```

## Key Architectural Decisions

### **AI-First Design**
- Natural language querying as the primary interface
- LLM integration with specialized financial tools
- Context-aware conversation management

### **Multi-Provider LLM Support**
- Flexible backend supporting OpenAI, Anthropic, and Groq
- Provider-agnostic tool calling interface
- Graceful fallback and error handling

### **Modular Data Processing**
- Separate parsers for each data source format
- Validation layer for data quality assurance
- Normalization for unified data representation

### **Production-Ready Architecture**
- Error handling and logging
- Health monitoring and performance metrics
- Scalable database design with proper indexing

## Component Responsibilities

| Component | Responsibility | Key Features |
|-----------|---------------|--------------|
| **Financial Agent** | Query orchestration and tool selection | Context awareness, multi-turn conversations |
| **LLM Client** | AI provider abstraction | Multi-provider support, error handling |
| **AI Tools Registry** | Financial analysis capabilities | 13 specialized tools, data access |
| **Data Parsers** | Source-specific data processing | QuickBooks P&L, RootFi transactions |
| **Validation Engine** | Data quality assurance | Quality scoring, error detection |
| **Ingestion Service** | File processing coordination | Batch operations, status tracking |

---