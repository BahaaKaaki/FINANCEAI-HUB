"""
End-to-end integration tests for complete data ingestion workflow.

Tests the complete flow from raw data files through parsing, validation,
normalization, and storage in the database.
"""

import json
import os
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.database.connection import create_tables, get_db_session, get_engine
from app.database.models import (
    AccountDB,
    AccountValueDB,
    DataIngestionLogDB,
    FinancialRecordDB,
)
from app.models.financial import SourceType
from app.services.ingestion import DataIngestionService, IngestionStatus


@pytest.fixture(scope="function")
def clean_database():
    """Clean database before and after each test."""
    engine = get_engine()
    from app.database.models import Base
    
    # Clean before test
    Base.metadata.drop_all(bind=engine)
    create_tables(engine)
    
    yield
    
    # Clean after test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_quickbooks_data():
    """Sample QuickBooks data for testing."""
    return {
        "data": {
            "Header": {
                "Time": "2024-01-31T23:59:59",
                "ReportName": "ProfitAndLoss",
                "Currency": "USD",
                "StartPeriod": "2024-01-01",
                "EndPeriod": "2024-01-31"
            },
            "Columns": [
                {"ColTitle": "", "ColType": "Account"},
                {"ColTitle": "Jan 2024", "ColType": "Money"}
            ],
            "Rows": [
                {
                    "group": "Income",
                    "ColData": [
                        {"value": "Total Income", "id": ""},
                        {"value": "25000.00"}
                    ]
                },
                {
                    "group": "Income",
                    "ColData": [
                        {"value": "Product Sales", "id": "qb-revenue-001"},
                        {"value": "20000.00"}
                    ]
                },
                {
                    "group": "Income", 
                    "ColData": [
                        {"value": "Service Revenue", "id": "qb-revenue-002"},
                        {"value": "5000.00"}
                    ]
                },
                {
                    "group": "Expense",
                    "ColData": [
                        {"value": "Total Expenses", "id": ""},
                        {"value": "18000.00"}
                    ]
                },
                {
                    "group": "Expense",
                    "ColData": [
                        {"value": "Operating Expenses", "id": "qb-expense-001"},
                        {"value": "12000.00"}
                    ]
                },
                {
                    "group": "Expense",
                    "ColData": [
                        {"value": "Marketing Costs", "id": "qb-expense-002"},
                        {"value": "6000.00"}
                    ]
                }
            ]
        }
    }


