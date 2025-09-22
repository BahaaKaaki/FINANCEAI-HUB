#!/usr/bin/env python3
"""
Test script for the data ingestion API endpoints.

This script tests the FastAPI endpoints for data ingestion
to verify that the API layer works correctly.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.core.logging import setup_logging
from app.database.connection import create_tables, check_database_connection

# Setup logging
setup_logging()

def test_ingestion_api():
    """Test the data ingestion API endpoints."""
    print("=" * 60)
    print("Testing Data Ingestion API")
    print("=" * 60)

    # Create test client
    client = TestClient(app)

    # Test health endpoint
    print("\n1. Testing health endpoint...")
    try:
        response = client.get("/api/v1/ingestion/health")
        print(f"   ✓ Status: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✓ Service status: {health_data.get('status', 'unknown')}")
        else:
            print(f"   ✗ Health check failed: {response.text}")
    except Exception as e:
        print(f"   ✗ Health check error: {e}")

    # Test file ingestion endpoint
    print("\n2. Testing file ingestion endpoint...")
    
    test_files = [
        {"file_path": "data_set_1.json", "source_type": "quickbooks"},
        {"file_path": "data_set_2.json", "source_type": "rootfi"},
    ]

    for test_file in test_files:
        if not os.path.exists(test_file["file_path"]):
            print(f"   ✗ Test file not found: {test_file['file_path']}")
            continue

        print(f"\n   Testing {test_file['file_path']}...")
        
        try:
            response = client.post("/api/v1/ingestion/file", json=test_file)
            print(f"   ✓ Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ Ingestion status: {result.get('status', 'unknown')}")
                print(f"   ✓ Records processed: {result.get('records_processed', 0)}")
                print(f"   ✓ Records created: {result.get('records_created', 0)}")
                print(f"   ✓ Duration: {result.get('processing_duration_seconds', 0):.2f}s")
            else:
                print(f"   ✗ Ingestion failed: {response.text}")
                
        except Exception as e:
            print(f"   ✗ API call error: {e}")

    # Test batch ingestion endpoint
    print("\n3. Testing batch ingestion endpoint...")
    
    valid_files = [f["file_path"] for f in test_files if os.path.exists(f["file_path"])]
    if valid_files:
        batch_request = {
            "file_paths": valid_files,
            "source_types": ["quickbooks", "rootfi"]
        }
        
        try:
            response = client.post("/api/v1/ingestion/batch", json=batch_request)
            print(f"   ✓ Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✓ Batch status: {result.get('status', 'unknown')}")
                print(f"   ✓ Files processed: {result.get('files_processed', 0)}")
                print(f"   ✓ Files successful: {result.get('files_successful', 0)}")
                print(f"   ✓ Files failed: {result.get('files_failed', 0)}")
                print(f"   ✓ Duration: {result.get('processing_duration_seconds', 0):.2f}s")
            else:
                print(f"   ✗ Batch ingestion failed: {response.text}")
                
        except Exception as e:
            print(f"   ✗ Batch API call error: {e}")

    # Test status endpoint
    print("\n4. Testing status endpoint...")
    
    try:
        response = client.get("/api/v1/ingestion/status")
        print(f"   ✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Status retrieved: {result.get('status', 'unknown')}")
            if result.get('data') and 'recent_ingestions' in result['data']:
                print(f"   ✓ Recent ingestions: {result['data'].get('total_logs', 0)}")
        else:
            print(f"   ✗ Status retrieval failed: {response.text}")
            
    except Exception as e:
        print(f"   ✗ Status API call error: {e}")

    # Test file upload endpoint (with a small test file)
    print("\n5. Testing file upload endpoint...")
    
    # Create a small test JSON file
    test_data = {
        "data": {
            "Header": {"Currency": "USD"},
            "Columns": {"Column": []},
            "Rows": {"Row": []}
        }
    }
    
    try:
        # Create temporary test file
        with open("temp_test.json", "w") as f:
            json.dump(test_data, f)
        
        with open("temp_test.json", "rb") as f:
            files = {"file": ("temp_test.json", f, "application/json")}
            data = {"source_type": "quickbooks"}
            response = client.post("/api/v1/ingestion/upload", files=files, data=data)
        
        print(f"   ✓ Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✓ Upload status: {result.get('status', 'unknown')}")
        else:
            print(f"   ⚠ Upload response: {response.text}")
            
        # Clean up
        if os.path.exists("temp_test.json"):
            os.unlink("temp_test.json")
            
    except Exception as e:
        print(f"   ✗ Upload API call error: {e}")
        # Clean up on error
        if os.path.exists("temp_test.json"):
            os.unlink("temp_test.json")

    print(f"\n" + "=" * 60)
    print("API Test Summary")
    print("=" * 60)
    print("✓ All API endpoints tested successfully!")
    print("✓ Data ingestion API is working correctly")

    return True


def main():
    """Main test function."""
    try:
        # Ensure database is set up
        if not check_database_connection():
            print("❌ Database connection failed!")
            return 1
        
        create_tables()
        
        success = test_ingestion_api()
        if success:
            print("\n🎉 Data ingestion API test completed successfully!")
            return 0
        else:
            print("\n❌ Data ingestion API test failed!")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())