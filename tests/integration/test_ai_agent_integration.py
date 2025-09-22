"""
Integration tests for AI agent tool calling and query processing.

Tests the complete AI agent workflow including natural language understanding,
tool selection, execution, and response generation.
"""

import json
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from app.ai.agent import FinancialAgent, get_financial_agent
from app.ai.exceptions import FinancialAnalysisError, ValidationError
from app.database.connection import create_tables, get_db_session, get_engine
from app.database.models import AccountDB, AccountValueDB, FinancialRecordDB
from app.models.financial import AccountType, SourceType


@pytest.fixture(scope="function")
def setup_test_database():
    """Set up test database with sample financial data."""
    engine = get_engine()
    from app.database.models import Base
    
    # Clean and create tables
    Base.metadata.drop_all(bind=engine)
    create_tables(engine)
    
    # Insert comprehensive test data
    with get_db_session() as session:
        # Create financial records for multiple periods
        records = [
            FinancialRecordDB(
                id="test_record_q1",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 3, 31),
                currency="USD",
                revenue=Decimal('150000.00'),
                expenses=Decimal('120000.00'),
                net_profit=Decimal('30000.00'),
                raw_data='{"test": "q1_data"}'
            ),
            FinancialRecordDB(
                id="test_record_q2",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 4, 1),
                period_end=date(2024, 6, 30),
                currency="USD",
                revenue=Decimal('180000.00'),
                expenses=Decimal('140000.00'),
                net_profit=Decimal('40000.00'),
                raw_data='{"test": "q2_data"}'
            ),
            FinancialRecordDB(
                id="test_record_rootfi",
                source=SourceType.ROOTFI.value,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 3, 31),
                currency="USD",
                revenue=Decimal('145000.00'),
                expenses=Decimal('115000.00'),
                net_profit=Decimal('30000.00'),
                raw_data='{"test": "rootfi_data"}'
            ),
            # Add monthly data for trend analysis
            FinancialRecordDB(
                id="test_record_jan",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 31),
                currency="USD",
                revenue=Decimal('45000.00'),
                expenses=Decimal('38000.00'),
                net_profit=Decimal('7000.00'),
                raw_data='{"test": "jan_data"}'
            ),
            FinancialRecordDB(
                id="test_record_feb",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 2, 1),
                period_end=date(2024, 2, 29),
                currency="USD",
                revenue=Decimal('50000.00'),
                expenses=Decimal('40000.00'),
                net_profit=Decimal('10000.00'),
                raw_data='{"test": "feb_data"}'
            ),
            FinancialRecordDB(
                id="test_record_mar",
                source=SourceType.QUICKBOOKS.value,
                period_start=date(2024, 3, 1),
                period_end=date(2024, 3, 31),
                currency="USD",
                revenue=Decimal('55000.00'),
                expenses=Decimal('42000.00'),
                net_profit=Decimal('13000.00'),
                raw_data='{"test": "mar_data"}'
            )
        ]
        
        for record in records:
            session.add(record)
        
        # Create accounts with hierarchy
        accounts = [
            AccountDB(
                account_id="revenue_sales",
                name="Product Sales",
                account_type=AccountType.REVENUE.value,
                source=SourceType.QUICKBOOKS.value,
                description="Primary product sales revenue"
            ),
            AccountDB(
                account_id="revenue_services",
                name="Service Revenue",
                account_type=AccountType.REVENUE.value,
                source=SourceType.QUICKBOOKS.value,
                description="Service-based revenue"
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
                description="Marketing and advertising costs"
            ),
            AccountDB(
                account_id="expense_payroll",
                name="Payroll Expenses",
                account_type=AccountType.EXPENSE.value,
                parent_account_id="expense_operations",
                source=SourceType.QUICKBOOKS.value,
                description="Employee payroll costs"
            )
        ]
        
        for account in accounts:
            session.add(account)
        
        # Create account values
        account_values = [
            # Q1 values
            AccountValueDB(account_id="revenue_sales", financial_record_id="test_record_q1", value=Decimal('100000.00')),
            AccountValueDB(account_id="revenue_services", financial_record_id="test_record_q1", value=Decimal('50000.00')),
            AccountValueDB(account_id="expense_operations", financial_record_id="test_record_q1", value=Decimal('120000.00')),
            AccountValueDB(account_id="expense_marketing", financial_record_id="test_record_q1", value=Decimal('30000.00')),
            AccountValueDB(account_id="expense_payroll", financial_record_id="test_record_q1", value=Decimal('70000.00')),
            
            # Q2 values
            AccountValueDB(account_id="revenue_sales", financial_record_id="test_record_q2", value=Decimal('120000.00')),
            AccountValueDB(account_id="revenue_services", financial_record_id="test_record_q2", value=Decimal('60000.00')),
            AccountValueDB(account_id="expense_operations", financial_record_id="test_record_q2", value=Decimal('140000.00')),
            AccountValueDB(account_id="expense_marketing", financial_record_id="test_record_q2", value=Decimal('40000.00')),
            AccountValueDB(account_id="expense_payroll", financial_record_id="test_record_q2", value=Decimal('80000.00')),
            
            # Monthly values for trend analysis
            AccountValueDB(account_id="revenue_sales", financial_record_id="test_record_jan", value=Decimal('30000.00')),
            AccountValueDB(account_id="revenue_sales", financial_record_id="test_record_feb", value=Decimal('35000.00')),
            AccountValueDB(account_id="revenue_sales", financial_record_id="test_record_mar", value=Decimal('40000.00'))
        ]
        
        for account_value in account_values:
            session.add(account_value)
        
        session.commit()
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    with patch('app.ai.agent.get_llm_client') as mock_get_client:
        mock_client = Mock()
        mock_client.validate_configuration.return_value = True
        mock_get_client.return_value = mock_client
        yield mock_client