@pytest.fixture
def sample_rootfi_data():
    """Sample Rootfi data for testing."""
    return {
        "data": [
            {
                "rootfi_id": "rf-001",
                "period_start": "2024-01-01",
                "period_end": "2024-01-31",
                "currency": "USD",
                "revenue": [
                    {
                        "account_id": "rf-revenue-001",
                        "name": "Sales Revenue",
                        "type": "operating_revenue",
                        "value": 22000.00,
                        "description": "Primary sales revenue"
                    }
                ],
                "expenses": [
                    {
                        "account_id": "rf-expense-001", 
                        "name": "Operating Costs",
                        "type": "operating_expenses",
                        "value": 16000.00,
                        "description": "General operating costs"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def temp_data_files(sample_quickbooks_data, sample_rootfi_data):
    """Create temporary data files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create QuickBooks file
        qb_file = Path(temp_dir) / "quickbooks_test.json"
        with open(qb_file, 'w') as f:
            json.dump(sample_quickbooks_data, f)
        
        # Create Rootfi file
        rf_file = Path(temp_dir) / "rootfi_test.json"
        with open(rf_file, 'w') as f:
            json.dump(sample_rootfi_data, f)
        
        yield {
            "quickbooks": str(qb_file),
            "rootfi": str(rf_file),
            "temp_dir": temp_dir
        }


class TestEndToEndIngestion:
    """End-to-end integration tests for data ingestion workflow."""
    
    def test_complete_quickbooks_ingestion_workflow(self, clean_database, temp_data_files):
        """Test complete QuickBooks data ingestion from file to database."""
        service = DataIngestionService()
        
        # Ingest the QuickBooks file
        result = service.ingest_file(
            temp_data_files["quickbooks"], 
            SourceType.QUICKBOOKS
        )
        
        # Verify ingestion result
        assert result.status == IngestionStatus.COMPLETED
        assert result.source_type == SourceType.QUICKBOOKS
        assert result.records_processed > 0
        assert result.records_created > 0
        assert result.validation_result is not None
        assert result.validation_result.is_valid
        assert result.processing_duration_seconds is not None
        assert result.processing_duration_seconds > 0
        
        # Verify data was stored in database
        with get_db_session() as session:
            # Check financial records
            financial_records = session.query(FinancialRecordDB).all()
            assert len(financial_records) == 1
            
            record = financial_records[0]
            assert record.source == SourceType.QUICKBOOKS.value
            assert record.period_start == date(2024, 1, 1)
            assert record.period_end == date(2024, 1, 31)
            assert record.currency == "USD"
            assert record.revenue == Decimal("25000.00")
            assert record.expenses == Decimal("18000.00")
            assert record.net_profit == Decimal("7000.00")
            assert record.raw_data is not None
            
            # Check accounts were created
            accounts = session.query(AccountDB).all()
            assert len(accounts) >= 4  # At least revenue and expense accounts
            
            revenue_accounts = [acc for acc in accounts if acc.account_type == "revenue"]
            expense_accounts = [acc for acc in accounts if acc.account_type == "expense"]
            assert len(revenue_accounts) >= 2
            assert len(expense_accounts) >= 2
            
            # Check account values
            account_values = session.query(AccountValueDB).all()
            assert len(account_values) >= 4
            
            # Verify specific account values
            product_sales = next(
                (av for av in account_values 
                 if av.account_id == "qb-revenue-001"), None
            )
            assert product_sales is not None
            assert product_sales.value == Decimal("20000.00")
            
            # Check ingestion log was created
            logs = session.query(DataIngestionLogDB).all()
            assert len(logs) == 1
            
            log = logs[0]
            assert log.source == SourceType.QUICKBOOKS.value
            assert log.filename == "quickbooks_test.json"
            assert log.status == IngestionStatus.COMPLETED.value
            assert log.records_processed > 0
            assert log.records_created > 0
            assert log.started_at is not None
            assert log.completed_at is not None
            assert log.processing_duration_seconds is not None
    
    def test_complete_rootfi_ingestion_workflow(self, clean_database, temp_data_files):
        """Test complete Rootfi data ingestion from file to database."""
        service = DataIngestionService()
        
        # Ingest the Rootfi file
        result = service.ingest_file(
            temp_data_files["rootfi"],
            SourceType.ROOTFI
        )
        
        # Verify ingestion result
        assert result.status == IngestionStatus.COMPLETED
        assert result.source_type == SourceType.ROOTFI
        assert result.records_processed > 0
        assert result.records_created > 0
        assert result.validation_result is not None
        assert result.validation_result.is_valid
        
        # Verify data was stored in database
        with get_db_session() as session:
            # Check financial records
            financial_records = session.query(FinancialRecordDB).all()
            assert len(financial_records) == 1
            
            record = financial_records[0]
            assert record.source == SourceType.ROOTFI.value
            assert record.period_start == date(2024, 1, 1)
            assert record.period_end == date(2024, 1, 31)
            assert record.currency == "USD"
            assert record.revenue == Decimal("22000.00")
            assert record.expenses == Decimal("16000.00")
            assert record.net_profit == Decimal("6000.00")
            
            # Check accounts were created
            accounts = session.query(AccountDB).all()
            assert len(accounts) >= 2
            
            # Check account values
            account_values = session.query(AccountValueDB).all()
            assert len(account_values) >= 2
    
    def test_batch_ingestion_workflow(self, clean_database, temp_data_files):
        """Test batch ingestion of multiple files."""
        service = DataIngestionService()
        
        # Ingest both files in batch
        file_paths = [temp_data_files["quickbooks"], temp_data_files["rootfi"]]
        source_types = [SourceType.QUICKBOOKS, SourceType.ROOTFI]
        
        result = service.ingest_batch(file_paths, source_types)
        
        # Verify batch result
        assert result.status == IngestionStatus.COMPLETED
        assert result.files_processed == 2
        assert result.files_successful == 2
        assert result.files_failed == 0
        assert result.total_records_processed >= 2
        assert result.total_records_created >= 2
        assert result.processing_duration_seconds is not None
        assert len(result.file_results) == 2
        
        # Verify individual file results
        qb_result = next(
            (fr for fr in result.file_results 
             if fr.filename == "quickbooks_test.json"), None
        )
        assert qb_result is not None
        assert qb_result.status == IngestionStatus.COMPLETED
        assert qb_result.source_type == SourceType.QUICKBOOKS
        
        rf_result = next(
            (fr for fr in result.file_results 
             if fr.filename == "rootfi_test.json"), None
        )
        assert rf_result is not None
        assert rf_result.status == IngestionStatus.COMPLETED
        assert rf_result.source_type == SourceType.ROOTFI
        
        # Verify data from both sources is in database
        with get_db_session() as session:
            financial_records = session.query(FinancialRecordDB).all()
            assert len(financial_records) == 2
            
            sources = [record.source for record in financial_records]
            assert SourceType.QUICKBOOKS.value in sources
            assert SourceType.ROOTFI.value in sources
            
            # Check that accounts from both sources exist
            accounts = session.query(AccountDB).all()
            account_sources = [account.source for account in accounts]
            assert SourceType.QUICKBOOKS.value in account_sources
            assert SourceType.ROOTFI.value in account_sources
    
    def test_ingestion_with_invalid_file(self, clean_database):
        """Test ingestion workflow with invalid file."""
        service = DataIngestionService()
        
        # Create invalid JSON file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json content}')  # Invalid JSON
            invalid_file = f.name
        
        try:
            result = service.ingest_file(invalid_file, SourceType.QUICKBOOKS)
            
            # Should fail with parsing error
            assert result.status == IngestionStatus.FAILED
            assert result.error_message is not None
            assert "error" in result.error_message.lower()
            assert result.records_processed == 0
            assert result.records_created == 0
            
            # Verify no data was stored
            with get_db_session() as session:
                financial_records = session.query(FinancialRecordDB).all()
                assert len(financial_records) == 0
                
                # But ingestion log should exist
                logs = session.query(DataIngestionLogDB).all()
                assert len(logs) == 1
                assert logs[0].status == IngestionStatus.FAILED.value
                
        finally:
            os.unlink(invalid_file)
    
    def test_ingestion_status_tracking(self, clean_database, temp_data_files):
        """Test ingestion status tracking and retrieval."""
        service = DataIngestionService()
        
        # Ingest a file
        service.ingest_file(temp_data_files["quickbooks"], SourceType.QUICKBOOKS)
        
        # Get ingestion status
        status = service.get_ingestion_status()
        
        assert "recent_ingestions" in status
        assert "total_logs" in status
        assert status["total_logs"] >= 1
        
        recent_logs = status["recent_ingestions"]
        assert len(recent_logs) >= 1
        
        latest_log = recent_logs[0]
        assert latest_log["source"] == SourceType.QUICKBOOKS.value
        assert latest_log["filename"] == "quickbooks_test.json"
        assert latest_log["status"] == IngestionStatus.COMPLETED.value
        assert latest_log["records_processed"] > 0
        assert latest_log["records_created"] > 0
        assert latest_log["started_at"] is not None
        assert latest_log["completed_at"] is not None
        assert latest_log["processing_duration_seconds"] is not None
    
    def test_duplicate_data_handling(self, clean_database, temp_data_files):
        """Test handling of duplicate data ingestion."""
        service = DataIngestionService()
        
        # Ingest the same file twice
        result1 = service.ingest_file(temp_data_files["quickbooks"], SourceType.QUICKBOOKS)
        result2 = service.ingest_file(temp_data_files["quickbooks"], SourceType.QUICKBOOKS)
        
        # Both should succeed
        assert result1.status == IngestionStatus.COMPLETED
        assert result2.status == IngestionStatus.COMPLETED
        
        # Second ingestion should update existing records
        assert result1.records_created > 0
        assert result2.records_created == 0  # No new records created
        assert result2.records_updated > 0   # Existing records updated
        
        # Verify only one set of records exists in database
        with get_db_session() as session:
            financial_records = session.query(FinancialRecordDB).all()
            assert len(financial_records) == 1  # Only one record despite two ingestions
            
            # But two ingestion logs should exist
            logs = session.query(DataIngestionLogDB).all()
            assert len(logs) == 2
    
    def test_auto_source_detection(self, clean_database, temp_data_files):
        """Test automatic source type detection."""
        service = DataIngestionService()
        
        # Ingest without specifying source type
        result = service.ingest_file(temp_data_files["quickbooks"])  # No source_type
        
        # Should auto-detect as QuickBooks
        assert result.status == IngestionStatus.COMPLETED
        assert result.source_type == SourceType.QUICKBOOKS
        
        # Verify data was processed correctly
        with get_db_session() as session:
            financial_records = session.query(FinancialRecordDB).all()
            assert len(financial_records) == 1
            assert financial_records[0].source == SourceType.QUICKBOOKS.value
    
    def test_ingestion_error_recovery(self, clean_database):
        """Test error recovery and partial success scenarios."""
        service = DataIngestionService()
        
        # Create a file with some valid and some invalid data
        problematic_data = {
            "data": {
                "Header": {
                    "Time": "2024-01-31T23:59:59",
                    "ReportName": "ProfitAndLoss", 
                    "Currency": "USD",
                    "StartPeriod": "2024-01-01",
                    "EndPeriod": "2024-01-31"
                },
                "Columns": [
                    {"ColTitle": "", "ColType": "Account"},
                    {"ColTitle": "Jan 2024", "ColType": "Money"}
                ],
                "Rows": [
                    {
                        "group": "Income",
                        "ColData": [
                            {"value": "Product Sales", "id": "qb-revenue-001"},
                            {"value": "invalid_amount"}  # Invalid amount
                        ]
                    }
                ]
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(problematic_data, f)
            problematic_file = f.name
        
        try:
            result = service.ingest_file(problematic_file, SourceType.QUICKBOOKS)
            
            # Should handle the error gracefully
            assert result.status in [IngestionStatus.FAILED, IngestionStatus.PARTIALLY_COMPLETED]
            assert result.error_message is not None
            
            # Verify error was logged
            with get_db_session() as session:
                logs = session.query(DataIngestionLogDB).all()
                assert len(logs) == 1
                assert logs[0].error_message is not None
                
        finally:
            os.unlink(problematic_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])