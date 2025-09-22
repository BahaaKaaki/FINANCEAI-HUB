"""
Test script for financial data API endpoints.

Tests all the core financial data API endpoints to ensure they work correctly
with the existing database and data.
"""

import asyncio
import json
from datetime import date, datetime
from decimal import Decimal

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db_session
from app.database.models import AccountDB, AccountValueDB, FinancialRecordDB
from app.models.financial import AccountType, SourceType

# Create test client
client = TestClient(app)


def test_basic_health_check():
    """Test that the application is running."""
    print("Testing basic health check...")
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health check passed")


def test_get_financial_data_basic():
    """Test basic financial data retrieval."""
    print("\nTesting basic financial data retrieval...")
    response = client.get("/api/v1/financial-data/")
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Retrieved {len(data['data'])} financial records")
        print(f"  Total count: {data['total_count']}")
        print(f"  Pagination: {data['pagination']}")
        
        if data['data']:
            record = data['data'][0]
            print(f"  Sample record: {record['id']} - {record['source']} - {record['currency']}")
    else:
        print(f"✗ Failed with status {response.status_code}: {response.text}")


def test_get_financial_data_with_filters():
    """Test financial data retrieval with filters."""
    print("\nTesting financial data with filters...")
    
    # Test with source filter
    response = client.get("/api/v1/financial-data/?source=quickbooks&page_size=5")
    print(f"QuickBooks filter - Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ QuickBooks records: {len(data['data'])}")
        if data['data']:
            print(f"  All records are QuickBooks: {all(r['source'] == 'quickbooks' for r in data['data'])}")
    
    # Test with currency filter
    response = client.get("/api/v1/financial-data/?currency=USD&page_size=5")
    print(f"USD filter - Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ USD records: {len(data['data'])}")
        if data['data']:
            print(f"  All records are USD: {all(r['currency'] == 'USD' for r in data['data'])}")


def test_get_financial_data_pagination():
    """Test financial data pagination."""
    print("\nTesting financial data pagination...")
    
    # Get first page
    response = client.get("/api/v1/financial-data/?page=1&page_size=2")
    print(f"Page 1 - Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Page 1: {len(data['data'])} records")
        print(f"  Has next: {data['pagination']['has_next']}")
        print(f"  Total pages: {data['pagination']['total_pages']}")
        
        # Get second page if available
        if data['pagination']['has_next']:
            response2 = client.get("/api/v1/financial-data/?page=2&page_size=2")
            if response2.status_code == 200:
                data2 = response2.json()
                print(f"✓ Page 2: {len(data2['data'])} records")


def test_get_period_data():
    """Test period-specific data retrieval."""
    print("\nTesting period-specific data retrieval...")
    
    # Test different period formats
    periods_to_test = ["2024", "2024-Q1", "2024-01"]
    
    for period in periods_to_test:
        response = client.get(f"/api/v1/financial-data/{period}")
        print(f"Period {period} - Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Period {period}: Revenue={data['total_revenue']}, Expenses={data['total_expenses']}")
            print(f"  Records: {data['record_count']}, Sources: {data['sources']}")
        elif response.status_code == 404:
            print(f"  No data found for period {period}")
        else:
            print(f"✗ Error: {response.text}")


def test_get_accounts():
    """Test account retrieval."""
    print("\nTesting account retrieval...")
    
    response = client.get("/api/v1/financial-data/accounts/")
    print(f"All accounts - Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✓ Retrieved {len(data['data'])} accounts")
        print(f"  Total count: {data['total_count']}")
        
        if data['data']:
            account = data['data'][0]
            print(f"  Sample account: {account['account_id']} - {account['name']} ({account['account_type']})")
            
            # Test filtering by account type
            account_types = ["revenue", "expense"]
            for acc_type in account_types:
                response2 = client.get(f"/api/v1/financial-data/accounts/?account_type={acc_type}")
                if response2.status_code == 200:
                    data2 = response2.json()
                    print(f"  {acc_type.title()} accounts: {len(data2['data'])}")


def test_get_account_by_id():
    """Test individual account retrieval."""
    print("\nTesting individual account retrieval...")
    
    # First get a list of accounts to find a valid ID
    response = client.get("/api/v1/financial-data/accounts/?page_size=1")
    
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            account_id = data['data'][0]['account_id']
            
            # Test getting specific account
            response2 = client.get(f"/api/v1/financial-data/accounts/{account_id}")
            print(f"Account {account_id} - Status: {response2.status_code}")
            
            if response2.status_code == 200:
                account_data = response2.json()
                print(f"✓ Retrieved account: {account_data['name']} ({account_data['account_type']})")
            else:
                print(f"✗ Failed to retrieve account: {response2.text}")
        else:
            print("  No accounts available to test individual retrieval")
    else:
        print(f"  Failed to get account list: {response.status_code}")


def test_get_account_hierarchy():
    """Test account hierarchy retrieval."""
    print("\nTesting account hierarchy retrieval...")
    
    # First get accounts to find one with potential children
    response = client.get("/api/v1/financial-data/accounts/?page_size=5")
    
    if response.status_code == 200:
        data = response.json()
        if data['data']:
            # Try the first few accounts for hierarchy
            for account in data['data'][:3]:
                account_id = account['account_id']
                
                response2 = client.get(f"/api/v1/financial-data/accounts/{account_id}/hierarchy")
                print(f"Hierarchy for {account_id} - Status: {response2.status_code}")
                
                if response2.status_code == 200:
                    hierarchy_data = response2.json()
                    print(f"✓ Account: {hierarchy_data['account']['name']}")
                    print(f"  Children: {len(hierarchy_data['children'])}")
                    print(f"  Values: {len(hierarchy_data['values'])}")
                    break  # Test just one successful hierarchy
                elif response2.status_code == 404:
                    print(f"  Account {account_id} not found")
                else:
                    print(f"  Error: {response2.text}")
        else:
            print("  No accounts available to test hierarchy")


def test_error_handling():
    """Test error handling for invalid requests."""
    print("\nTesting error handling...")
    
    # Test invalid account ID
    response = client.get("/api/v1/financial-data/accounts/invalid-account-id")
    print(f"Invalid account ID - Status: {response.status_code}")
    if response.status_code == 404:
        print("✓ Correctly returned 404 for invalid account ID")
    
    # Test invalid period format
    response = client.get("/api/v1/financial-data/invalid-period")
    print(f"Invalid period - Status: {response.status_code}")
    if response.status_code in [400, 422]:
        print("✓ Correctly returned error for invalid period")
    
    # Test invalid pagination
    response = client.get("/api/v1/financial-data/?page=0")
    print(f"Invalid pagination - Status: {response.status_code}")
    if response.status_code == 422:
        print("✓ Correctly returned 422 for invalid pagination")


def run_all_tests():
    """Run all test functions."""
    print("=" * 60)
    print("FINANCIAL DATA API ENDPOINT TESTS")
    print("=" * 60)
    
    try:
        test_basic_health_check()
        test_get_financial_data_basic()
        test_get_financial_data_with_filters()
        test_get_financial_data_pagination()
        test_get_period_data()
        test_get_accounts()
        test_get_account_by_id()
        test_get_account_hierarchy()
        test_error_handling()
        
        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test execution failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()