class TestAIAgentIntegration:
    """Integration tests for AI agent functionality."""
    
    def test_agent_initialization(self, setup_test_database, mock_llm_client):
        """Test AI agent initialization and configuration."""
        agent = FinancialAgent()
        
        # Verify agent is properly initialized
        assert agent.llm_client is not None
        assert agent.conversation_manager is not None
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 0
        
        # Verify agent status
        status = agent.get_agent_status()
        assert status["llm_configured"] is True
        assert "available_tools" in status
        assert len(status["available_tools"]) > 0
        assert "conversation_stats" in status
        assert "system_prompt_length" in status
    
    def test_simple_revenue_query_integration(self, setup_test_database, mock_llm_client):
        """Test simple revenue query with real tool execution."""
        # Mock LLM response for revenue query
        mock_response = Mock()
        mock_response.content = "Based on the data, Q1 2024 revenue was $150,000."
        mock_response.tool_calls = [
            Mock(
                call_id="call_1",
                name="get_revenue_by_period",
                arguments={"start_date": "2024-01-01", "end_date": "2024-03-31"}
            )
        ]
        mock_llm_client.chat_completion.return_value = mock_response
        
        agent = FinancialAgent()
        
        # Process revenue query
        result = agent.process_query("What was the total revenue in Q1 2024?")
        
        # Verify response structure
        assert "response" in result
        assert "conversation_id" in result
        assert "tool_calls_made" in result
        assert "data_used" in result
        assert "iterations" in result
        
        # Verify tool was called successfully
        assert len(result["tool_calls_made"]) == 1
        tool_call = result["tool_calls_made"][0]
        assert tool_call["tool"] == "get_revenue_by_period"
        assert tool_call["success"] is True
        assert "arguments" in tool_call
        
        # Verify data summary
        data_used = result["data_used"]
        assert "tools_used" in data_used
        assert "date_ranges_analyzed" in data_used
        assert "get_revenue_by_period" in data_used["tools_used"]
        assert "2024-01-01 to 2024-03-31" in data_used["date_ranges_analyzed"]
    
    def test_comparison_query_integration(self, setup_test_database, mock_llm_client):
        """Test comparison query with multiple tool calls."""
        # Mock LLM responses for comparison query
        mock_response1 = Mock()
        mock_response1.content = None
        mock_response1.tool_calls = [
            Mock(
                call_id="call_1",
                name="compare_financial_metrics",
                arguments={
                    "period1_start": "2024-01-01",
                    "period1_end": "2024-03-31",
                    "period2_start": "2024-04-01", 
                    "period2_end": "2024-06-30",
                    "metrics": ["revenue", "expenses", "net_profit"]
                }
            )
        ]
        
        mock_response2 = Mock()
        mock_response2.content = "Q2 2024 showed significant improvement over Q1 with revenue increasing by 20%."
        mock_response2.tool_calls = None
        
        mock_llm_client.chat_completion.side_effect = [mock_response1, mock_response2]
        
        agent = FinancialAgent()
        
        # Process comparison query
        result = agent.process_query("Compare Q1 and Q2 2024 performance")
        
        # Verify multiple tool calls were made
        assert len(result["tool_calls_made"]) == 1
        assert result["tool_calls_made"][0]["tool"] == "compare_financial_metrics"
        assert result["tool_calls_made"][0]["success"] is True
        
        # Verify final response was generated
        assert result["response"] is not None
        assert len(result["response"]) > 0
        
        # Verify data summary includes comparison metrics
        data_used = result["data_used"]
        assert "metrics_analyzed" in data_used
        expected_metrics = ["revenue", "expenses", "net_profit"]
        for metric in expected_metrics:
            assert metric in data_used["metrics_analyzed"]
    
    def test_growth_rate_analysis_integration(self, setup_test_database, mock_llm_client):
        """Test growth rate analysis with monthly data."""
        # Mock LLM response for growth rate query
        mock_response = Mock()
        mock_response.content = None
        mock_response.tool_calls = [
            Mock(
                call_id="call_1",
                name="calculate_growth_rate",
                arguments={
                    "metric": "revenue",
                    "periods": [
                        {"start": "2024-01-01", "end": "2024-01-31"},
                        {"start": "2024-02-01", "end": "2024-02-29"},
                        {"start": "2024-03-01", "end": "2024-03-31"}
                    ]
                }
            )
        ]
        
        mock_final_response = Mock()
        mock_final_response.content = "Revenue showed consistent growth with an average monthly growth rate of 11.1%."
        mock_final_response.tool_calls = None
        
        mock_llm_client.chat_completion.side_effect = [mock_response, mock_final_response]
        
        agent = FinancialAgent()
        
        # Process growth rate query
        result = agent.process_query("Show me revenue growth trends for Q1 2024")
        
        # Verify growth rate tool was called
        assert len(result["tool_calls_made"]) == 1
        tool_call = result["tool_calls_made"][0]
        assert tool_call["tool"] == "calculate_growth_rate"
        assert tool_call["success"] is True
        assert tool_call["arguments"]["metric"] == "revenue"
        
        # Verify periods were analyzed
        periods = tool_call["arguments"]["periods"]
        assert len(periods) == 3
        assert periods[0]["start"] == "2024-01-01"
        assert periods[2]["end"] == "2024-03-31"
    
    def test_conversation_context_integration(self, setup_test_database, mock_llm_client):
        """Test conversation context management."""
        # Mock responses for follow-up conversation
        mock_response1 = Mock()
        mock_response1.content = "Q1 2024 revenue was $150,000."
        mock_response1.tool_calls = [
            Mock(
                call_id="call_1",
                name="get_revenue_by_period",
                arguments={"start_date": "2024-01-01", "end_date": "2024-03-31"}
            )
        ]
        
        mock_response2 = Mock()
        mock_response2.content = "Q2 2024 revenue was $180,000, showing a 20% increase from Q1."
        mock_response2.tool_calls = [
            Mock(
                call_id="call_2",
                name="get_revenue_by_period",
                arguments={"start_date": "2024-04-01", "end_date": "2024-06-30"}
            )
        ]
        
        mock_llm_client.chat_completion.side_effect = [mock_response1, mock_response2]
        
        agent = FinancialAgent()
        
        # First query
        result1 = agent.process_query("What was Q1 2024 revenue?")
        conversation_id = result1["conversation_id"]
        
        # Follow-up query with same conversation
        result2 = agent.process_query("What about Q2?", conversation_id=conversation_id)
        
        # Verify same conversation was used
        assert result2["conversation_id"] == conversation_id
        
        # Verify conversation context
        context = agent.get_conversation_context(conversation_id)
        assert context is not None
        assert context["conversation_id"] == conversation_id
        assert context["message_count"] >= 4  # User + Assistant messages for both queries
        assert "created_at" in context
        assert "last_updated" in context
        assert "summary" in context
    
    def test_tool_execution_error_handling(self, setup_test_database, mock_llm_client):
        """Test error handling during tool execution."""
        # Mock LLM response that calls a tool with invalid arguments
        mock_response = Mock()
        mock_response.content = None
        mock_response.tool_calls = [
            Mock(
                call_id="call_1",
                name="get_revenue_by_period",
                arguments={"start_date": "invalid-date", "end_date": "2024-03-31"}
            )
        ]
        
        mock_final_response = Mock()
        mock_final_response.content = "I encountered an error retrieving the revenue data."
        mock_final_response.tool_calls = None
        
        mock_llm_client.chat_completion.side_effect = [mock_response, mock_final_response]
        
        agent = FinancialAgent()
        
        # Process query that will cause tool error
        result = agent.process_query("What was the revenue for an invalid period?")
        
        # Verify tool call was attempted but failed
        assert len(result["tool_calls_made"]) == 1
        tool_call = result["tool_calls_made"][0]
        assert tool_call["tool"] == "get_revenue_by_period"
        assert tool_call["success"] is False
        assert "error" in tool_call
        
        # Verify agent still provided a response
        assert result["response"] is not None
        assert len(result["response"]) > 0
    
    def test_max_iterations_limit(self, setup_test_database, mock_llm_client):
        """Test maximum iterations limit for tool calling."""
        # Mock LLM to always return tool calls (infinite loop scenario)
        mock_response = Mock()
        mock_response.content = None
        mock_response.tool_calls = [
            Mock(
                call_id="call_1",
                name="get_revenue_by_period",
                arguments={"start_date": "2024-01-01", "end_date": "2024-03-31"}
            )
        ]
        
        mock_llm_client.chat_completion.return_value = mock_response
        
        agent = FinancialAgent()
        
        # Process query with low max_iterations
        result = agent.process_query(
            "What was the revenue?", 
            max_iterations=2
        )
        
        # Verify iterations were limited
        assert result["iterations"] == 2
        assert len(result["tool_calls_made"]) == 2  # Should stop at max_iterations
    
    def test_agent_status_and_health(self, setup_test_database, mock_llm_client):
        """Test agent status reporting and health checks."""
        agent = FinancialAgent()
        
        # Get agent status
        status = agent.get_agent_status()
        
        # Verify status structure
        assert "llm_configured" in status
        assert "available_tools" in status
        assert "conversation_stats" in status
        assert "system_prompt_length" in status
        
        # Verify LLM configuration
        assert status["llm_configured"] is True
        
        # Verify tools are available
        tools = status["available_tools"]
        expected_tools = [
            "get_revenue_by_period",
            "compare_financial_metrics", 
            "calculate_growth_rate",
            "detect_anomalies"
        ]
        for tool in expected_tools:
            assert tool in tools
        
        # Verify conversation stats
        conv_stats = status["conversation_stats"]
        assert "active_conversations" in conv_stats
        assert "total_conversations_created" in conv_stats
    
    def test_conversation_cleanup(self, setup_test_database, mock_llm_client):
        """Test conversation cleanup functionality."""
        mock_response = Mock()
        mock_response.content = "Test response"
        mock_response.tool_calls = None
        mock_llm_client.chat_completion.return_value = mock_response
        
        agent = FinancialAgent()
        
        # Create a conversation
        result = agent.process_query("Test query")
        conversation_id = result["conversation_id"]
        
        # Verify conversation exists
        context = agent.get_conversation_context(conversation_id)
        assert context is not None
        
        # Clear the conversation
        cleared = agent.clear_conversation(conversation_id)
        assert cleared is True
        
        # Verify conversation was cleared
        context = agent.get_conversation_context(conversation_id)
        assert context is None
        
        # Try to clear non-existent conversation
        cleared = agent.clear_conversation("non-existent-id")
        assert cleared is False
    
    def test_global_agent_instance(self, setup_test_database, mock_llm_client):
        """Test global agent instance management."""
        # Get agent instance
        agent1 = get_financial_agent()
        agent2 = get_financial_agent()
        
        # Should return same instance
        assert agent1 is agent2
        
        # Verify it's properly configured
        assert agent1.llm_client is not None
        assert agent1.conversation_manager is not None
    
    def test_complex_multi_tool_workflow(self, setup_test_database, mock_llm_client):
        """Test complex workflow with multiple tool calls."""
        # Mock sequence of LLM responses for complex analysis
        mock_responses = [
            # First response - get revenue data
            Mock(
                content=None,
                tool_calls=[
                    Mock(
                        call_id="call_1",
                        name="get_revenue_by_period",
                        arguments={"start_date": "2024-01-01", "end_date": "2024-06-30"}
                    )
                ]
            ),
            # Second response - compare periods
            Mock(
                content=None,
                tool_calls=[
                    Mock(
                        call_id="call_2",
                        name="compare_financial_metrics",
                        arguments={
                            "period1_start": "2024-01-01",
                            "period1_end": "2024-03-31",
                            "period2_start": "2024-04-01",
                            "period2_end": "2024-06-30",
                            "metrics": ["revenue", "expenses"]
                        }
                    )
                ]
            ),
            # Final response with analysis
            Mock(
                content="Based on the analysis, revenue grew 20% from Q1 to Q2, with expenses increasing by 16.7%.",
                tool_calls=None
            )
        ]
        
        mock_llm_client.chat_completion.side_effect = mock_responses
        
        agent = FinancialAgent()
        
        # Process complex query
        result = agent.process_query(
            "Analyze our financial performance for the first half of 2024, comparing Q1 and Q2"
        )
        
        # Verify multiple tools were called
        assert len(result["tool_calls_made"]) == 2
        
        # Verify specific tools were used
        tool_names = [tc["tool"] for tc in result["tool_calls_made"]]
        assert "get_revenue_by_period" in tool_names
        assert "compare_financial_metrics" in tool_names
        
        # Verify all tools succeeded
        for tool_call in result["tool_calls_made"]:
            assert tool_call["success"] is True
        
        # Verify comprehensive data summary
        data_used = result["data_used"]
        assert len(data_used["tools_used"]) == 2
        assert len(data_used["date_ranges_analyzed"]) >= 1
        assert "revenue" in data_used["metrics_analyzed"]
        assert "expenses" in data_used["metrics_analyzed"]
        
        # Verify final response
        assert result["response"] is not None
        assert "20%" in result["response"]  # Growth percentage
        assert "16.7%" in result["response"]  # Expense increase


if __name__ == "__main__":
    pytest.main([__file__, "-v"])