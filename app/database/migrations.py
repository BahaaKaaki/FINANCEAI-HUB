from datetime import datetime
from typing import Callable, List, Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

from app.core.logging import get_logger
from app.database.connection import get_db_session, get_engine

logger = get_logger(__name__)

MigrationBase = declarative_base()


class MigrationHistoryDB(MigrationBase):
    """
    Database model for tracking applied migrations.

    Keeps a record of all migrations that have been applied to the database,
    including timestamps and success/failure status.
    """

    __tablename__ = "migration_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    applied_at = Column(DateTime, nullable=False, default=func.now())
    success = Column(
        String(10), nullable=False, default="SUCCESS"
    )  # 'SUCCESS' or 'FAILED'
    error_message = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<MigrationHistory(version='{self.version}', name='{self.name}', success='{self.success}')>"


class Migration:
    """
    Represents a single database migration.

    Contains the migration version, name, and functions to apply/rollback changes.
    """

    def __init__(
        self,
        version: str,
        name: str,
        upgrade_func: Callable,
        downgrade_func: Optional[Callable] = None,
    ):
        self.version = version
        self.name = name
        self.upgrade_func = upgrade_func
        self.downgrade_func = downgrade_func

    def __repr__(self):
        return f"<Migration(version='{self.version}', name='{self.name}')>"


