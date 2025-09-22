"""
Test script for the new /api/v1/query endpoint.

This script tests the natural language query endpoint to ensure it works correctly
with various types of queries and error conditions.
"""

import json
import requests
import time
from typing import Dict, Any


def test_query_endpoint():
    """Test the /api/v1/query endpoint with various scenarios."""
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/v1/query"
    
    print("Testing /api/v1/query endpoint...")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        {
            "name": "Simple Revenue Query",
            "query": "What was the total revenue in 2024?",
            "expected_status": 200
        },
        {
            "name": "Expense Analysis Query", 
            "query": "Which expense categories increased the most this year?",
            "expected_status": 200
        },
        {
            "name": "Comparison Query",
            "query": "Compare Q1 and Q2 performance",
            "expected_status": 200
        },
        {
            "name": "Trend Analysis Query",
            "query": "Show me revenue trends for the last 6 months",
            "expected_status": 200
        },
        {
            "name": "Empty Query",
            "query": "",
            "expected_status": 422
        },
        {
            "name": "Very Long Query",
            "query": "A" * 1001,  # Exceeds max length
            "expected_status": 422
        }
    ]
    
    # Test each case
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['name']}")
        print("-" * 30)
        
        payload = {
            "query": test_case["query"],
            "max_iterations": 3,
            "include_raw_data": True
        }
        
        try:
            start_time = time.time()
            response = requests.post(endpoint, json=payload, timeout=30)
            response_time = time.time() - start_time
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Time: {response_time:.3f}s")
            
            if response.status_code == test_case["expected_status"]:
                print("✅ Status code matches expected")
            else:
                print(f"❌ Expected {test_case['expected_status']}, got {response.status_code}")
            
            # Parse response
            try:
                response_data = response.json()
                print(f"Response Keys: {list(response_data.keys())}")
                
                if response.status_code == 200:
                    # Validate successful response structure
                    required_keys = ["answer", "supporting_data", "conversation_id", "query_metadata"]
                    missing_keys = [key for key in required_keys if key not in response_data]
                    
                    if not missing_keys:
                        print("✅ Response structure is valid")
                        
                        # Print FULL answer
                        print(f"\n📝 COMPLETE ANSWER:")
                        print("=" * 60)
                        print(response_data['answer'])
                        print("=" * 60)
                        
                        # Check metadata
                        metadata = response_data.get("query_metadata", {})
                        print(f"\n📊 METADATA:")
                        print(f"Processing Time: {metadata.get('processing_time_seconds', 'N/A')}s")
                        print(f"Tools Used: {metadata.get('tools_used', 'N/A')}")
                        print(f"Iterations: {metadata.get('iterations', 'N/A')}")
                        
                        # Check supporting data
                        supporting_data = response_data.get("supporting_data", {})
                        analysis_summary = supporting_data.get("analysis_summary", {})
                        print(f"Data Sources: {analysis_summary.get('data_sources', [])}")
                        print(f"Tools Executed: {analysis_summary.get('tools_executed', 0)}")
                        
                        # Print suggestions
                        suggestions = response_data.get("suggestions", [])
                        if suggestions:
                            print(f"\n💡 SUGGESTED FOLLOW-UP QUESTIONS:")
                            for i, suggestion in enumerate(suggestions, 1):
                                print(f"   {i}. {suggestion}")
                        
                        # Print supporting data details
                        print(f"\n🔧 SUPPORTING DATA:")
                        print(f"Analysis Summary: {analysis_summary}")
                        
                    else:
                        print(f"❌ Missing required keys: {missing_keys}")
                        
                else:
                    # Check error response structure
                    if "detail" in response_data:
                        detail = response_data["detail"]
                        if isinstance(detail, dict):
                            print(f"Error Type: {detail.get('error', 'N/A')}")
                            print(f"Error Message: {detail.get('message', 'N/A')}")
                            if detail.get('fallback_response'):
                                print(f"Fallback: {detail['fallback_response'][:100]}...")
                        else:
                            print(f"Error Detail: {detail}")
                    
            except json.JSONDecodeError:
                print("❌ Invalid JSON response")
                print(f"Raw Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {str(e)}")
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
    
    # Test conversation context
    print(f"\n\nTest: Conversation Context")
    print("-" * 30)
    
    try:
        # First query
        payload1 = {
            "query": "What was the revenue in Q1 2024?",
            "max_iterations": 3
        }
        
        response1 = requests.post(endpoint, json=payload1, timeout=30)
        if response1.status_code == 200:
            data1 = response1.json()
            conversation_id = data1.get("conversation_id")
            print(f"✅ First query successful, conversation_id: {conversation_id}")
            
            # Follow-up query with same conversation ID
            payload2 = {
                "query": "How does that compare to Q2?",
                "conversation_id": conversation_id,
                "max_iterations": 3
            }
            
            response2 = requests.post(endpoint, json=payload2, timeout=30)
            if response2.status_code == 200:
                data2 = response2.json()
                if data2.get("conversation_id") == conversation_id:
                    print("✅ Conversation context maintained")
                else:
                    print("❌ Conversation context not maintained")
            else:
                print(f"❌ Follow-up query failed: {response2.status_code}")
        else:
            print(f"❌ First query failed: {response1.status_code}")
            
    except Exception as e:
        print(f"❌ Conversation test failed: {str(e)}")
    
    print(f"\n\nTesting complete!")


if __name__ == "__main__":
    test_query_endpoint()