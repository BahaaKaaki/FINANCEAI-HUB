# Data Ingestion Service Documentation

## Overview

The Data Ingestion Service is a comprehensive system for orchestrating the parsing, validation, and storage of financial data from multiple sources (QuickBooks and Rootfi). It provides both programmatic APIs and service-level interfaces for batch processing, error handling, and status tracking.

## Features

### Core Capabilities
- **Multi-source Support**: Handles QuickBooks P&L and Rootfi financial data formats
- **Batch Processing**: Process multiple files simultaneously with parallel execution
- **Auto-detection**: Automatically detects source type based on file content and naming
- **Comprehensive Validation**: Data quality scoring and validation with detailed issue reporting
- **Error Recovery**: Robust error handling with detailed logging and recovery mechanisms
- **Status Tracking**: Real-time status tracking for all ingestion operations
- **Audit Trail**: Complete audit trail with ingestion logs and processing history

### API Endpoints
- **File Ingestion**: `/api/v1/ingestion/file` - Ingest single files
- **Batch Ingestion**: `/api/v1/ingestion/batch` - Process multiple files
- **Async Batch**: `/api/v1/ingestion/batch/async` - Background batch processing
- **File Upload**: `/api/v1/ingestion/upload` - Upload and process files
- **Status Tracking**: `/api/v1/ingestion/status` - Get processing status
- **Health Check**: `/api/v1/ingestion/health` - Service health monitoring

## Architecture

### Service Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Data Ingestion Service                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │   File Parser   │  │   Validator     │  │  Database    │ │
│  │                 │  │                 │  │  Storage     │ │
│  │ • QuickBooks    │  │ • Data Quality  │  │              │ │
│  │ • Rootfi        │  │ • Validation    │  │ • Records    │ │
│  │ • Auto-detect   │  │ • Conflict Res. │  │ • Accounts   │ │
│  └─────────────────┘  └─────────────────┘  │ • Values     │ │
│                                            │ • Audit Logs │ │
│  ┌─────────────────┐  ┌─────────────────┐  └──────────────┘ │
│  │ Error Handler   │  │ Status Tracker  │                   │
│  │                 │  │                 │                   │
│  │ • Retry Logic   │  │ • Progress      │                   │
│  │ • Logging       │  │ • History       │                   │
│  │ • Recovery      │  │ • Monitoring    │                   │
│  └─────────────────┘  └─────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Input**: Files (JSON) from QuickBooks or Rootfi
2. **Detection**: Auto-detect source type or use provided type
3. **Parsing**: Extract financial records, accounts, and values
4. **Validation**: Comprehensive data quality checks
5. **Storage**: Store in unified database schema
6. **Logging**: Record processing details and audit trail

## Usage Examples

### 1. Single File Ingestion

```python
from app.services.ingestion import DataIngestionService
from app.models.financial import SourceType

# Initialize service
ingestion_service = DataIngestionService()

# Ingest a single file
result = ingestion_service.ingest_file(
    file_path="data_set_1.json",
    source_type=SourceType.QUICKBOOKS  # Optional, auto-detected if not provided
)

print(f"Status: {result.status}")
print(f"Records processed: {result.records_processed}")
print(f"Records created: {result.records_created}")
print(f"Duration: {result.processing_duration_seconds:.2f}s")
```

### 2. Batch Processing

```python
# Process multiple files
file_paths = ["data_set_1.json", "data_set_2.json"]
source_types = [SourceType.QUICKBOOKS, SourceType.ROOTFI]

batch_result = ingestion_service.ingest_batch(file_paths, source_types)

print(f"Batch ID: {batch_result.batch_id}")
print(f"Files successful: {batch_result.files_successful}")
print(f"Files failed: {batch_result.files_failed}")
print(f"Total records: {batch_result.total_records_processed}")
```

### 3. API Usage

```bash
# Single file ingestion
curl -X POST "http://localhost:8000/api/v1/ingestion/file" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "data_set_1.json",
    "source_type": "quickbooks"
  }'

# Batch ingestion
curl -X POST "http://localhost:8000/api/v1/ingestion/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": ["data_set_1.json", "data_set_2.json"],
    "source_types": ["quickbooks", "rootfi"]
  }'

# Check status
curl -X GET "http://localhost:8000/api/v1/ingestion/status"

# Health check
curl -X GET "http://localhost:8000/api/v1/ingestion/health"
```

### 4. File Upload

```bash
# Upload and process file
curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
  -F "file=@data_set_1.json" \
  -F "source_type=quickbooks"
```

## Response Models

### FileProcessingResult

```json
{
  "filename": "data_set_1.json",
  "source_type": "quickbooks",
  "status": "completed",
  "records_processed": 68,
  "records_created": 68,
  "records_updated": 0,
  "validation_result": {
    "is_valid": true,
    "quality_score": 1.0,
    "issues": []
  },
  "error_message": null,
  "processing_duration_seconds": 0.13
}
```

### BatchIngestionResult

```json
{
  "batch_id": "8c532afb-8cff-4fde-8ed8-4cece3ad5f2e",
  "status": "completed",
  "files_processed": 2,
  "files_successful": 2,
  "files_failed": 0,
  "total_records_processed": 104,
  "total_records_created": 104,
  "total_records_updated": 0,
  "file_results": [...],
  "started_at": "2024-01-01T00:00:00Z",
  "completed_at": "2024-01-01T00:00:20Z",
  "processing_duration_seconds": 0.20,
  "error_summary": null
}
```

