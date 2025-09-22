from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.retry import retry_database_operation, DATABASE_RETRY_CONFIG, execute_with_retry
from app.core.monitoring import record_database_operation, monitor_operation
from app.database.models import Base

logger = get_logger(__name__)

_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """
    Enable foreign key constraints for SQLite connections.

    SQLite has foreign key constraints disabled by default,
    so we need to enable them for each connection.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _configure_sqlite_performance(dbapi_connection, connection_record):
    """
    Configure SQLite performance settings for better performance.

    Sets various PRAGMA settings to optimize SQLite performance
    for our use case using values from configuration.
    """
    settings = get_settings()
    cursor = dbapi_connection.cursor()

    # Enable WAL mode for better concurrent access
    cursor.execute("PRAGMA journal_mode=WAL")
    # Set synchronous mode to NORMAL for better performance
    cursor.execute("PRAGMA synchronous=NORMAL")
    # Increase cache size (in KB) - configurable
    cursor.execute(f"PRAGMA cache_size={settings.database_cache_size}")
    # Set temp store to memory
    cursor.execute("PRAGMA temp_store=MEMORY")
    # Set mmap size for memory-mapped I/O - configurable
    cursor.execute(f"PRAGMA mmap_size={settings.database_mmap_size}")
    cursor.close()


def create_database_engine(database_url: Optional[str] = None) -> Engine:
    """
    Create and configure the database engine with connection pooling.

    Args:
        database_url: Optional database URL. If not provided, uses settings.

    Returns:
        Configured SQLAlchemy engine with connection pooling.
    """
    settings = get_settings()

    if database_url is None:
        database_url = settings.database_url

    logger.info(
        "Creating database engine with URL: %s", database_url.split("://")[0] + "://***"
    )

    # Configure engine with connection pooling
    engine_kwargs = {
        "echo": settings.database_echo,
        "future": True,
    }

    # SQLite-specific configuration
    if database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,  # Allow multiple threads
                    "timeout": settings.database_connection_timeout,
                },
                "pool_pre_ping": True,  # Verify connections before use
                "pool_recycle": settings.database_pool_recycle,
            }
        )
    else:
        # For other databases (PostgreSQL, MySQL, etc.)
        engine_kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "pool_recycle": settings.database_pool_recycle,
                "pool_pre_ping": True,
            }
        )

    engine = create_engine(database_url, **engine_kwargs)

    # Register event listeners for SQLite
    if database_url.startswith("sqlite"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        event.listen(engine, "connect", _configure_sqlite_performance)

    return engine


def get_engine() -> Engine:
    """
    Get the global database engine, creating it if necessary.

    Returns:
        The global SQLAlchemy engine instance.
    """
    global _engine

    if _engine is None:
        _engine = create_database_engine()
        logger.info("Database engine created successfully")

    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get the global session factory, creating it if necessary.

    Returns:
        The global SQLAlchemy session factory.
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = sessionmaker(
            bind=engine, autocommit=False, autoflush=False, expire_on_commit=False
        )
        logger.info("Database session factory created successfully")

    return _session_factory


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic cleanup and retry logic.

    Provides a database session with automatic transaction management,
    retry logic for transient failures, and performance monitoring.
    Commits on success, rolls back on exception, and always closes the session.

    Yields:
        SQLAlchemy session instance.

    Example:
        with get_db_session() as session:
            # Use session for database operations
            result = session.query(FinancialRecordDB).all()
    """
    with monitor_operation("database.session", {"operation": "session_lifecycle"}):
        session_factory = get_session_factory()
        
        def _create_session():
            return session_factory()
        
        # Use retry logic for session creation
        session = execute_with_retry(
            _create_session,
            "database_session_creation",
            DATABASE_RETRY_CONFIG
        )

        try:
            logger.debug("Database session created")
            yield session
            
            # Commit with retry logic
            def _commit_session():
                session.commit()
                
            execute_with_retry(
                _commit_session,
                "database_session_commit",
                DATABASE_RETRY_CONFIG
            )
            
            logger.debug("Database session committed successfully")
            record_database_operation("session_commit", 0, True)
            
        except Exception as e:
            logger.error("Database session error, rolling back: %s", str(e))
            
            try:
                session.rollback()
                record_database_operation("session_rollback", 0, True)
            except Exception as rollback_error:
                logger.error("Failed to rollback session: %s", str(rollback_error))
                record_database_operation("session_rollback", 0, False)
            
            record_database_operation("session_commit", 0, False)
            raise
        finally:
            try:
                session.close()
                logger.debug("Database session closed")
            except Exception as close_error:
                logger.warning("Error closing database session: %s", str(close_error))


def create_tables(engine: Optional[Engine] = None) -> None:
    """
    Create all database tables defined in the models.

    Args:
        engine: Optional engine to use. If not provided, uses global engine.
    """
    if engine is None:
        engine = get_engine()

    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


def drop_tables(engine: Optional[Engine] = None) -> None:
    """
    Drop all database tables. Use with caution!

    Args:
        engine: Optional engine to use. If not provided, uses global engine.
    """
    if engine is None:
        engine = get_engine()

    logger.warning("Dropping all database tables...")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")


def reset_database(engine: Optional[Engine] = None) -> None:
    """
    Reset the database by dropping and recreating all tables.

    Args:
        engine: Optional engine to use. If not provided, uses global engine.
    """
    logger.warning("Resetting database...")
    drop_tables(engine)
    create_tables(engine)
    logger.info("Database reset completed")


@retry_database_operation
def check_database_connection() -> bool:
    """
    Check if the database connection is working with retry logic.

    Returns:
        True if connection is successful, False otherwise.
    """
    with monitor_operation("database.health_check"):
        try:
            from sqlalchemy import text

            engine = get_engine()
            with engine.connect() as connection:
                # Execute a simple query to test the connection
                result = connection.execute(text("SELECT 1"))
                result.fetchone()
            logger.info("Database connection check successful")
            record_database_operation("health_check", 0, True)
            return True
        except Exception as e:
            logger.error("Database connection check failed: %s", str(e))
            record_database_operation("health_check", 0, False)
            return False


def get_database_info() -> dict:
    """
    Get information about the database connection and configuration.

    Returns:
        Dictionary containing database information.
    """
    engine = get_engine()
    settings = get_settings()

    info = {
        "database_url": settings.database_url.split("://")[0]
        + "://***",  # Hide sensitive info
        "driver": engine.driver,
        "dialect": engine.dialect.name,
        "pool_size": getattr(engine.pool, "size", "N/A"),
        "pool_checked_out": getattr(engine.pool, "checkedout", "N/A"),
        "echo": engine.echo,
    }

    return info


# Cleanup function for graceful shutdown
def cleanup_database_connections():
    """
    Clean up database connections and resources.

    Should be called during application shutdown.
    """
    global _engine, _session_factory

    if _engine:
        logger.info("Disposing database engine...")
        _engine.dispose()
        _engine = None

    if _session_factory:
        _session_factory = None

    logger.info("Database connections cleaned up")
