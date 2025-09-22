import json
from typing import Any, Dict, List, Optional, Tuple

from app.ai.conversation import ConversationManager, get_conversation_manager
from app.ai.exceptions import FinancialAnalysisError, ValidationError
from app.ai.llm_client import LLMClient, get_llm_client
from app.ai.registry import call_tool, get_available_tools
from app.ai.tools.schemas import (
    get_financial_tool_schemas,
    validate_tool_call_arguments,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class FinancialAgent:
    """
    AI agent for financial data analysis with tool calling capabilities.

    This agent can understand natural language queries about financial data,
    select appropriate tools, execute them, and provide intelligent responses.
    """

    def __init__(self):
        self.llm_client: LLMClient = get_llm_client()
        self.conversation_manager: ConversationManager = get_conversation_manager()
        self.system_prompt = self._build_system_prompt()

        # Validate configuration
        if not self.llm_client.validate_configuration():
            raise FinancialAnalysisError(
                "LLM client is not properly configured. Please check API keys."
            )

        logger.info("Financial agent initialized successfully")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the AI agent."""
        available_tools = get_available_tools()

        return f"""You are an AI financial analyst assistant with access to comprehensive financial data analysis tools. 
Your role is to provide direct, actionable answers to financial questions using real data.

AVAILABLE TOOLS:
{', '.join(available_tools)}

CORE CAPABILITIES:
- Revenue analysis and trends across any time period
- Expense analysis, trends, and category breakdowns
- Profit calculations and performance comparisons
- Seasonal pattern analysis and quarterly performance
- Growth rate calculations and anomaly detection
- Multi-source data integration (QuickBooks, RootFi)

RESPONSE STRATEGY:
1. ALWAYS provide a direct answer first, then supporting details
2. Use tools proactively - don't ask for clarification unless absolutely necessary
3. Make reasonable assumptions about time periods (default to current/recent year)
4. For vague queries, choose the most logical interpretation and proceed
5. Provide specific numbers, percentages, and concrete insights
6. Include actionable business recommendations when relevant

SMART DEFAULTS - USE THESE AUTOMATICALLY:
- Time period not specified → Use 2024 (current year)
- "Last 6 months" → Use 2024-07-01 to 2024-12-31
- "This year" → Use 2024-01-01 to 2024-12-31
- "Q1" → Use 2024-01-01 to 2024-03-31
- "Q2" → Use 2024-04-01 to 2024-06-30
- Source not specified → Analyze all sources, show breakdown
- Comparison queries → Compare Q1 vs Q2 2024, or 2023 vs 2024

IMMEDIATE ACTION RULES:
1. For "expense trends" → Use get_revenue_by_period with account_type="expense" for last 6 months
2. For "seasonal patterns" → Use calculate_growth_rate across multiple months
3. For "expense categories" → Use detect_anomalies on expenses to find unusual patterns
4. For "compare Q1 Q2" → Use compare_financial_metrics with Q1 and Q2 periods
5. For "biggest revenue source" → Use get_revenue_by_period, analyze by source

RESPONSE FORMAT:
- **Bold key findings** with specific numbers
- Show source breakdown (QuickBooks vs RootFi)
- Include growth percentages when comparing periods
- Add 2-3 business insights or recommendations
- Use tables or bullet points for clarity

NEVER ASK FOR CLARIFICATION ON:
- Time periods (use current year/recent months)
- Which metrics to analyze (choose the most relevant)
- Which data source (analyze all, show breakdown)
- Comparison periods (use logical defaults like Q1 vs Q2)

EXAMPLE RESPONSES:
- "Show expense trends" → Analyze expenses for 2024-07-01 to 2024-12-31, show month-by-month changes
- "Compare Q1 Q2" → Use compare_financial_metrics for Q1 vs Q2 2024, show revenue/expenses/profit
- "Seasonal patterns" → Use calculate_growth_rate for monthly data across 2024
- "Expense categories" → Use detect_anomalies to find unusual expense patterns

Remember: Users want immediate, actionable insights. Be decisive, use smart defaults, and provide comprehensive analysis without asking for clarification."""

    def process_query(
        self, query: str, conversation_id: Optional[str] = None, max_iterations: int = 5
    ) -> Dict[str, Any]:
        """
        Process a natural language query about financial data.

        Args:
            query: User's natural language query
            conversation_id: Optional conversation ID for context
            max_iterations: Maximum number of tool calling iterations

        Returns:
            Dictionary containing:
            - response: The agent's response text
            - conversation_id: Conversation ID (created if not provided)
            - tool_calls_made: List of tools that were called
            - data_used: Summary of data that was analyzed

        Raises:
            FinancialAnalysisError: If query processing fails
        """
        logger.info(
            "Processing query: %s", query[:100] + "..." if len(query) > 100 else query
        )

        try:
            # Create or get conversation context
            if conversation_id is None:
                conversation_id = self.conversation_manager.create_conversation()

            context = self.conversation_manager.get_conversation(conversation_id)
            if context is None:
                conversation_id = self.conversation_manager.create_conversation(
                    conversation_id
                )
                context = self.conversation_manager.get_conversation(conversation_id)

            # Add user message to conversation
            context.add_user_message(query)

            # Prepare messages for LLM
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(context.get_messages_for_llm(max_messages=10))

            # Get available tools
            tools = get_financial_tool_schemas()

            # Track tool calls and iterations
            tool_calls_made = []
            iteration = 0

            while iteration < max_iterations:
                iteration += 1
                logger.debug("Agent iteration %d/%d", iteration, max_iterations)

                # Get LLM response
                llm_response = self.llm_client.chat_completion(
                    messages=messages, tools=tools
                )

                # Add assistant message to conversation
                assistant_tool_calls = None
                if llm_response.tool_calls:
                    assistant_tool_calls = [
                        {
                            "id": tc.call_id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in llm_response.tool_calls
                    ]

                context.add_assistant_message(
                    content=llm_response.content, tool_calls=assistant_tool_calls
                )

                # Add assistant message to LLM messages
                assistant_message = {"role": "assistant"}
                if llm_response.content:
                    assistant_message["content"] = llm_response.content
                if assistant_tool_calls:
                    assistant_message["tool_calls"] = assistant_tool_calls
                messages.append(assistant_message)

                # If no tool calls, we're done
                if not llm_response.tool_calls:
                    break

                # Execute tool calls
                for tool_call in llm_response.tool_calls:
                    try:
                        # Validate tool call arguments
                        validate_tool_call_arguments(
                            tool_call.name, tool_call.arguments
                        )

                        # Execute the tool
                        logger.debug("Executing tool: %s", tool_call.name)
                        result = call_tool(tool_call.name, **tool_call.arguments)

                        # Track tool call
                        tool_calls_made.append(
                            {
                                "tool": tool_call.name,
                                "arguments": tool_call.arguments,
                                "success": True,
                            }
                        )

                        # Add tool response to conversation and messages
                        context.add_tool_response(
                            tool_call.name, tool_call.call_id, result
                        )

                        tool_message = {
                            "role": "tool",
                            "tool_call_id": tool_call.call_id,
                            "name": tool_call.name,
                            "content": json.dumps(result, default=str, indent=2),
                        }
                        messages.append(tool_message)

                    except Exception as e:
                        logger.error(
                            "Tool execution failed for %s: %s", tool_call.name, str(e)
                        )

                        # Track failed tool call
                        tool_calls_made.append(
                            {
                                "tool": tool_call.name,
                                "arguments": tool_call.arguments,
                                "success": False,
                                "error": str(e),
                            }
                        )

                        # Add error message for LLM
                        error_message = {
                            "role": "tool",
                            "tool_call_id": tool_call.call_id,
                            "name": tool_call.name,
                            "content": f"Error: {str(e)}",
                        }
                        messages.append(error_message)

            # Get final response if we ended with tool calls
            if llm_response.tool_calls and iteration < max_iterations:
                final_response = self.llm_client.chat_completion(
                    messages=messages, tools=tools
                )

                context.add_assistant_message(content=final_response.content)
                final_content = final_response.content
            else:
                final_content = llm_response.content

            # Prepare response data
            data_used = self._extract_data_summary(tool_calls_made)

            result = {
                "response": final_content
                or "I apologize, but I couldn't generate a response to your query.",
                "conversation_id": conversation_id,
                "tool_calls_made": tool_calls_made,
                "data_used": data_used,
                "iterations": iteration,
            }

            logger.info(
                "Query processed successfully with %d tool calls", len(tool_calls_made)
            )
            return result

        except Exception as e:
            logger.error("Error processing query: %s", str(e))
            raise FinancialAnalysisError(f"Failed to process query: {str(e)}") from e

    def _extract_data_summary(
        self, tool_calls_made: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract a summary of data that was used in the analysis.

        Args:
            tool_calls_made: List of tool calls that were executed

        Returns:
            Summary of data usage
        """
        summary = {
            "tools_used": [],
            "date_ranges_analyzed": [],
            "metrics_analyzed": set(),
            "sources_accessed": set(),
        }

        for tool_call in tool_calls_made:
            if not tool_call.get("success", False):
                continue

            tool_name = tool_call["tool"]
            args = tool_call["arguments"]

            summary["tools_used"].append(tool_name)

            # Extract date ranges
            if "start_date" in args and "end_date" in args:
                date_range = f"{args['start_date']} to {args['end_date']}"
                if date_range not in summary["date_ranges_analyzed"]:
                    summary["date_ranges_analyzed"].append(date_range)

            # Extract metrics
            if "metric" in args:
                summary["metrics_analyzed"].add(args["metric"])
            if "metrics" in args:
                summary["metrics_analyzed"].update(args["metrics"])

            # Extract sources
            if "source" in args and args["source"]:
                summary["sources_accessed"].add(args["source"])

        # Convert sets to lists for JSON serialization
        summary["metrics_analyzed"] = list(summary["metrics_analyzed"])
        summary["sources_accessed"] = list(summary["sources_accessed"])

        return summary

    def get_conversation_context(
        self, conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation context and summary.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation context information or None if not found
        """
        context = self.conversation_manager.get_conversation(conversation_id)
        if context is None:
            return None

        return {
            "conversation_id": conversation_id,
            "created_at": context.created_at.isoformat(),
            "last_updated": context.last_updated.isoformat(),
            "message_count": len(context.messages),
            "summary": context.get_context_summary(),
        }

    def clear_conversation(self, conversation_id: str) -> bool:
        """
        Clear a conversation context.

        Args:
            conversation_id: Conversation ID to clear

        Returns:
            True if conversation was found and cleared
        """
        if conversation_id in self.conversation_manager.conversations:
            del self.conversation_manager.conversations[conversation_id]
            logger.info("Cleared conversation: %s", conversation_id)
            return True
        return False

    def get_agent_status(self) -> Dict[str, Any]:
        """
        Get the current status of the AI agent.

        Returns:
            Dictionary with agent status information
        """
        return {
            "llm_configured": self.llm_client.validate_configuration(),
            "available_tools": get_available_tools(),
            "conversation_stats": self.conversation_manager.get_conversation_stats(),
            "system_prompt_length": len(self.system_prompt),
        }


# Global agent instance
_financial_agent = None


def get_financial_agent() -> FinancialAgent:
    """Get the global financial agent instance."""
    global _financial_agent
    if _financial_agent is None:
        _financial_agent = FinancialAgent()
    return _financial_agent
