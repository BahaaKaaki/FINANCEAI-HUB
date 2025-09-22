"""
Script to ingest both datasets using the ingestion service.
"""

from app.services.ingestion import DataIngestionService
from app.models.financial import SourceType

def main():
    print("Starting data ingestion for both datasets...")
    
    # Initialize the ingestion service
    service = DataIngestionService()
    
    # Ingest QuickBooks data
    print("\n1. Ingesting QuickBooks data (data_set_1.json)...")
    try:
        qb_result = service.ingest_file("data_set_1.json", SourceType.QUICKBOOKS)
        print(f"✅ QuickBooks ingestion: {qb_result.status}")
        print(f"   Records processed: {qb_result.records_processed}")
        print(f"   Records created: {qb_result.records_created}")
        print(f"   Duration: {qb_result.processing_duration_seconds:.2f}s")
    except Exception as e:
        print(f"❌ QuickBooks ingestion failed: {e}")
    
    # Ingest Rootfi data
    print("\n2. Ingesting Rootfi data (data_set_2.json)...")
    try:
        rootfi_result = service.ingest_file("data_set_2.json", SourceType.ROOTFI)
        print(f"✅ Rootfi ingestion: {rootfi_result.status}")
        print(f"   Records processed: {rootfi_result.records_processed}")
        print(f"   Records created: {rootfi_result.records_created}")
        print(f"   Duration: {rootfi_result.processing_duration_seconds:.2f}s")
    except Exception as e:
        print(f"❌ Rootfi ingestion failed: {e}")
    
    # Batch ingestion alternative
    print("\n3. Alternative: Batch ingestion...")
    try:
        batch_result = service.ingest_batch(
            ["data_set_1.json", "data_set_2.json"],
            [SourceType.QUICKBOOKS, SourceType.ROOTFI]
        )
        print(f"✅ Batch ingestion: {batch_result.status}")
        print(f"   Files successful: {batch_result.files_successful}")
        print(f"   Files failed: {batch_result.files_failed}")
        print(f"   Total records: {batch_result.total_records_processed}")
    except Exception as e:
        print(f"❌ Batch ingestion failed: {e}")
    
    print("\n🎉 Data ingestion complete!")

if __name__ == "__main__":
    main()