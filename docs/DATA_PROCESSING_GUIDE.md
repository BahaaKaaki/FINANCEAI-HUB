# Data Processing Guide

## Overview

The AI Financial Data System provides comprehensive data processing capabilities for financial data from multiple sources. This guide covers the complete data processing pipeline from ingestion to analysis.

## Supported Data Sources

### QuickBooks P&L Reports
- **Format**: JSON export from QuickBooks P&L reports
- **Structure**: Hierarchical account structure with monthly columns
- **Features**: Multi-period data, account hierarchies, automatic classification
- **Sample Data**: `data_set_1.json`

### Rootfi Financial Data
- **Format**: JSON export from Rootfi platform
- **Structure**: Period-based records with nested line items
- **Features**: Multi-category financial data, hierarchical accounts
- **Sample Data**: `data_set_2.json`

## Data Processing Pipeline

### 1. Data Ingestion

#### Automatic Source Detection
The system automatically detects data source type based on:
- File structure analysis
- Key field presence
- Data format patterns
- Filename conventions

```python
from app.services.ingestion import DataIngestionService

service = DataIngestionService()

# Auto-detection (recommended)
result = service.ingest_file("financial_data.json")

# Explicit source type
result = service.ingest_file("data.json", source_type="quickbooks")
```

#### Batch Processing
Process multiple files simultaneously:

```python
# Batch with auto-detection
files = ["quickbooks_data.json", "rootfi_data.json"]
batch_result = service.ingest_batch(files)

# Batch with explicit types
files = ["data1.json", "data2.json"]
types = ["quickbooks", "rootfi"]
batch_result = service.ingest_batch(files, types)
```

### 2. Data Parsing

#### QuickBooks Parser (`app/parsers/quickbooks_parser.py`)

**Data Structure Processing:**
```json
{
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
```

**Parsing Features:**
- Hierarchical account extraction
- Monthly column processing
- Automatic account type classification
- Financial calculation validation

#### Rootfi Parser (`app/parsers/rootfi_parser.py`)

**Data Structure Processing:**
```json
{
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
            {
              "name": "Consulting",
              "value": 15000.00
            }
          ]
        }
      ],
      "operating_expenses": [
        {
          "name": "Office Expenses",
          "value": 5000.00
        }
      ]
    }
  ]
}
```

**Parsing Features:**
- Period-based record processing
- Multi-category financial data
- Nested line item handling
- Account ID generation

### 3. Data Validation

#### Validation Rules (`app/services/validation.py`)

**Financial Accuracy:**
- Negative revenue detection
- Negative expense validation
- Unusually high amount flagging
- Balance equation verification

**Date Consistency:**
- Period date range validation
- Future date detection
- Chronological order checking
- Date format validation

**Account Hierarchy:**
- Circular reference detection
- Missing parent validation
- Type consistency checking
- Self-reference prevention

**Data Quality:**
- Currency code validation
- Account value totals verification
- Missing data detection
- Format consistency checking

#### Quality Scoring System

Quality scores range from 0.0 to 1.0:
- **1.0**: Perfect data, no issues
- **0.8-0.9**: Minor warnings only
- **0.5-0.7**: Some validation issues
- **0.0-0.4**: Critical errors present

**Scoring Formula:**
```python
base_score = 1.0
for issue in validation_issues:
    if issue.severity == "INFO":
        base_score -= 0.05
    elif issue.severity == "WARNING":
        base_score -= 0.15
    elif issue.severity == "ERROR":
        base_score -= 0.35
    elif issue.severity == "CRITICAL":
        base_score -= 0.50

quality_score = max(0.0, base_score)
```

### 4. Data Normalization

#### Unified Data Models (`app/models/financial.py`)

**FinancialRecord:**
```python
class FinancialRecord(BaseModel):
    id: str
    source: SourceType
    period_start: date
    period_end: date
    currency: str
    revenue: Decimal
    expenses: Decimal
    net_profit: Decimal
    raw_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

**Account:**
```python
class Account(BaseModel):
    account_id: str
    name: str
    account_type: AccountType
    parent_account_id: Optional[str]
    source: SourceType
    description: Optional[str]
    is_active: bool
