# AI Financial Agent Guide

## Overview

The AI Financial Agent is an intelligent system that can understand natural language queries about financial data and automatically select and execute the appropriate analysis tools to provide comprehensive answers.

## Key Features

### 🤖 Natural Language Processing
- Understands complex financial queries in plain English
- Maps natural language to appropriate tool calls
- Provides intelligent, context-aware responses

### 🛠️ Tool Integration
- **get_revenue_by_period**: Analyze revenue data for specific time periods
- **compare_financial_metrics**: Compare financial performance between periods
- **calculate_growth_rate**: Calculate growth rates and trends
- **detect_anomalies**: Identify unusual patterns in financial data

### 💬 Conversation Management
- Multi-turn conversations with context preservation
- Follow-up questions that reference previous queries
- Conversation history tracking and cleanup

### 🔄 Multi-Step Reasoning
- Can perform complex analysis requiring multiple tool calls
- Chains tool results together for comprehensive insights
- Handles error recovery and alternative approaches

## API Endpoints

### GET /api/v1/ai/status
Get the current status of the AI agent.

**Response:**
```json
{
  "llm_configured": true,
  "available_tools": ["get_revenue_by_period", "compare_financial_metrics", "calculate_growth_rate", "detect_anomalies"],
  "conversation_stats": {...},
  "system_prompt_length": 1545
}
```

### POST /api/v1/ai/query
Process a natural language query about financial data.

**Request:**
```json
{
  "query": "What was our revenue last month compared to the previous month?",
  "conversation_id": "optional-conversation-id",
  "max_iterations": 5
}
```

**Response:**
```json
{
  "response": "Based on the analysis of your financial data...",
  "conversation_id": "uuid-conversation-id",
  "tool_calls_made": [...],
  "data_used": {...},
  "iterations": 2
}
```

### GET /api/v1/ai/tools
Get information about available financial analysis tools.

### GET /api/v1/ai/conversation/{id}
Get information about a specific conversation.

### DELETE /api/v1/ai/conversation/{id}
Clear a conversation and its history.

## Usage Examples

### Basic Query
```bash
curl -X POST "http://localhost:8000/api/v1/ai/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What was the revenue last month?"}'
```

### Comparative Analysis
```bash
curl -X POST "http://localhost:8000/api/v1/ai/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "Compare Q1 2024 revenue to Q1 2023 and show growth trends"}'
```

### Follow-up Questions
```bash
# First query
curl -X POST "http://localhost:8000/api/v1/ai/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "What was our revenue last month?"}'

# Follow-up using the same conversation_id
curl -X POST "http://localhost:8000/api/v1/ai/query" \
     -H "Content-Type: application/json" \
     -d '{"query": "How does that compare to expenses?", "conversation_id": "previous-conversation-id"}'
```

## Python API Usage

```python
from app.ai import get_financial_agent

# Initialize the agent
agent = get_financial_agent()

# Process a query
result = agent.process_query("What was the revenue last month?")
print(result['response'])

# Continue the conversation
result = agent.process_query(
    "How does that compare to the previous month?", 
    conversation_id=result['conversation_id']
)
print(result['response'])
```

## Configuration

### Environment Variables
```bash
# Required: At least one LLM provider API key
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# LLM Configuration
DEFAULT_LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4
ANTHROPIC_MODEL=claude-3-sonnet-20240229
MAX_TOKENS=4000
TEMPERATURE=0.1
```

### Supported Models
- **OpenAI**: GPT-4, GPT-3.5-turbo, and newer models with function calling
- **Anthropic**: Claude-3 models (future support)

## Query Examples

### Revenue Analysis
- "What was our total revenue last month?"
- "Show me revenue by source for Q1 2024"
- "Compare revenue between QuickBooks and RootFi data"

### Comparative Analysis
- "Compare Q1 vs Q2 revenue and expenses"
- "How did our profit change year-over-year?"
- "Show the difference between this month and last month"

### Growth Analysis
- "Calculate monthly revenue growth for the past 6 months"
- "What's our profit growth trend?"
- "Show expense growth patterns"

### Anomaly Detection
- "Are there any unusual spikes in our revenue?"
- "Detect anomalies in expense patterns"
- "Find irregularities in profit data"

### Complex Multi-Step Queries
- "Analyze our financial performance for Q1, compare it to Q4, and identify any anomalies"
- "Show revenue trends, calculate growth rates, and highlight any concerning patterns"
- "Compare all metrics between this year and last year, then detect any unusual changes"

## Error Handling

The AI agent includes comprehensive error handling:

- **Validation Errors**: Invalid parameters or date formats
- **Data Not Found**: No data available for specified criteria
- **LLM Errors**: API failures or rate limiting
- **Tool Execution Errors**: Database or calculation failures

All errors are logged and returned with appropriate HTTP status codes and user-friendly messages.

## Performance Considerations

- **Conversation Cleanup**: Old conversations are automatically cleaned up
- **Rate Limiting**: Respects LLM provider rate limits
- **Caching**: Tool results are cached within conversations
- **Timeout Handling**: Requests have configurable timeouts

## Security

- API keys are stored securely in environment variables
- Input validation prevents injection attacks
- Conversation data is stored in memory (not persisted)
- No sensitive data is logged

## Troubleshooting

### Common Issues

1. **"LLM client is not properly configured"**
   - Ensure OPENAI_API_KEY or ANTHROPIC_API_KEY is set
   - Check that the API key is valid and has sufficient credits

2. **"No financial records found"**
   - Verify that financial data has been ingested
   - Check date ranges and filters in the query

3. **"Tool execution failed"**
   - Check database connectivity
   - Verify data integrity and format

### Debug Mode
Set `DEBUG=true` in your environment to enable detailed logging.

## Development

### Adding New Tools
1. Create the tool function in `app/ai/`
2. Add the tool to `FINANCIAL_TOOLS` registry
3. Define the tool schema in `tool_schemas.py`
4. Update the system prompt if needed

### Extending LLM Support
1. Add new provider client in `llm_client.py`
2. Update configuration in `config.py`
3. Add provider-specific message formatting

### Testing
Run the test suite to verify functionality:
```bash
python -m pytest tests/
```