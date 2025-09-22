"""
Test to check available tools.
"""

import requests

def test_available_tools():
    """Test what tools are available."""
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/ai/tools"
    
    try:
        response = requests.get(endpoint, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            tools = data.get("available_tools", [])
            
            print("🛠️  Available Tools:")
            for i, tool in enumerate(tools, 1):
                print(f"   {i}. {tool}")
            
            print(f"\nTotal tools: {len(tools)}")
            
            # Check if our new tools are there
            new_tools = [
                "get_expenses_by_period",
                "analyze_expense_trends", 
                "get_expense_categories",
                "analyze_seasonal_patterns",
                "get_quarterly_performance"
            ]
            
            print(f"\n🔍 Checking for new tools:")
            for tool in new_tools:
                if tool in tools:
                    print(f"   ✅ {tool}")
                else:
                    print(f"   ❌ {tool} - MISSING")
                    
        else:
            print(f"❌ Failed to get tools: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    test_available_tools()