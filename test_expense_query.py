"""
Test a specific expense query to debug the timeout issue.
"""

import json
import requests
import time


def test_expense_query():
    """Test a simple expense query."""
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/query"
    
    print("🧪 Testing Expense Query")
    print("=" * 40)
    
    # Simple expense query
    query = "What were the total expenses in 2024?"
    
    payload = {
        "query": query,
        "max_iterations": 3,
        "include_raw_data": True
    }
    
    print(f"📝 Query: {query}")
    print("-" * 40)
    
    try:
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=60)
        response_time = time.time() - start_time
        
        print(f"⏱️  Response Time: {response_time:.3f}s")
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n🎯 AI RESPONSE:")
            print("=" * 40)
            print(data.get('answer', 'No answer provided'))
            print("=" * 40)
            
            # Show tool calls
            raw_calls = data.get('supporting_data', {}).get('raw_tool_calls', [])
            if raw_calls:
                print(f"\n🔧 TOOL CALLS:")
                for i, call in enumerate(raw_calls, 1):
                    print(f"   {i}. Tool: {call.get('tool', 'unknown')}")
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


if __name__ == "__main__":
    test_expense_query()