```

**AccountValue:**
```python
class AccountValue(BaseModel):
    account_id: str
    financial_record_id: str
    value: Decimal
```

#### Normalization Process

**QuickBooks Normalization:**
1. Extract header information (currency, basis)
2. Process column definitions for periods
3. Parse hierarchical row structure
4. Generate account IDs and classifications
5. Calculate financial totals
6. Create unified data models

**Rootfi Normalization:**
1. Process period records
2. Extract multi-category financial data
3. Handle nested line item structures
4. Generate or map account IDs
5. Aggregate financial totals
6. Create unified data models

### 5. Conflict Resolution

#### Multi-Source Data Handling

**Source Priority System:**
1. QuickBooks: Priority 2 (highest)
2. Rootfi: Priority 1

**Conflict Detection:**
- Revenue amount differences
- Expense amount differences
- Currency code conflicts
- Account structure variations

**Resolution Strategy:**
```python
def resolve_conflicts(records):
    conflicts = detect_conflicts(records)
    
    for conflict in conflicts:
        if conflict.type == "revenue_mismatch":
            # Use higher priority source
            resolved_value = get_highest_priority_value(conflict.values)
        elif conflict.type == "currency_conflict":
            # Use most common currency or highest priority
            resolved_currency = resolve_currency_conflict(conflict.currencies)
    
    return resolved_records
```

## Data Models and Schema

### Database Schema

```sql
-- Financial Records Table
CREATE TABLE financial_records (
    id VARCHAR PRIMARY KEY,
    source VARCHAR NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    currency VARCHAR(3) NOT NULL,
    revenue DECIMAL(15,2) NOT NULL,
    expenses DECIMAL(15,2) NOT NULL,
    net_profit DECIMAL(15,2) NOT NULL,
    raw_data JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Accounts Table
CREATE TABLE accounts (
    account_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    account_type VARCHAR NOT NULL,
    parent_account_id VARCHAR,
    source VARCHAR NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (parent_account_id) REFERENCES accounts(account_id)
);

-- Account Values Table
CREATE TABLE account_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id VARCHAR NOT NULL,
    financial_record_id VARCHAR NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (financial_record_id) REFERENCES financial_records(id)
);
```

### Indexes for Performance

```sql
-- Performance indexes
CREATE INDEX idx_financial_records_period ON financial_records(period_start, period_end);
CREATE INDEX idx_financial_records_source ON financial_records(source);
CREATE INDEX idx_accounts_type ON accounts(account_type);
CREATE INDEX idx_accounts_parent ON accounts(parent_account_id);
CREATE INDEX idx_account_values_record ON account_values(financial_record_id);
CREATE INDEX idx_account_values_account ON account_values(account_id);
```

## API Usage Examples

### Data Ingestion API

```bash
# Single file ingestion
curl -X POST "http://localhost:8000/api/v1/data/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "data_set_1.json",
    "source_type": "quickbooks"
  }'

# Batch ingestion
curl -X POST "http://localhost:8000/api/v1/data/ingest/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "file_paths": ["data_set_1.json", "data_set_2.json"],
    "source_types": ["quickbooks", "rootfi"]
  }'

# File upload
curl -X POST "http://localhost:8000/api/v1/data/upload" \
  -F "file=@financial_data.json" \
  -F "source_type=quickbooks"
```

### Data Retrieval API

```bash
# Get all financial records
curl -X GET "http://localhost:8000/api/v1/financial-data"

# Filter by source and date range
curl -X GET "http://localhost:8000/api/v1/financial-data?source=quickbooks&period_start=2024-01-01&period_end=2024-12-31"

# Get period summary
curl -X GET "http://localhost:8000/api/v1/financial-data/2024-Q1"

