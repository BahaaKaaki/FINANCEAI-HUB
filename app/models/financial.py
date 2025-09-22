from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    field_validator,
    validator,
    ConfigDict,
)

from app.core.logging import get_logger

logger = get_logger(__name__)


class SourceType(str, Enum):
    """Enum of supported data sources."""

    QUICKBOOKS = "quickbooks"
    ROOTFI = "rootfi"


class AccountType(str, Enum):
    """Enum of account types."""

    REVENUE = "revenue"
    EXPENSE = "expense"
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"


class FinancialRecord(BaseModel):
    """
    Unified financial record model representing processed financial data.

    This model serves as the normalized representation of financial data
    from various sources (QuickBooks, Rootfi, etc.).
    """

    id: str = Field(..., description="Unique identifier for the financial record")
    source: SourceType = Field(..., description="Source system that provided this data")
    period_start: date = Field(..., description="Start date of the financial period")
    period_end: date = Field(..., description="End date of the financial period")
    currency: str = Field(..., description="Currency code (e.g., USD, EUR)")
    revenue: Decimal = Field(..., description="Total revenue for the period")
    expenses: Decimal = Field(..., description="Total expenses for the period")
    net_profit: Decimal = Field(..., description="Net profit (revenue - expenses)")
    raw_data: Optional[Dict[str, Any]] = Field(
        None, description="Original raw data for audit trail"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record last update timestamp",
    )

    @field_validator("period_end")
    @classmethod
    def validate_period_end(cls, v, info: ValidationInfo):
        """Basic period_end validation - let validation service handle detailed checks."""
        # Just return the value, let validation service handle date range checks
        return v

    @field_validator("net_profit")
    @classmethod
    def validate_net_profit(cls, v, info: ValidationInfo):
        """Basic net_profit validation - let validation service handle detailed checks."""
        # Just return the value, let validation service handle balance equation checks
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v):
        """Normalize currency code to uppercase."""
        # Just normalize to uppercase, let validation service handle format checks
        return v.upper() if isinstance(v, str) else str(v).upper()

    model_config = ConfigDict(
        # Note: json_encoders is deprecated in Pydantic v2
        # Use custom serializers or model_dump with custom serialization instead
        arbitrary_types_allowed=True
    )


class Account(BaseModel):
    """
    Account model representing individual financial accounts.

    Supports hierarchical account structures with parent-child relationships.
    """

    account_id: str = Field(..., description="Unique identifier for the account")
    name: str = Field(..., description="Human-readable account name")
    account_type: AccountType = Field(
        ..., description="Type of account (revenue, expense, etc.)"
    )
    parent_account_id: Optional[str] = Field(
        None, description="Parent account ID for hierarchical structure"
    )
    source: SourceType = Field(
        ..., description="Source system that provided this account"
    )
    description: Optional[str] = Field(None, description="Optional account description")
    is_active: bool = Field(True, description="Whether the account is currently active")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Account creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Account last update timestamp",
    )

    @field_validator("name")
    @classmethod
    def validate_name_length(cls, v):
        """Validate account name meets minimum length requirement."""
        from app.core.config import get_settings

        settings = get_settings()

        if len(v.strip()) < settings.MIN_ACCOUNT_NAME_LENGTH:
            raise ValueError(
                f"account name must be at least {settings.MIN_ACCOUNT_NAME_LENGTH} character(s) long"
            )
        return v.strip()

    @field_validator("parent_account_id")
    @classmethod
    def validate_parent_account_id(cls, v, info: ValidationInfo):
        """Ensure account doesn't reference itself as parent."""
        if (
            v
            and info.data
            and "account_id" in info.data
            and v == info.data["account_id"]
        ):
            raise ValueError("account cannot be its own parent")
        return v

    model_config = ConfigDict(arbitrary_types_allowed=True)


class AccountValue(BaseModel):
    """
    Account value model representing the value of an account for a specific period.

    Links accounts to financial records with specific monetary values.
    """

    id: Optional[int] = Field(None, description="Auto-generated primary key")
    account_id: str = Field(..., description="Reference to the account")
    financial_record_id: str = Field(
        ..., description="Reference to the financial record"
    )
    value: Decimal = Field(
        ..., description="Monetary value for this account in this period"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Value record creation timestamp",
    )

    model_config = ConfigDict(arbitrary_types_allowed=True)


# Request/Response models for API endpoints
class FinancialRecordCreate(BaseModel):
    """Model for creating new financial records."""

    source: SourceType
    period_start: date
    period_end: date
    currency: str
    revenue: Decimal
    expenses: Decimal
    raw_data: Optional[Dict[str, Any]] = None

    @field_validator("period_end")
    @classmethod
    def validate_period_end(cls, v, info: ValidationInfo):
        """Basic period_end validation - let validation service handle detailed checks."""
        # Just return the value, let validation service handle date range checks
        return v

    @property
    def net_profit(self) -> Decimal:
        """Calculate net profit from revenue and expenses."""
        return self.revenue - self.expenses


class AccountCreate(BaseModel):
    """Model for creating new accounts."""

    account_id: str
    name: str
    account_type: AccountType
    parent_account_id: Optional[str] = None
    source: SourceType
    description: Optional[str] = None
    is_active: bool = True


class AccountValueCreate(BaseModel):
    """Model for creating new account values."""

    account_id: str
    financial_record_id: str
    value: Decimal


class FinancialRecordFilter(BaseModel):
    """Model for filtering financial records."""

    source: Optional[SourceType] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    currency: Optional[str] = None
    min_revenue: Optional[Decimal] = None
    max_revenue: Optional[Decimal] = None
    min_expenses: Optional[Decimal] = None
    max_expenses: Optional[Decimal] = None
