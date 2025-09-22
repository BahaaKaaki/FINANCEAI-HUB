import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.models.financial import SourceType
from app.services.ingestion import (
    BatchIngestionResult,
    DataIngestionService,
    FileProcessingResult,
    IngestionStatus,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/ingestion", tags=["Data Ingestion"])


class IngestionRequest(BaseModel):
    """Request model for file ingestion."""

    file_path: str = Field(..., description="Path to the file to ingest")
    source_type: Optional[SourceType] = Field(
        None, description="Source type (auto-detected if not provided)"
    )


class BatchIngestionRequest(BaseModel):
    """Request model for batch ingestion."""

    file_paths: List[str] = Field(..., description="List of file paths to ingest")
    source_types: Optional[List[SourceType]] = Field(
        None, description="List of source types (auto-detected if not provided)"
    )


class IngestionStatusResponse(BaseModel):
    """Response model for ingestion status."""

    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


# Initialize the ingestion service
ingestion_service = DataIngestionService()


@router.post("/file", response_model=FileProcessingResult)
async def ingest_file(request: IngestionRequest) -> FileProcessingResult:
    """
    Ingest a single financial data file.

    Args:
        request: Ingestion request with file path and optional source type

    Returns:
        FileProcessingResult with processing details

    Raises:
        HTTPException: If file not found or ingestion fails
    """
    logger.info("Received file ingestion request: %s", request.file_path)

    # Validate file exists
    if not os.path.exists(request.file_path):
        raise HTTPException(
            status_code=404, detail=f"File not found: {request.file_path}"
        )

    try:
        result = ingestion_service.ingest_file(request.file_path, request.source_type)
        
        # Log the result
        logger.info(
            "File ingestion completed: %s, status=%s, records=%d",
            request.file_path,
            result.status,
            result.records_processed,
        )

        return result

    except Exception as e:
        logger.error("File ingestion failed: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Ingestion failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchIngestionResult)
async def ingest_batch(request: BatchIngestionRequest) -> BatchIngestionResult:
    """
    Ingest multiple financial data files in batch.

    Args:
        request: Batch ingestion request with file paths and optional source types

    Returns:
        BatchIngestionResult with batch processing details

    Raises:
        HTTPException: If no files provided or batch ingestion fails
    """
    logger.info("Received batch ingestion request: %d files", len(request.file_paths))

    if not request.file_paths:
        raise HTTPException(status_code=400, detail="No file paths provided")

    # Validate all files exist
    missing_files = [
        path for path in request.file_paths if not os.path.exists(path)
    ]
    if missing_files:
        raise HTTPException(
            status_code=404,
            detail=f"Files not found: {', '.join(missing_files)}",
        )

    try:
        result = ingestion_service.ingest_batch(
            request.file_paths, request.source_types
        )

        logger.info(
            "Batch ingestion completed: batch_id=%s, status=%s, successful=%d, failed=%d",
            result.batch_id,
            result.status,
            result.files_successful,
            result.files_failed,
        )

        return result

    except Exception as e:
        logger.error("Batch ingestion failed: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Batch ingestion failed: {str(e)}"
        )


@router.post("/batch/async", response_model=Dict[str, str])
async def ingest_batch_async(
    background_tasks: BackgroundTasks, request: BatchIngestionRequest
) -> Dict[str, str]:
    """
    Ingest multiple files asynchronously in the background.

    Args:
        background_tasks: FastAPI background tasks
        request: Batch ingestion request

    Returns:
        Dictionary with batch ID for tracking

    Raises:
        HTTPException: If no files provided or validation fails
    """
    logger.info("Received async batch ingestion request: %d files", len(request.file_paths))

    if not request.file_paths:
        raise HTTPException(status_code=400, detail="No file paths provided")

    # Validate all files exist
    missing_files = [
        path for path in request.file_paths if not os.path.exists(path)
    ]
    if missing_files:
        raise HTTPException(
            status_code=404,
            detail=f"Files not found: {', '.join(missing_files)}",
        )

    # Generate batch ID for tracking
    import uuid
    batch_id = str(uuid.uuid4())

    # Add batch processing to background tasks
    background_tasks.add_task(
        _process_batch_async,
        batch_id,
        request.file_paths,
        request.source_types,
    )

    logger.info("Started async batch processing: batch_id=%s", batch_id)

    return {
        "batch_id": batch_id,
        "status": "processing",
        "message": f"Batch processing started with {len(request.file_paths)} files",
    }


@router.post("/upload", response_model=FileProcessingResult)
async def upload_and_ingest(
    file: UploadFile = File(...),
    source_type: Optional[SourceType] = Form(None),
) -> FileProcessingResult:
    """
    Upload and ingest a financial data file.

    Args:
        file: Uploaded file
        source_type: Optional source type (auto-detected if not provided)

    Returns:
        FileProcessingResult with processing details

    Raises:
        HTTPException: If upload or ingestion fails
    """
    logger.info("Received file upload for ingestion: %s", file.filename)

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Validate file type (basic check)
    if not file.filename.lower().endswith('.json'):
        raise HTTPException(
            status_code=400, detail="Only JSON files are supported"
        )

    try:
        # Save uploaded file temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Ingest the temporary file
            result = ingestion_service.ingest_file(temp_file_path, source_type)
            
            # Update filename in result to use original filename
            result.filename = file.filename

            logger.info(
                "File upload and ingestion completed: %s, status=%s, records=%d",
                file.filename,
                result.status,
                result.records_processed,
            )

            return result

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except OSError:
                logger.warning("Failed to delete temporary file: %s", temp_file_path)

    except Exception as e:
        logger.error("File upload and ingestion failed: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Upload and ingestion failed: {str(e)}"
        )


@router.get("/status", response_model=IngestionStatusResponse)
async def get_ingestion_status(
    batch_id: Optional[str] = None,
) -> IngestionStatusResponse:
    """
    Get status of ingestion operations.

    Args:
        batch_id: Optional batch ID to get specific batch status

    Returns:
        IngestionStatusResponse with status information

    Raises:
        HTTPException: If status retrieval fails
    """
    try:
        status_data = ingestion_service.get_ingestion_status(batch_id)

        if "error" in status_data:
            raise HTTPException(
                status_code=500, detail=status_data["error"]
            )

        return IngestionStatusResponse(
            status="success",
            message="Status retrieved successfully",
            data=status_data,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get ingestion status: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to get status: {str(e)}"
        )


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for the ingestion service.

    Returns:
        Dictionary with health status and service information
    """
    try:
        # Test database connection
        from app.database.connection import check_database_connection
        db_healthy = check_database_connection()

        # Test file system access (check if we can create temp files)
        import tempfile
        fs_healthy = True
        try:
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(b"test")
        except Exception:
            fs_healthy = False

        # Overall health status
        healthy = db_healthy and fs_healthy

        health_data = {
            "status": "healthy" if healthy else "unhealthy",
            "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
            "service": "data_ingestion",
            "version": "1.0.0",
            "checks": {
                "database": "healthy" if db_healthy else "unhealthy",
                "filesystem": "healthy" if fs_healthy else "unhealthy",
            },
        }

        if not healthy:
            logger.warning("Health check failed: %s", health_data)

        return health_data

    except Exception as e:
        logger.error("Health check error: %s", str(e))
        return {
            "status": "unhealthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "service": "data_ingestion",
            "version": "1.0.0",
            "error": str(e),
        }


async def _process_batch_async(
    batch_id: str,
    file_paths: List[str],
    source_types: Optional[List[SourceType]] = None,
) -> None:
    """
    Process batch ingestion asynchronously.

    Args:
        batch_id: Batch ID for tracking
        file_paths: List of file paths to process
        source_types: Optional list of source types
    """
    logger.info("Starting async batch processing: batch_id=%s", batch_id)

    try:
        result = ingestion_service.ingest_batch(file_paths, source_types)
        
        logger.info(
            "Async batch processing completed: batch_id=%s, status=%s, successful=%d, failed=%d",
            batch_id,
            result.status,
            result.files_successful,
            result.files_failed,
        )

        # In a production system, we might want to:
        # 1. Store the result in a cache/database for later retrieval
        # 2. Send notifications about completion
        # 3. Trigger downstream processes

    except Exception as e:
        logger.error("Async batch processing failed: batch_id=%s, error=%s", batch_id, str(e))
        # In a production system, we might want to:
        # 1. Store the error for later retrieval
        # 2. Send error notifications
        # 3. Implement retry logic