# Get accounts
curl -X GET "http://localhost:8000/api/v1/financial-data/accounts"

# Get account hierarchy
curl -X GET "http://localhost:8000/api/v1/financial-data/accounts/ACC_001/hierarchy"
```

## Python SDK Usage

### Direct Service Usage

```python
from app.services.ingestion import DataIngestionService
from app.services.validation import FinancialDataValidator
from app.services.normalizer import DataNormalizer

# Initialize services
ingestion_service = DataIngestionService()
validator = FinancialDataValidator()
normalizer = DataNormalizer()

# Process a file
result = ingestion_service.ingest_file("financial_data.json")

if result.status == "completed":
    print(f"Successfully processed {result.records_processed} records")
    print(f"Quality score: {result.validation_result.quality_score}")
else:
    print(f"Processing failed: {result.error_message}")
```

### Parser Usage

```python
from app.parsers.quickbooks_parser import parse_quickbooks_file
from app.parsers.rootfi_parser import parse_rootfi_file

# Parse QuickBooks data
qb_records, qb_accounts, qb_values = parse_quickbooks_file("quickbooks.json")

# Parse Rootfi data
rf_records, rf_accounts, rf_values = parse_rootfi_file("rootfi.json")

# Combine data from multiple sources
all_records = qb_records + rf_records
all_accounts = qb_accounts + rf_accounts
all_values = qb_values + rf_values
```

## Error Handling and Recovery

### Common Error Scenarios

**File Processing Errors:**
- Invalid JSON format
- Missing required fields
- Corrupted file data
- Unsupported file format

**Data Validation Errors:**
- Invalid date formats
- Negative financial values
- Missing account relationships
- Currency code issues

**Database Errors:**
- Connection failures
- Constraint violations
- Transaction rollbacks
- Storage capacity issues

### Error Recovery Strategies

**Graceful Degradation:**
```python
try:
    result = process_financial_data(file_path)
except ValidationError as e:
    # Continue with warnings, don't fail completely
    result = process_with_warnings(file_path, e.issues)
except DatabaseError as e:
    # Retry with exponential backoff
    result = retry_with_backoff(process_financial_data, file_path)
except Exception as e:
    # Log error and return structured error response
    logger.error(f"Unexpected error: {e}")
    result = create_error_result(str(e))
```

**Partial Processing:**
- Process valid records even if some fail
- Provide detailed error reports for failed records
- Allow reprocessing of failed records only
- Maintain data integrity throughout process

## Performance Optimization

### Processing Performance

**Batch Optimization:**
- Process multiple files in parallel
- Use database transactions efficiently
- Implement connection pooling
- Cache frequently accessed data

**Memory Management:**
- Stream large files instead of loading entirely
- Use generators for data processing
- Implement proper garbage collection
- Monitor memory usage during processing

**Database Optimization:**
- Use bulk insert operations
- Implement proper indexing strategy
- Optimize query patterns
- Use connection pooling

### Monitoring and Metrics

**Processing Metrics:**
- Records processed per second
- File processing duration
- Error rates by type
- Memory and CPU usage

**Quality Metrics:**
- Average quality scores
- Validation issue frequency
- Data completeness rates
- Source reliability metrics

## Best Practices

### Data Quality
1. Always validate data before processing
2. Implement comprehensive error handling
3. Maintain audit trails for all operations
4. Use quality scoring to assess data reliability

### Performance
1. Use batch processing for multiple files
2. Implement proper caching strategies
3. Monitor resource usage during processing
4. Optimize database queries and indexes

### Security
1. Validate all input data thoroughly
2. Use parameterized database queries
3. Implement proper error handling without data exposure
4. Maintain secure audit logs

### Maintainability
1. Use consistent data models across sources
2. Implement comprehensive testing
3. Document all data transformations
4. Use version control for schema changes

This comprehensive data processing guide provides everything needed to understand, implement, and maintain the financial data processing pipeline in the AI Financial Data System.