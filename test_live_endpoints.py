"""
Test script to verify live API endpoints are working.
Run this while the server is running on localhost:8000
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def test_endpoint(method, endpoint, params=None, expected_status=200):
    """Test a single endpoint and return the result."""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=10)
        else:
            response = requests.request(method, url, params=params, timeout=10)
        
        print(f"✓ {method} {endpoint} -> {response.status_code}")
        
        if response.status_code == expected_status:
            if response.headers.get('content-type', '').startswith('application/json'):
                data = response.json()
                if isinstance(data, dict):
                    if 'data' in data:
                        print(f"  Records returned: {len(data['data'])}")
                    if 'total_count' in data:
                        print(f"  Total count: {data['total_count']}")
                    if 'total_revenue' in data:
                        print(f"  Revenue: ${data['total_revenue']:,.2f}")
                return True, data
            return True, response.text
        else:
            print(f"  ✗ Expected {expected_status}, got {response.status_code}")
            print(f"  Response: {response.text[:200]}...")
            return False, None
            
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        return False, None

def main():
    print("=" * 60)
    print("TESTING LIVE API ENDPOINTS")
    print("=" * 60)
    
    # Test basic health check
    print("\n1. Health Check:")
    test_endpoint("GET", "/health")
    
    # Test financial data endpoints
    print("\n2. Financial Data Endpoints:")
    
    # Basic financial data
    test_endpoint("GET", "/api/v1/financial-data/")
    
    # With pagination
    test_endpoint("GET", "/api/v1/financial-data/", {"page": 1, "page_size": 5})
    
    # With filters
    test_endpoint("GET", "/api/v1/financial-data/", {"source": "quickbooks", "page_size": 3})
    test_endpoint("GET", "/api/v1/financial-data/", {"currency": "USD", "page_size": 3})
    
    # Period-specific data
    print("\n3. Period-Specific Data:")
    test_endpoint("GET", "/api/v1/financial-data/2024")
    test_endpoint("GET", "/api/v1/financial-data/2024-Q1")
    test_endpoint("GET", "/api/v1/financial-data/2024-01")
    
    # Account endpoints
    print("\n4. Account Endpoints:")
    
    # All accounts
    success, data = test_endpoint("GET", "/api/v1/financial-data/accounts/")
    
    # Filtered accounts
    test_endpoint("GET", "/api/v1/financial-data/accounts/", {"account_type": "revenue"})
    test_endpoint("GET", "/api/v1/financial-data/accounts/", {"account_type": "expense"})
    
    # Individual account (if we have account data)
    if success and data and data.get('data'):
        account_id = data['data'][0]['account_id']
        print(f"\n5. Individual Account ({account_id}):")
        test_endpoint("GET", f"/api/v1/financial-data/accounts/{account_id}")
        test_endpoint("GET", f"/api/v1/financial-data/accounts/{account_id}/hierarchy")
    
    # Test error handling
    print("\n6. Error Handling:")
    test_endpoint("GET", "/api/v1/financial-data/accounts/invalid-id", expected_status=404)
    test_endpoint("GET", "/api/v1/financial-data/invalid-period", expected_status=500)
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)
    print("\nYou can also test interactively at:")
    print("- Swagger UI: http://127.0.0.1:8000/docs")
    print("- ReDoc: http://127.0.0.1:8000/redoc")

if __name__ == "__main__":
    main()