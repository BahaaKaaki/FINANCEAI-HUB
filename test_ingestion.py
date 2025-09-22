#!/usr/bin/env python3
"""
Test script for the data ingestion service.

This script tests the ingestion service with the sample data files
to verify that the implementation works correctly.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.logging import setup_logging
from app.database.connection import create_tables, check_database_connection
from app.services.ingestion import DataIngestionService
from app.models.financial import SourceType

# Setup logging
setup_logging()

async def test_ingestion_service():
    """Test the data ingestion service with sample files."""
    print("=" * 60)
    print("Testing Data Ingestion Service")
    print("=" * 60)

    # Initialize the ingestion service
    ingestion_service = DataIngestionService()

    # Check database connection
    print("\n1. Checking database connection...")
    if check_database_connection():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
        return False

    # Create tables if they don't exist
    print("\n2. Creating database tables...")
    try:
        create_tables()
        print("✓ Database tables created/verified")
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return False

    # Test files
    test_files = [
        ("data_set_1.json", SourceType.QUICKBOOKS),
        ("data_set_2.json", SourceType.ROOTFI),
    ]

    print(f"\n3. Testing file ingestion ({len(test_files)} files)...")
    
    results = []
    for file_path, source_type in test_files:
        if not os.path.exists(file_path):
            print(f"✗ Test file not found: {file_path}")
            continue

        print(f"\n   Testing {file_path} ({source_type})...")
        
        try:
            result = ingestion_service.ingest_file(file_path, source_type)
            results.append(result)
            
            print(f"   ✓ Status: {result.status}")
            print(f"   ✓ Records processed: {result.records_processed}")
            print(f"   ✓ Records created: {result.records_created}")
            print(f"   ✓ Records updated: {result.records_updated}")
            print(f"   ✓ Duration: {result.processing_duration_seconds:.2f}s")
            
            if result.validation_result:
                print(f"   ✓ Validation score: {result.validation_result.quality_score:.2f}")
                if result.validation_result.issues:
                    print(f"   ⚠ Validation issues: {len(result.validation_result.issues)}")
            
            if result.error_message:
                print(f"   ⚠ Error: {result.error_message}")
                
        except Exception as e:
            print(f"   ✗ Failed to ingest {file_path}: {e}")
            results.append(None)

    # Test batch ingestion
    print(f"\n4. Testing batch ingestion...")
    
    valid_files = [f for f, _ in test_files if os.path.exists(f)]
    if valid_files:
        try:
            batch_result = ingestion_service.ingest_batch(valid_files)
            
            print(f"   ✓ Batch ID: {batch_result.batch_id}")
            print(f"   ✓ Status: {batch_result.status}")
            print(f"   ✓ Files processed: {batch_result.files_processed}")
            print(f"   ✓ Files successful: {batch_result.files_successful}")
            print(f"   ✓ Files failed: {batch_result.files_failed}")
            print(f"   ✓ Total records: {batch_result.total_records_processed}")
            print(f"   ✓ Duration: {batch_result.processing_duration_seconds:.2f}s")
            
        except Exception as e:
            print(f"   ✗ Batch ingestion failed: {e}")

    # Test status retrieval
    print(f"\n5. Testing status retrieval...")
    
    try:
        status = ingestion_service.get_ingestion_status()
        print(f"   ✓ Status retrieved successfully")
        if "recent_ingestions" in status:
            print(f"   ✓ Recent ingestions: {status['total_logs']}")
        
    except Exception as e:
        print(f"   ✗ Status retrieval failed: {e}")

    # Summary
    print(f"\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    successful_files = sum(1 for r in results if r and r.status.value == "completed")
    total_files = len([r for r in results if r is not None])
    
    print(f"Files tested: {len(test_files)}")
    print(f"Files processed: {total_files}")
    print(f"Files successful: {successful_files}")
    print(f"Success rate: {(successful_files/total_files*100) if total_files > 0 else 0:.1f}%")

    return successful_files > 0


def main():
    """Main test function."""
    try:
        success = asyncio.run(test_ingestion_service())
        if success:
            print("\n🎉 Data ingestion service test completed successfully!")
            return 0
        else:
            print("\n❌ Data ingestion service test failed!")
            return 1
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())