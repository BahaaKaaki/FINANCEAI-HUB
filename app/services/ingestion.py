import json
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import (
    AccountDB,
    AccountValueDB,
    DataIngestionLogDB,
    FinancialRecordDB,
)
from app.models.financial import (
    Account,
    AccountCreate,
    AccountValue,
    AccountValueCreate,
    FinancialRecord,
    FinancialRecordCreate,
    SourceType,
)
from app.parsers.quickbooks_parser import QuickBooksParseError, parse_quickbooks_file
from app.parsers.rootfi_parser import RootfiParseError, parse_rootfi_file
from app.services.validation import ValidationResult, ValidationSeverity

logger = get_logger(__name__)


class IngestionStatus(str, Enum):
    """Status of data ingestion operations."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_COMPLETED = "partially_completed"


class FileProcessingResult(BaseModel):
    """Result of processing a single file."""

    filename: str
    source_type: SourceType
    status: IngestionStatus
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    validation_result: Optional[ValidationResult] = None
    error_message: Optional[str] = None
    processing_duration_seconds: Optional[float] = None


class BatchIngestionResult(BaseModel):
    """Result of batch ingestion operation."""

    batch_id: str
    status: IngestionStatus
    files_processed: int = 0
    files_successful: int = 0
    files_failed: int = 0
    total_records_processed: int = 0
    total_records_created: int = 0
    total_records_updated: int = 0
    file_results: List[FileProcessingResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    processing_duration_seconds: Optional[float] = None
    error_summary: Optional[str] = None


class DataIngestionService:
    """
    Service for orchestrating financial data ingestion operations.
    """

    def __init__(self):
        """Initialize the data ingestion service."""
        self.settings = get_settings()

    def ingest_file(
        self, file_path: str, source_type: Optional[SourceType] = None
    ) -> FileProcessingResult:
        """
        Ingest a single financial data file.

        Args:
            file_path: Path to the file to ingest
            source_type: Optional source type override (auto-detected if not provided)

        Returns:
            FileProcessingResult with processing details and status
        """
        start_time = datetime.now(timezone.utc)
        filename = os.path.basename(file_path)

        logger.info("Starting ingestion of file: %s", filename)

        result = FileProcessingResult(
            filename=filename,
            source_type=source_type or self._detect_source_type(file_path),
            status=IngestionStatus.PROCESSING,
        )

        log_id = self._create_ingestion_log(result.source_type, filename)

        try:
            financial_records, accounts, account_values = self._parse_file(
                file_path, result.source_type
            )

            result.records_processed = len(financial_records)

            validation_result = self._validate_parsed_data(
                financial_records, accounts, account_values
            )
            result.validation_result = validation_result

            if validation_result.is_valid or self._has_only_warnings(validation_result):
                created, updated = self._store_data(
                    financial_records, accounts, account_values
                )
                result.records_created = created
                result.records_updated = updated
                result.status = IngestionStatus.COMPLETED
            else:
                result.status = IngestionStatus.FAILED
                result.error_message = f"Validation failed with {len(validation_result.issues)} critical issues"

        except (QuickBooksParseError, RootfiParseError) as e:
            logger.error("Parsing error for file %s: %s", filename, str(e))
            result.status = IngestionStatus.FAILED
            result.error_message = f"Parsing error: {str(e)}"

        except SQLAlchemyError as e:
            logger.error("Database error for file %s: %s", filename, str(e))
            result.status = IngestionStatus.FAILED
            result.error_message = f"Database error: {str(e)}"

        except Exception as e:
            logger.error("Unexpected error for file %s: %s", filename, str(e))
            result.status = IngestionStatus.FAILED
            result.error_message = f"Unexpected error: {str(e)}"

        finally:
            # Calculate processing duration
            end_time = datetime.now(timezone.utc)
            result.processing_duration_seconds = (end_time - start_time).total_seconds()

            self._update_ingestion_log(
                log_id, result.status, result, end_time, start_time
            )

            logger.info(
                "Completed ingestion of file %s: status=%s, duration=%.2fs",
                filename,
                result.status,
                result.processing_duration_seconds,
            )

        return result

    def ingest_batch(
        self, file_paths: List[str], source_types: Optional[List[SourceType]] = None
    ) -> BatchIngestionResult:
        """
        Ingest multiple financial data files in batch.

        Args:
            file_paths: List of file paths to ingest
            source_types: Optional list of source types (auto-detected if not provided)

        Returns:
            BatchIngestionResult with batch processing details and status
        """
        batch_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        logger.info(
            "Starting batch ingestion %s with %d files", batch_id, len(file_paths)
        )

        result = BatchIngestionResult(
            batch_id=batch_id,
            status=IngestionStatus.PROCESSING,
            files_processed=len(file_paths),
        )

        for i, file_path in enumerate(file_paths):
            source_type = None
            if source_types and i < len(source_types):
                source_type = source_types[i]

            try:
                file_result = self.ingest_file(file_path, source_type)
                result.file_results.append(file_result)

                if file_result.status == IngestionStatus.COMPLETED:
                    result.files_successful += 1
                    result.total_records_created += file_result.records_created
                    result.total_records_updated += file_result.records_updated
                else:
                    result.files_failed += 1

                result.total_records_processed += file_result.records_processed

            except Exception as e:
                logger.error(
                    "Failed to process file %s in batch: %s", file_path, str(e)
                )
                failed_result = FileProcessingResult(
                    filename=os.path.basename(file_path),
                    source_type=source_type or SourceType.QUICKBOOKS,  # Default
                    status=IngestionStatus.FAILED,
                    error_message=f"Batch processing error: {str(e)}",
                )
                result.file_results.append(failed_result)
                result.files_failed += 1

        if result.files_failed == 0:
            result.status = IngestionStatus.COMPLETED
        elif result.files_successful == 0:
            result.status = IngestionStatus.FAILED
            result.error_summary = f"All {result.files_failed} files failed to process"
        else:
            result.status = IngestionStatus.PARTIALLY_COMPLETED
            result.error_summary = (
                f"{result.files_failed} of {result.files_processed} files failed"
            )

        # Calculate processing duration
        end_time = datetime.now(timezone.utc)
        result.completed_at = end_time
        result.processing_duration_seconds = (end_time - start_time).total_seconds()

        logger.info(
            "Completed batch ingestion %s: status=%s, successful=%d, failed=%d, duration=%.2fs",
            batch_id,
            result.status,
            result.files_successful,
            result.files_failed,
            result.processing_duration_seconds,
        )

        return result

    def get_ingestion_status(self, batch_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get status of ingestion operations.

        Args:
            batch_id: Optional batch ID to get specific batch status

        Returns:
            Dictionary with ingestion status information
        """
        try:
            with get_db_session() as session:
                if batch_id:
                    return {"batch_id": batch_id, "status": "not_implemented"}
                else:
                    recent_logs = (
                        session.query(DataIngestionLogDB)
                        .order_by(DataIngestionLogDB.started_at.desc())
                        .limit(10)
                        .all()
                    )

                    logs_data = []
                    for log in recent_logs:
                        log_data = {
                            "id": log.id,
                            "source": log.source,
                            "filename": log.filename,
                            "status": log.status,
                            "records_processed": log.records_processed,
                            "records_created": log.records_created,
                            "records_updated": log.records_updated,
                            "started_at": (
                                log.started_at.isoformat() if log.started_at else None
                            ),
                            "completed_at": (
                                log.completed_at.isoformat()
                                if log.completed_at
                                else None
                            ),
                            "processing_duration_seconds": log.processing_duration_seconds,
                            "error_message": log.error_message,
                        }
                        logs_data.append(log_data)

                    return {
                        "recent_ingestions": logs_data,
                        "total_logs": len(logs_data),
                    }

        except Exception as e:
            logger.error("Failed to get ingestion status: %s", str(e))
            return {"error": f"Failed to get status: {str(e)}"}

    def _detect_source_type(self, file_path: str) -> SourceType:
        """
        Auto-detect source type based on file content or naming patterns.

        Args:
            file_path: Path to the file

        Returns:
            Detected SourceType
        """
        filename = os.path.basename(file_path).lower()

        if "quickbooks" in filename or "qb" in filename:
            return SourceType.QUICKBOOKS
        elif "rootfi" in filename or "rf" in filename:
            return SourceType.ROOTFI

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # QuickBooks typically has Header, Columns, Rows structure
            if isinstance(data, dict) and "data" in data:
                data_section = data["data"]
                if (
                    isinstance(data_section, dict)
                    and "Header" in data_section
                    and "Columns" in data_section
                    and "Rows" in data_section
                ):
                    return SourceType.QUICKBOOKS

            # Rootfi typically has an array of records with specific fields
            if isinstance(data, dict) and "data" in data:
                data_array = data["data"]
                if isinstance(data_array, list) and len(data_array) > 0:
                    first_record = data_array[0]
                    if (
                        isinstance(first_record, dict)
                        and "rootfi_id" in first_record
                        and "revenue" in first_record
                    ):
                        return SourceType.ROOTFI

        except (json.JSONDecodeError, FileNotFoundError, KeyError):
            logger.warning(
                "Could not detect source type from file content: %s", file_path
            )

        logger.info("Defaulting to QuickBooks source type for file: %s", file_path)
        return SourceType.QUICKBOOKS

    def _parse_file(
        self, file_path: str, source_type: SourceType
    ) -> Tuple[
        List[FinancialRecordCreate], List[AccountCreate], List[AccountValueCreate]
    ]:
        """
        Parse a file using the appropriate parser.

        Args:
            file_path: Path to the file to parse
            source_type: Type of source data

        Returns:
            Tuple of (financial_records, accounts, account_values)
        """
        logger.debug("Parsing file %s as %s", file_path, source_type)

        if source_type == SourceType.QUICKBOOKS:
            return parse_quickbooks_file(file_path)
        elif source_type == SourceType.ROOTFI:
            return parse_rootfi_file(file_path)
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

    def _validate_parsed_data(
        self,
        financial_records: List[FinancialRecordCreate],
        accounts: List[AccountCreate],
        account_values: List[AccountValueCreate],
    ) -> ValidationResult:
        """
        Validate parsed data before storage.

        Args:
            financial_records: List of financial records to validate
            accounts: List of accounts to validate
            account_values: List of account values to validate

        Returns:
            ValidationResult with validation details
        """
        from app.services.validation import FinancialDataValidator

        validator = FinancialDataValidator()

        # For now, we will return a basic validation result
        # In a full implementation, this would validate all the data
        validation_result = ValidationResult(is_valid=True, quality_score=1.0)

        # Validation checks
        if not financial_records:
            validation_result.add_issue(
                ValidationSeverity.ERROR,
                "NO_FINANCIAL_RECORDS",
                "No financial records found in parsed data",
                suggestion="Verify file contains valid financial data",
            )

        if not accounts:
            validation_result.add_issue(
                ValidationSeverity.WARNING,
                "NO_ACCOUNTS",
                "No accounts found in parsed data",
                suggestion="Verify file contains account information",
            )

        logger.debug(
            "Validated parsed data: records=%d, accounts=%d, values=%d, valid=%s",
            len(financial_records),
            len(accounts),
            len(account_values),
            validation_result.is_valid,
        )

        return validation_result

    def _has_only_warnings(self, validation_result: ValidationResult) -> bool:
        """
        Check if validation result has only warnings (no errors or critical issues).

        Args:
            validation_result: Validation result to check

        Returns:
            True if only warnings exist, False if errors or critical issues exist
        """
        for issue in validation_result.issues:
            if issue.severity in [
                ValidationSeverity.ERROR,
                ValidationSeverity.CRITICAL,
            ]:
                return False
        return True

    def _store_data(
        self,
        financial_records: List[FinancialRecordCreate],
        accounts: List[AccountCreate],
        account_values: List[AccountValueCreate],
    ) -> Tuple[int, int]:
        """
        Store validated data in the database.

        Args:
            financial_records: List of financial records to store
            accounts: List of accounts to store
            account_values: List of account values to store

        Returns:
            Tuple of (records_created, records_updated)
        """
        records_created = 0
        records_updated = 0

        try:
            with get_db_session() as session:
                # Store accounts first (due to foreign key relationships)
                for account_create in accounts:
                    existing_account = (
                        session.query(AccountDB)
                        .filter(AccountDB.account_id == account_create.account_id)
                        .first()
                    )

                    if existing_account:
                        # Update existing account
                        existing_account.name = account_create.name
                        existing_account.account_type = account_create.account_type
                        existing_account.parent_account_id = (
                            account_create.parent_account_id
                        )
                        existing_account.description = account_create.description
                        existing_account.is_active = account_create.is_active
                        existing_account.updated_at = datetime.now(timezone.utc)
                    else:
                        # Create new account
                        account_db = AccountDB(
                            account_id=account_create.account_id,
                            name=account_create.name,
                            account_type=account_create.account_type,
                            parent_account_id=account_create.parent_account_id,
                            source=account_create.source,
                            description=account_create.description,
                            is_active=account_create.is_active,
                        )
                        session.add(account_db)

                # Store financial records
                for record_create in financial_records:
                    # Generate ID if not provided
                    record_id = str(uuid.uuid4())

                    existing_record = (
                        session.query(FinancialRecordDB)
                        .filter(
                            FinancialRecordDB.source == record_create.source,
                            FinancialRecordDB.period_start
                            == record_create.period_start,
                            FinancialRecordDB.period_end == record_create.period_end,
                        )
                        .first()
                    )

                    if existing_record:
                        # Update existing record
                        existing_record.currency = record_create.currency
                        existing_record.revenue = record_create.revenue
                        existing_record.expenses = record_create.expenses
                        existing_record.net_profit = record_create.net_profit
                        existing_record.raw_data = (
                            json.dumps(record_create.raw_data)
                            if record_create.raw_data
                            else None
                        )
                        existing_record.updated_at = datetime.now(timezone.utc)
                        records_updated += 1
                        record_id = existing_record.id
                    else:
                        # Create new record
                        record_db = FinancialRecordDB(
                            id=record_id,
                            source=record_create.source,
                            period_start=record_create.period_start,
                            period_end=record_create.period_end,
                            currency=record_create.currency,
                            revenue=record_create.revenue,
                            expenses=record_create.expenses,
                            net_profit=record_create.net_profit,
                            raw_data=(
                                json.dumps(record_create.raw_data)
                                if record_create.raw_data
                                else None
                            ),
                        )
                        session.add(record_db)
                        records_created += 1

                    # Store account values for this record
                    for value_create in account_values:
                        if (
                            value_create.financial_record_id == record_id
                            or not hasattr(value_create, "financial_record_id")
                        ):
                            # Update the financial_record_id to match our generated/found ID
                            value_create.financial_record_id = record_id

                            existing_value = (
                                session.query(AccountValueDB)
                                .filter(
                                    AccountValueDB.account_id
                                    == value_create.account_id,
                                    AccountValueDB.financial_record_id == record_id,
                                )
                                .first()
                            )

                            if existing_value:
                                # Update existing value
                                existing_value.value = value_create.value
                            else:
                                # Create new value
                                value_db = AccountValueDB(
                                    account_id=value_create.account_id,
                                    financial_record_id=record_id,
                                    value=value_create.value,
                                )
                                session.add(value_db)

                # Commit all changes
                session.commit()

                logger.info(
                    "Stored data successfully: created=%d, updated=%d",
                    records_created,
                    records_updated,
                )

        except Exception as e:
            logger.error("Failed to store data: %s", str(e))
            raise

        return records_created, records_updated

    def _create_ingestion_log(
        self, source: SourceType, filename: Optional[str] = None
    ) -> int:
        """
        Create an ingestion log entry.

        Args:
            source: Source type being ingested
            filename: Optional filename being processed

        Returns:
            Log entry ID
        """
        try:
            with get_db_session() as session:
                log_entry = DataIngestionLogDB(
                    source=source,
                    filename=filename,
                    status="started",
                    started_at=datetime.now(timezone.utc),
                )
                session.add(log_entry)
                session.commit()
                return log_entry.id

        except Exception as e:
            logger.error("Failed to create ingestion log: %s", str(e))
            return -1

    def _update_ingestion_log(
        self,
        log_id: int,
        status: IngestionStatus,
        result: FileProcessingResult,
        end_time: datetime,
        start_time: datetime,
    ) -> None:
        """
        Update an ingestion log entry with completion details.

        Args:
            log_id: Log entry ID to update
            status: Final status of the ingestion
            result: Processing result with details
            end_time: Processing end time
            start_time: Processing start time
        """
        if log_id == -1:
            return

        try:
            with get_db_session() as session:
                log_entry = (
                    session.query(DataIngestionLogDB)
                    .filter(DataIngestionLogDB.id == log_id)
                    .first()
                )

                if log_entry:
                    log_entry.status = status.value
                    log_entry.records_processed = result.records_processed
                    log_entry.records_created = result.records_created
                    log_entry.records_updated = result.records_updated
                    log_entry.error_message = result.error_message
                    log_entry.completed_at = end_time
                    log_entry.processing_duration_seconds = int(
                        (end_time - start_time).total_seconds()
                    )
                    session.commit()

        except Exception as e:
            logger.error("Failed to update ingestion log %d: %s", log_id, str(e))
