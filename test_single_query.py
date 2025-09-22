"""
Test a single query to see the complete response from the /api/v1/query endpoint.
"""

import json
import requests
import time


def test_single_query():
    """Test a single query and show the complete response."""
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/query"
    
    print("🧪 Testing Single Query - Complete Response")
    print("=" * 60)
    
    # Test query
    query = "What was the total revenue in 2024?"
    
    payload = {
        "query": query,
        "max_iterations": 5,
        "include_raw_data": True
    }
    
    print(f"📝 Query: {query}")
    print("-" * 60)
    
    try:
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=60)
        response_time = time.time() - start_time
        
        print(f"⏱️  Response Time: {response_time:.3f}s")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n🎯 COMPLETE AI RESPONSE:")
            print("=" * 60)
            print(data.get('answer', 'No answer provided'))
            print("=" * 60)
            
            # Conversation ID
            print(f"\n🔗 Conversation ID: {data.get('conversation_id', 'N/A')}")
            
            # Metadata
            metadata = data.get('query_metadata', {})
            print(f"\n📊 PROCESSING METADATA:")
            print(f"   • Processing Time: {metadata.get('processing_time_seconds', 'N/A')}s")
            print(f"   • Tools Used: {metadata.get('tools_used', 'N/A')}")
            print(f"   • Iterations: {metadata.get('iterations', 'N/A')}")
            print(f"   • Data Sources: {metadata.get('data_sources_accessed', [])}")
            print(f"   • Date Ranges: {metadata.get('date_ranges_analyzed', [])}")
            
            # Supporting Data
            supporting_data = data.get('supporting_data', {})
            analysis_summary = supporting_data.get('analysis_summary', {})
            
            print(f"\n🔍 ANALYSIS SUMMARY:")
            print(f"   • Tools Executed: {analysis_summary.get('tools_executed', 0)}")
            print(f"   • Data Sources: {analysis_summary.get('data_sources', [])}")
            print(f"   • Date Ranges: {analysis_summary.get('date_ranges', [])}")
            print(f"   • Metrics Analyzed: {analysis_summary.get('metrics_analyzed', [])}")
            
            # Data Quality
            data_quality = supporting_data.get('data_quality', {})
            print(f"\n✅ DATA QUALITY:")
            print(f"   • Successful Operations: {data_quality.get('successful_operations', 0)}")
            print(f"   • Failed Operations: {data_quality.get('failed_operations', 0)}")
            print(f"   • Data Completeness: {data_quality.get('data_completeness', 'unknown')}")
            
            # Tools Used Details
            tools_used = supporting_data.get('tools_used', {})
            if tools_used:
                print(f"\n🛠️  TOOLS EXECUTION DETAILS:")
                for tool_name, tool_info in tools_used.items():
                    print(f"   • {tool_name}:")
                    print(f"     - Count: {tool_info.get('count', 0)}")
                    print(f"     - Success Rate: {tool_info.get('success_rate', 0)}%")
            
            # Suggestions
            suggestions = data.get('suggestions', [])
            if suggestions:
                print(f"\n💡 SUGGESTED FOLLOW-UP QUESTIONS:")
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"   {i}. {suggestion}")
            else:
                print(f"\n💡 No follow-up suggestions provided")
            
            # Raw data if included
            if payload.get('include_raw_data') and 'raw_tool_calls' in supporting_data:
                print(f"\n🔧 RAW TOOL CALLS:")
                raw_calls = supporting_data.get('raw_tool_calls', [])
                for i, call in enumerate(raw_calls, 1):
                    print(f"   {i}. Tool: {call.get('tool', 'unknown')}")
                    print(f"      Arguments: {call.get('arguments', {})}")
                    print(f"      Success: {call.get('success', False)}")
                    if call.get('error'):
                        print(f"      Error: {call.get('error')}")
            
        else:
            print(f"\n❌ Error Response:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
                
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")


def test_example_questions():
    """Test some example questions to see what the system can handle."""
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/query"
    
    example_queries = [
        "What was the total profit in Q1 2024?",
        "Show me expense trends for the last 6 months",
        "Which expense category had the highest increase this year?",
        "Compare Q1 and Q2 performance",
        "What are the seasonal patterns in our revenue?",
        "How much did we spend on payroll last year?",
        "What's our biggest source of revenue?",
        "Are there any unusual patterns in our expenses?"
    ]
    
    print(f"\n\n🎯 TESTING EXAMPLE QUESTIONS")
    print("=" * 60)
    
    for i, query in enumerate(example_queries, 1):
        print(f"\n{i}. Testing: '{query}'")
        print("-" * 40)
        
        payload = {
            "query": query,
            "max_iterations": 3,
            "include_raw_data": False
        }
        
        try:
            response = requests.post(endpoint, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', 'No answer')
                # Show first 150 characters of answer
                preview = answer[:150] + "..." if len(answer) > 150 else answer
                print(f"✅ Response: {preview}")
                
                # Show suggestions if any
                suggestions = data.get('suggestions', [])
                if suggestions:
                    print(f"💡 Suggestions: {suggestions[0]}")
                    
            else:
                print(f"❌ Failed with status {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # Small delay between requests
        time.sleep(1)


if __name__ == "__main__":
    # Test single query with full details
    test_single_query()
    
    # Test example questions
    test_example_questions()
    
    print(f"\n\n🎉 Testing Complete!")