## Status Values

### IngestionStatus Enum
- `PENDING`: Operation queued but not started
- `PROCESSING`: Currently being processed
- `COMPLETED`: Successfully completed
- `FAILED`: Failed with errors
- `PARTIALLY_COMPLETED`: Some files succeeded, others failed

## Error Handling

### Error Categories

1. **Parsing Errors**: Invalid file format or structure
2. **Validation Errors**: Data quality issues or constraint violations
3. **Database Errors**: Storage or connection issues
4. **File System Errors**: File access or permission issues
5. **Configuration Errors**: Missing settings or invalid configuration

### Error Recovery

- **Retry Logic**: Automatic retry with exponential backoff for transient errors
- **Partial Success**: Continue processing other files if one fails in batch
- **Detailed Logging**: Comprehensive error logging with context
- **Graceful Degradation**: Service continues operating even with some failures

### Error Response Format

```json
{
  "status": "failed",
  "error_message": "Parsing error: Invalid JSON structure",
  "validation_result": {
    "is_valid": false,
    "quality_score": 0.0,
    "issues": [
      {
        "severity": "error",
        "code": "INVALID_JSON",
        "message": "File contains invalid JSON syntax",
        "field": null,
        "suggestion": "Verify file format and structure"
      }
    ]
  }
}
```

## Validation and Quality Scoring

### Validation Checks

1. **Financial Accuracy**
   - No negative revenue (unless justified)
   - No negative expenses (unless justified)
   - Reasonable value ranges

2. **Date Consistency**
   - Period end after period start
   - No future dates (configurable)
   - Chronological order

3. **Balance Equations**
   - Net profit = Revenue - Expenses
   - Account value totals match record totals

4. **Data Integrity**
   - Valid currency codes
   - Account hierarchy consistency
   - No circular references

### Quality Scoring

Quality scores range from 0.0 (worst) to 1.0 (perfect):

- **1.0**: No issues found
- **0.8-0.9**: Minor warnings only
- **0.5-0.7**: Some validation issues
- **0.0-0.4**: Critical errors present

## Performance Characteristics

### Throughput
- **Single File**: ~100-500 records/second (depending on complexity)
- **Batch Processing**: Parallel processing of multiple files
- **Memory Usage**: Efficient streaming for large files

### Scalability
- **Horizontal**: Multiple service instances supported
- **Vertical**: Efficient memory and CPU usage
- **Database**: Connection pooling and optimization

## Monitoring and Observability

### Logging
- **Structured Logging**: JSON format with consistent fields
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Context**: Request IDs, user context, operation traces

### Metrics
- Processing duration per file
- Success/failure rates
- Records processed per minute
- Error frequency by type

### Health Checks
- Database connectivity
- File system access
- Service dependencies
- Resource utilization

## Configuration

### Environment Variables

```bash
# Database settings
DATABASE_URL=sqlite:///./financial_data.db
DATABASE_ECHO=false
DATABASE_POOL_SIZE=20

# Logging
LOG_LEVEL=INFO

# Performance
MAX_CONCURRENT_REQUESTS=100
REQUEST_TIMEOUT=30

# Validation
DECIMAL_PRECISION_TOLERANCE=0.01
```

### Settings File

```python
# app/core/config.py
class Settings(BaseSettings):
    # Database configuration
    database_url: str = "sqlite:///./financial_data.db"
    database_pool_size: int = 20
    
    # Validation settings
    DECIMAL_PRECISION_TOLERANCE: str = "0.01"
    MAX_CURRENCY_CODE_LENGTH: int = 3
    
    # Performance settings
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT: int = 30
```

## Testing

### Unit Tests
```bash
# Run ingestion service tests
python test_ingestion.py

# Run API endpoint tests
python test_ingestion_api.py
```

### Integration Tests
```bash
# Start the FastAPI server
uvicorn app.main:app --reload

# Test with real data files
curl -X POST "http://localhost:8000/api/v1/ingestion/file" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "data_set_1.json"}'
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations
- Use PostgreSQL instead of SQLite for production
- Implement proper authentication and authorization
- Set up monitoring and alerting
- Configure load balancing for multiple instances
- Implement rate limiting and request throttling

## Troubleshooting

### Common Issues

1. **File Not Found**
   - Verify file path is correct
   - Check file permissions
   - Ensure file exists and is readable

2. **Parsing Errors**
   - Validate JSON syntax
   - Check file format matches expected structure
   - Verify encoding (UTF-8 expected)

3. **Database Errors**
   - Check database connection
   - Verify database schema is up to date
   - Check disk space and permissions

4. **Validation Failures**
   - Review validation error details
   - Check data quality and consistency
   - Verify business rules are met

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
# Set log level to DEBUG
LOG_LEVEL=DEBUG

# Enable database query logging
DATABASE_ECHO=true
```

## Future Enhancements

### Planned Features
- **Real-time Processing**: WebSocket support for real-time status updates
- **Data Transformation**: Custom transformation rules and mappings
- **Advanced Validation**: Machine learning-based anomaly detection
- **Multi-tenant Support**: Tenant isolation and data segregation
- **API Rate Limiting**: Request throttling and quota management
- **Caching Layer**: Redis integration for improved performance

### Extensibility
- **Custom Parsers**: Plugin architecture for new data sources
- **Validation Rules**: Configurable business rules and constraints
- **Output Formats**: Support for multiple output formats (CSV, Excel, etc.)
- **Integration Hooks**: Webhooks and event-driven processing