class MigrationManager:
    """
    Manages database migrations and schema evolution.

    Provides functionality to apply migrations, track migration history,
    and manage database schema changes over time.
    """

    def __init__(self):
        self.migrations: List[Migration] = []
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """Ensure the migration history table exists."""
        try:
            engine = get_engine()
            MigrationBase.metadata.create_all(bind=engine)
            logger.info("Migration history table ensured")
        except Exception as e:
            logger.error("Failed to create migration history table: %s", str(e))
            raise

    def add_migration(
        self,
        version: str,
        name: str,
        upgrade_func: Callable,
        downgrade_func: Optional[Callable] = None,
    ):
        """
        Add a migration to the manager.

        Args:
            version: Unique version identifier (e.g., '001', '002', etc.)
            name: Descriptive name for the migration
            upgrade_func: Function to apply the migration
            downgrade_func: Optional function to rollback the migration
        """
        migration = Migration(version, name, upgrade_func, downgrade_func)
        self.migrations.append(migration)
        logger.debug("Added migration: %s - %s", version, name)

    def get_applied_migrations(self) -> List[str]:
        """
        Get list of migration versions that have been successfully applied.

        Returns:
            List of migration version strings.
        """
        try:
            with get_db_session() as session:
                applied = (
                    session.query(MigrationHistoryDB.version)
                    .filter(MigrationHistoryDB.success == "SUCCESS")
                    .all()
                )
                return [row.version for row in applied]
        except Exception as e:
            logger.error("Failed to get applied migrations: %s", str(e))
            return []

    def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of migrations that haven't been applied yet.

        Returns:
            List of Migration objects that need to be applied.
        """
        applied_versions = set(self.get_applied_migrations())
        pending = [m for m in self.migrations if m.version not in applied_versions]

        # Sort by version to ensure proper order
        pending.sort(key=lambda x: x.version)
        return pending

    def apply_migration(self, migration: Migration) -> bool:
        """
        Apply a single migration with timeout handling.

        Args:
            migration: Migration object to apply

        Returns:
            True if successful, False otherwise
        """
        from app.core.config import get_settings

        settings = get_settings()

        start_time = datetime.utcnow()

        try:
            logger.info("Applying migration %s: %s", migration.version, migration.name)

            # Execute the migration
            migration.upgrade_func()

            # Calculate execution time
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Check if migration took too long
            if execution_time_ms > (settings.MIGRATION_TIMEOUT_SECONDS * 1000):
                logger.warning(
                    "Migration %s took %d ms, which exceeds timeout of %d seconds",
                    migration.version,
                    execution_time_ms,
                    settings.MIGRATION_TIMEOUT_SECONDS,
                )

            # Record successful migration
            with get_db_session() as session:
                history_record = MigrationHistoryDB(
                    version=migration.version,
                    name=migration.name,
                    applied_at=start_time,
                    success="SUCCESS",
                    execution_time_ms=execution_time_ms,
                )
                session.add(history_record)

            logger.info(
                "Migration %s applied successfully in %d ms",
                migration.version,
                execution_time_ms,
            )
            return True

        except Exception as e:
            # Calculate execution time even for failed migrations
            end_time = datetime.utcnow()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            error_message = str(e)
            logger.error(
                "Migration %s failed after %d ms: %s",
                migration.version,
                execution_time_ms,
                error_message,
            )

            # Record failed migration
            try:
                with get_db_session() as session:
                    history_record = MigrationHistoryDB(
                        version=migration.version,
                        name=migration.name,
                        applied_at=start_time,
                        success="FAILED",
                        error_message=error_message,
                        execution_time_ms=execution_time_ms,
                    )
                    session.add(history_record)
            except Exception as record_error:
                logger.error(
                    "Failed to record migration failure: %s", str(record_error)
                )

            return False

    def apply_all_pending(self) -> bool:
        """
        Apply all pending migrations in order.

        Returns:
            True if all migrations were successful, False if any failed
        """
        pending_migrations = self.get_pending_migrations()

        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return True

        logger.info("Found %d pending migrations", len(pending_migrations))

        success_count = 0
        for migration in pending_migrations:
            if self.apply_migration(migration):
                success_count += 1
            else:
                logger.error(
                    "Migration %s failed, stopping migration process", migration.version
                )
                break

        if success_count == len(pending_migrations):
            logger.info("All %d migrations applied successfully", success_count)
            return True
        else:
            logger.error(
                "Applied %d out of %d migrations",
                success_count,
                len(pending_migrations),
            )
            return False

    def get_migration_status(self) -> dict:
        """
        Get current migration status information.

        Returns:
            Dictionary with migration status details
        """
        applied_migrations = self.get_applied_migrations()
        pending_migrations = self.get_pending_migrations()

        return {
            "total_migrations": len(self.migrations),
            "applied_count": len(applied_migrations),
            "pending_count": len(pending_migrations),
            "applied_versions": applied_migrations,
            "pending_versions": [m.version for m in pending_migrations],
            "latest_applied": applied_migrations[-1] if applied_migrations else None,
        }


# Global migration manager instance
migration_manager = MigrationManager()


# Initial migration functions
def _create_initial_schema():
    """Create the initial database schema with all tables."""
    from app.database.connection import create_tables

    create_tables()
    logger.info("Initial schema created")


def _drop_initial_schema():
    """Drop the initial database schema (rollback function)."""
    from app.database.connection import drop_tables

    drop_tables()
    logger.info("Initial schema dropped")


# Register initial migration
migration_manager.add_migration(
    version="001",
    name="Create initial schema",
    upgrade_func=_create_initial_schema,
    downgrade_func=_drop_initial_schema,
)


def initialize_database() -> bool:
    """
    Initialize the database with all necessary tables and initial data.

    This function should be called during application startup to ensure
    the database is properly set up.

    Returns:
        True if initialization was successful, False otherwise
    """
    try:
        logger.info("Initializing database...")

        # Ensure migration table exists
        migration_manager._ensure_migration_table()

        # Apply all pending migrations
        success = migration_manager.apply_all_pending()

        if success:
            logger.info("Database initialization completed successfully")
        else:
            logger.error("Database initialization failed")

        return success

    except Exception as e:
        logger.error("Database initialization error: %s", str(e))
        return False


def get_migration_status() -> dict:
    """
    Get current database migration status.

    Returns:
        Dictionary with migration status information
    """
    return migration_manager.get_migration_status()


def apply_migrations() -> bool:
    """
    Apply all pending database migrations.

    Returns:
        True if all migrations were successful, False otherwise
    """
    return migration_manager.apply_all_pending()
