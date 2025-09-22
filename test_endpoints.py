#!/usr/bin/env python3
"""
Simple test script to verify the new API documentation endpoints work correctly.
"""

import sys
import traceback
from app.main import app
from fastapi.testclient import TestClient

def test_endpoints():
    """Test the new API documentation endpoints."""
    client = TestClient(app)
    
    tests = [
        ("Health endpoint", "GET", "/api/v1/health"),
        ("Documentation examples", "GET", "/api/v1/docs/examples"),
        ("Integration guides", "GET", "/api/v1/docs/integration-guides"),
        ("API reference", "GET", "/api/v1/docs/api-reference"),
        ("FastAPI docs", "GET", "/docs"),
        ("Root endpoint", "GET", "/"),
    ]
    
    results = []
    
    for test_name, method, endpoint in tests:
        try:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.request(method, endpoint)
            
            status = "✅ PASS" if response.status_code == 200 else f"❌ FAIL ({response.status_code})"
            results.append(f"{status} - {test_name}: {endpoint}")
            
        except Exception as e:
            results.append(f"❌ ERROR - {test_name}: {endpoint} - {str(e)}")
    
    return results

if __name__ == "__main__":
    print("Testing API Documentation Endpoints...")
    print("=" * 50)
    
    try:
        results = test_endpoints()
        for result in results:
            print(result)
        
        # Check if all tests passed
        failed_tests = [r for r in results if "❌" in r]
        if failed_tests:
            print(f"\n{len(failed_tests)} test(s) failed.")
            sys.exit(1)
        else:
            print(f"\nAll {len(results)} tests passed! 🎉")
            
    except Exception as e:
        print(f"Error running tests: {e}")
        traceback.print_exc()
        sys.exit(1)