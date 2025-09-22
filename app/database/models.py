from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    DECIMAL,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.logging import get_logger

logger = get_logger(__name__)
Base = declarative_base()


class FinancialRecordDB(Base):
    """
    Database model for financial records.
    """

    __tablename__ = "financial_records"

    id = Column(String(255), primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)
    period_start = Column(Date, nullable=False, index=True)
    period_end = Column(Date, nullable=False, index=True)
    currency = Column(String(3), nullable=False, index=True)
    revenue = Column(DECIMAL(15, 2), nullable=False)
    expenses = Column(DECIMAL(15, 2), nullable=False)
    net_profit = Column(DECIMAL(15, 2), nullable=False)
    raw_data = Column(Text)  # JSON stored as text
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    # Relationships
    account_values = relationship(
        "AccountValueDB",
        back_populates="financial_record",
        cascade="all, delete-orphan",
    )

    # Constraints
    __table_args__ = (
        CheckConstraint("revenue >= 0", name="check_revenue_non_negative"),
        CheckConstraint("expenses >= 0", name="check_expenses_non_negative"),
        CheckConstraint(
            "period_end > period_start", name="check_period_end_after_start"
        ),
        CheckConstraint("length(currency) = 3", name="check_currency_length"),
        CheckConstraint("length(source) > 0", name="check_source_not_empty"),
        # Composite indexes for common query patterns
        Index(
            "idx_financial_records_period_source",
            "period_start",
            "period_end",
            "source",
        ),
        Index(
            "idx_financial_records_currency_period",
            "currency",
            "period_start",
            "period_end",
        ),
        Index("idx_financial_records_created_at_source", "created_at", "source"),
    )

    def __repr__(self):
        return f"<FinancialRecord(id='{self.id}', source='{self.source}', period='{self.period_start}' to '{self.period_end}')>"


class AccountDB(Base):
    """
    Database model for financial accounts.

    Supports hierarchical account structures with self-referential
    foreign keys and proper indexing for tree traversal.
    """

    __tablename__ = "accounts"

    account_id = Column(String(255), primary_key=True, index=True)
    name = Column(String(500), nullable=False, index=True)
    account_type = Column(String(50), nullable=False, index=True)
    parent_account_id = Column(
        String(255), ForeignKey("accounts.account_id"), nullable=True, index=True
    )
    source = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )

    # Self-referential relationship for account hierarchy
    parent = relationship(
        "AccountDB", remote_side=[account_id], back_populates="children"
    )
    children = relationship(
        "AccountDB", back_populates="parent", cascade="all, delete-orphan"
    )

    # Relationship to account values
    account_values = relationship(
        "AccountValueDB", back_populates="account", cascade="all, delete-orphan"
    )

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint("length(name) > 0", name="check_account_name_not_empty"),
        CheckConstraint(
            "length(account_type) > 0", name="check_account_type_not_empty"
        ),
        CheckConstraint("length(source) > 0", name="check_account_source_not_empty"),
        CheckConstraint(
            "account_id != parent_account_id", name="check_not_self_parent"
        ),
        # Composite indexes for common queries
        Index("idx_accounts_type_source_active", "account_type", "source", "is_active"),
        Index("idx_accounts_parent_type", "parent_account_id", "account_type"),
        Index("idx_accounts_source_active", "source", "is_active"),
    )

    def __repr__(self):
        return f"<Account(id='{self.account_id}', name='{self.name}', type='{self.account_type}')>"


class AccountValueDB(Base):
    """
    Database model for account values.

    Links accounts to financial records with specific monetary values,
    enabling detailed financial analysis and reporting.
    """

    __tablename__ = "account_values"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(
        String(255), ForeignKey("accounts.account_id"), nullable=False, index=True
    )
    financial_record_id = Column(
        String(255), ForeignKey("financial_records.id"), nullable=False, index=True
    )
    value = Column(DECIMAL(15, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)

    # Relationships
    account = relationship("AccountDB", back_populates="account_values")
    financial_record = relationship(
        "FinancialRecordDB", back_populates="account_values"
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint to prevent duplicate account values for the same record
        Index(
            "idx_account_values_unique",
            "account_id",
            "financial_record_id",
            unique=True,
        ),
        # Composite indexes for common query patterns
        Index("idx_account_values_record_account", "financial_record_id", "account_id"),
        Index("idx_account_values_account_created", "account_id", "created_at"),
    )

    def __repr__(self):
        return f"<AccountValue(account_id='{self.account_id}', record_id='{self.financial_record_id}', value={self.value})>"


# Additional utility models for database operations


class DataIngestionLogDB(Base):
    """
    Database model for tracking data ingestion operations.

    Provides audit trail and monitoring capabilities for data processing.
    """

    __tablename__ = "data_ingestion_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)
    filename = Column(String(500), nullable=True)
    status = Column(
        String(50), nullable=False, index=True
    )  # 'started', 'completed', 'failed'
    records_processed = Column(Integer, nullable=True)
    records_created = Column(Integer, nullable=True)
    records_updated = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    completed_at = Column(DateTime, nullable=True)
    processing_duration_seconds = Column(Integer, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "records_processed >= 0", name="check_records_processed_non_negative"
        ),
        CheckConstraint(
            "records_created >= 0", name="check_records_created_non_negative"
        ),
        CheckConstraint(
            "records_updated >= 0", name="check_records_updated_non_negative"
        ),
        CheckConstraint(
            "processing_duration_seconds >= 0", name="check_duration_non_negative"
        ),
        Index("idx_ingestion_logs_status_started", "status", "started_at"),
        Index("idx_ingestion_logs_source_status", "source", "status"),
    )

    def __repr__(self):
        return f"<DataIngestionLog(id={self.id}, source='{self.source}', status='{self.status}')>"
