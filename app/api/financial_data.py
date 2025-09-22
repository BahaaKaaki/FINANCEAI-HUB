from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import joinedload

from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import AccountDB, AccountValueDB, FinancialRecordDB
from app.models.financial import Account, AccountType, FinancialRecord, SourceType

logger = get_logger(__name__)

router = APIRouter(prefix="/financial-data", tags=["Financial Data"])


class PaginationParams(BaseModel):
    """Pagination parameters for API responses."""

    page: int = Field(1, ge=1, description="Page number (1-based)")
    page_size: int = Field(20, ge=1, le=100, description="Number of items per page")


class FinancialDataResponse(BaseModel):
    """Response model for financial data endpoints."""

    data: List[FinancialRecord]
    pagination: Dict[str, Any]
    total_count: int
    filters_applied: Dict[str, Any]


class AccountResponse(BaseModel):
    """Response model for account endpoints."""

    data: List[Account]
    total_count: int
    filters_applied: Dict[str, Any]


class AccountHierarchyResponse(BaseModel):
    """Response model for account hierarchy."""

    account: Account
    children: List["AccountHierarchyResponse"]
    values: List[Dict[str, Any]]


class PeriodSummary(BaseModel):
    """Summary statistics for a specific period."""

    period_start: date
    period_end: date
    total_revenue: float
    total_expenses: float
    net_profit: float
    currency: str
    record_count: int
    sources: List[str]


@router.get(
    "/", response_model=FinancialDataResponse, summary="Retrieve Financial Records"
)
async def get_financial_data(
    # Pagination parameters
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    # Filtering parameters
    source: Optional[SourceType] = Query(None, description="Filter by data source"),
    period_start: Optional[date] = Query(
        None, description="Filter by period start date (inclusive)"
    ),
    period_end: Optional[date] = Query(
        None, description="Filter by period end date (inclusive)"
    ),
    currency: Optional[str] = Query(None, description="Filter by currency code"),
    min_revenue: Optional[float] = Query(
        None, ge=0, description="Minimum revenue filter"
    ),
    max_revenue: Optional[float] = Query(
        None, ge=0, description="Maximum revenue filter"
    ),
    min_expenses: Optional[float] = Query(
        None, ge=0, description="Minimum expenses filter"
    ),
    max_expenses: Optional[float] = Query(
        None, ge=0, description="Maximum expenses filter"
    ),
    # Sorting parameters
    sort_by: str = Query("period_start", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
) -> FinancialDataResponse:
    """
    Retrieve financial records with filtering and pagination.

    Supports filtering by source, date ranges, currency, and financial metrics.
    Results are paginated and can be sorted by various fields.

    **Example Usage:**
    ```
    GET /api/v1/financial-data?source=quickbooks&page=1&page_size=10
    GET /api/v1/financial-data?period_start=2024-01-01&period_end=2024-03-31
    GET /api/v1/financial-data?min_revenue=10000&sort_by=revenue&sort_order=desc
    ```

    **Example Response:**
    ```json
    {
        "data": [
            {
                "id": "qb_2024_q1",
                "source": "quickbooks",
                "period_start": "2024-01-01",
                "period_end": "2024-03-31",
                "currency": "USD",
                "revenue": 125000.00,
                "expenses": 85000.00,
                "net_profit": 40000.00,
                "created_at": "2024-04-01T10:00:00Z",
                "updated_at": "2024-04-01T10:00:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 10,
            "total_pages": 5,
            "has_next": true,
            "has_prev": false
        },
        "total_count": 45,
        "filters_applied": {"source": "quickbooks"}
    }
    ```

    Args:
        page: Page number (1-based)
        page_size: Number of items per page (max 100)
        source: Filter by data source (quickbooks, rootfi)
        period_start: Filter records with period_start >= this date
        period_end: Filter records with period_end <= this date
        currency: Filter by currency code (e.g., USD, EUR)
        min_revenue: Minimum revenue threshold
        max_revenue: Maximum revenue threshold
        min_expenses: Minimum expenses threshold
        max_expenses: Maximum expenses threshold
        sort_by: Field to sort by (period_start, revenue, expenses, net_profit, created_at)
        sort_order: Sort order (asc, desc)

    Returns:
        FinancialDataResponse with paginated results and metadata

    Raises:
        HTTPException: If invalid parameters or database error occurs
    """
    logger.info(
        "Retrieving financial data: page=%d, page_size=%d, source=%s",
        page,
        page_size,
        source,
    )

    try:
        with get_db_session() as session:

            query = session.query(FinancialRecordDB)

            # Apply filters
            filters = []
            filters_applied = {}

            if source:
                filters.append(FinancialRecordDB.source == source.value)
                filters_applied["source"] = source.value

            if period_start:
                filters.append(FinancialRecordDB.period_start >= period_start)
                filters_applied["period_start_gte"] = period_start.isoformat()

            if period_end:
                filters.append(FinancialRecordDB.period_end <= period_end)
                filters_applied["period_end_lte"] = period_end.isoformat()

            if currency:
                filters.append(FinancialRecordDB.currency == currency.upper())
                filters_applied["currency"] = currency.upper()

            if min_revenue is not None:
                filters.append(FinancialRecordDB.revenue >= min_revenue)
                filters_applied["min_revenue"] = min_revenue

            if max_revenue is not None:
                filters.append(FinancialRecordDB.revenue <= max_revenue)
                filters_applied["max_revenue"] = max_revenue

            if min_expenses is not None:
                filters.append(FinancialRecordDB.expenses >= min_expenses)
                filters_applied["min_expenses"] = min_expenses

            if max_expenses is not None:
                filters.append(FinancialRecordDB.expenses <= max_expenses)
                filters_applied["max_expenses"] = max_expenses

            # Apply all filters
            if filters:
                query = query.filter(and_(*filters))

            # Get total count before pagination
            total_count = query.count()

            # Apply sorting
            sort_field = getattr(FinancialRecordDB, sort_by, None)
            if sort_field is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid sort field: {sort_by}. Valid fields: period_start, revenue, expenses, net_profit, created_at",
                )

            if sort_order == "desc":
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(sort_field)

            # Apply pagination
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size)

            # Execute query
            db_records = query.all()

            # Convert to Pydantic models
            financial_records = []
            for db_record in db_records:
                financial_record = FinancialRecord(
                    id=db_record.id,
                    source=SourceType(db_record.source),
                    period_start=db_record.period_start,
                    period_end=db_record.period_end,
                    currency=db_record.currency,
                    revenue=db_record.revenue,
                    expenses=db_record.expenses,
                    net_profit=db_record.net_profit,
                    created_at=db_record.created_at,
                    updated_at=db_record.updated_at,
                )
                financial_records.append(financial_record)

            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size
            has_next = page < total_pages
            has_prev = page > 1

            pagination = {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_prev": has_prev,
                "next_page": page + 1 if has_next else None,
                "prev_page": page - 1 if has_prev else None,
            }

            logger.info(
                "Financial data retrieved successfully: %d records, page %d/%d",
                len(financial_records),
                page,
                total_pages,
            )

            return FinancialDataResponse(
                data=financial_records,
                pagination=pagination,
                total_count=total_count,
                filters_applied=filters_applied,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve financial data: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve financial data: {str(e)}"
        )


@router.get("/{period}", response_model=PeriodSummary)
async def get_financial_data_by_period(
    period: str = Path(
        ..., description="Period identifier (YYYY-MM or YYYY-Q1/Q2/Q3/Q4 or YYYY)"
    ),
    source: Optional[SourceType] = Query(None, description="Filter by data source"),
    currency: Optional[str] = Query(None, description="Filter by currency code"),
) -> PeriodSummary:
    """
    Get aggregated financial data for a specific period.

    Supports various period formats:
    - Monthly: YYYY-MM (e.g., 2024-03)
    - Quarterly: YYYY-Q1, YYYY-Q2, YYYY-Q3, YYYY-Q4 (e.g., 2024-Q1)
    - Yearly: YYYY (e.g., 2024)

    Args:
        period: Period identifier in supported format
        source: Optional filter by data source
        currency: Optional filter by currency code

    Returns:
        PeriodSummary with aggregated financial metrics for the period

    Raises:
        HTTPException: If invalid period format or no data found
    """
    logger.info("Retrieving financial data for period: %s", period)

    try:
        # Parse period to date range
        period_start, period_end = _parse_period(period)

        with get_db_session() as session:
            # Build query with period filter
            query = session.query(FinancialRecordDB).filter(
                and_(
                    FinancialRecordDB.period_start >= period_start,
                    FinancialRecordDB.period_end <= period_end,
                )
            )

            # Apply additional filters
            filters_applied = {"period": period}

            if source:
                query = query.filter(FinancialRecordDB.source == source.value)
                filters_applied["source"] = source.value

            if currency:
                query = query.filter(FinancialRecordDB.currency == currency.upper())
                filters_applied["currency"] = currency.upper()

            # Get records for the period
            records = query.all()

            if not records:
                raise HTTPException(
                    status_code=404,
                    detail=f"No financial data found for period: {period}",
                )

            # Calculate aggregated metrics
            total_revenue = sum(float(record.revenue) for record in records)
            total_expenses = sum(float(record.expenses) for record in records)
            net_profit = total_revenue - total_expenses

            # Get unique currencies and sources
            currencies = list(set(record.currency for record in records))
            sources = list(set(record.source for record in records))

            # Use the most common currency if multiple currencies exist
            if len(currencies) > 1:
                logger.warning(
                    "Multiple currencies found for period %s: %s", period, currencies
                )

            primary_currency = currencies[0] if currencies else "USD"

            logger.info(
                "Period summary calculated: period=%s, revenue=%.2f, expenses=%.2f, profit=%.2f",
                period,
                total_revenue,
                total_expenses,
                net_profit,
            )

            return PeriodSummary(
                period_start=period_start,
                period_end=period_end,
                total_revenue=total_revenue,
                total_expenses=total_expenses,
                net_profit=net_profit,
                currency=primary_currency,
                record_count=len(records),
                sources=sources,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve period data: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve period data: {str(e)}"
        )


@router.get("/accounts/", response_model=AccountResponse)
async def get_accounts(
    account_type: Optional[AccountType] = Query(
        None, description="Filter by account type"
    ),
    source: Optional[SourceType] = Query(None, description="Filter by data source"),
    parent_account_id: Optional[str] = Query(
        None, description="Filter by parent account ID"
    ),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in account names"),
) -> AccountResponse:
    """
    Retrieve accounts with optional filtering.

    Supports filtering by account type, source, parent account, active status,
    and text search in account names.

    Args:
        account_type: Filter by account type (revenue, expense, asset, liability, equity)
        source: Filter by data source (quickbooks, rootfi)
        parent_account_id: Filter by parent account ID (for hierarchical queries)
        is_active: Filter by active status
        search: Search term for account names (case-insensitive partial match)

    Returns:
        AccountResponse with filtered account list

    Raises:
        HTTPException: If database error occurs
    """
    logger.info(
        "Retrieving accounts with filters: type=%s, source=%s", account_type, source
    )

    try:
        with get_db_session() as session:

            query = session.query(AccountDB)

            # Apply filters
            filters_applied = {}

            if account_type:
                query = query.filter(AccountDB.account_type == account_type.value)
                filters_applied["account_type"] = account_type.value

            if source:
                query = query.filter(AccountDB.source == source.value)
                filters_applied["source"] = source.value

            if parent_account_id is not None:
                query = query.filter(AccountDB.parent_account_id == parent_account_id)
                filters_applied["parent_account_id"] = parent_account_id

            if is_active is not None:
                query = query.filter(AccountDB.is_active == is_active)
                filters_applied["is_active"] = is_active

            if search:
                search_term = f"%{search}%"
                query = query.filter(AccountDB.name.ilike(search_term))
                filters_applied["search"] = search

            # Order by name for consistent results
            query = query.order_by(AccountDB.name)

            # Execute query
            db_accounts = query.all()

            accounts = []
            for db_account in db_accounts:
                account = Account(
                    account_id=db_account.account_id,
                    name=db_account.name,
                    account_type=AccountType(db_account.account_type),
                    parent_account_id=db_account.parent_account_id,
                    source=SourceType(db_account.source),
                    description=db_account.description,
                    is_active=db_account.is_active,
                    created_at=db_account.created_at,
                    updated_at=db_account.updated_at,
                )
                accounts.append(account)

            logger.info("Accounts retrieved successfully: %d accounts", len(accounts))

            return AccountResponse(
                data=accounts,
                total_count=len(accounts),
                filters_applied=filters_applied,
            )

    except Exception as e:
        logger.error("Failed to retrieve accounts: %s", str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve accounts: {str(e)}"
        )


@router.get("/accounts/{account_id}", response_model=Account)
async def get_account_by_id(
    account_id: str = Path(..., description="Account ID to retrieve")
) -> Account:
    """
    Retrieve a specific account by its ID.

    Args:
        account_id: Unique account identifier

    Returns:
        Account details

    Raises:
        HTTPException: If account not found or database error occurs
    """
    logger.info("Retrieving account by ID: %s", account_id)

    try:
        with get_db_session() as session:
            db_account = (
                session.query(AccountDB)
                .filter(AccountDB.account_id == account_id)
                .first()
            )

            if not db_account:
                raise HTTPException(
                    status_code=404, detail=f"Account not found: {account_id}"
                )

            account = Account(
                account_id=db_account.account_id,
                name=db_account.name,
                account_type=AccountType(db_account.account_type),
                parent_account_id=db_account.parent_account_id,
                source=SourceType(db_account.source),
                description=db_account.description,
                is_active=db_account.is_active,
                created_at=db_account.created_at,
                updated_at=db_account.updated_at,
            )

            logger.info("Account retrieved successfully: %s", account_id)
            return account

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve account %s: %s", account_id, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve account: {str(e)}"
        )


@router.get("/accounts/{account_id}/hierarchy", response_model=AccountHierarchyResponse)
async def get_account_hierarchy(
    account_id: str = Path(..., description="Root account ID for hierarchy")
) -> AccountHierarchyResponse:
    """
    Retrieve account hierarchy starting from a specific account.

    Returns the account and all its child accounts in a hierarchical structure,
    along with associated financial values.

    Args:
        account_id: Root account ID to start hierarchy from

    Returns:
        AccountHierarchyResponse with nested account structure

    Raises:
        HTTPException: If account not found or database error occurs
    """
    logger.info("Retrieving account hierarchy for: %s", account_id)

    try:
        with get_db_session() as session:
            # Get the root account
            root_account = (
                session.query(AccountDB)
                .filter(AccountDB.account_id == account_id)
                .first()
            )

            if not root_account:
                raise HTTPException(
                    status_code=404, detail=f"Account not found: {account_id}"
                )

            # Build hierarchy recursively
            hierarchy = _build_account_hierarchy(session, root_account)

            logger.info("Account hierarchy retrieved successfully for: %s", account_id)
            return hierarchy

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve account hierarchy %s: %s", account_id, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve account hierarchy: {str(e)}"
        )


def _parse_period(period: str) -> tuple[date, date]:
    """
    Parse period string into start and end dates.

    Args:
        period: Period string (YYYY-MM, YYYY-Q1/Q2/Q3/Q4, or YYYY)

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        ValueError: If period format is invalid
    """
    import re
    from datetime import datetime
    from calendar import monthrange

    # Monthly format: YYYY-MM
    if re.match(r"^\d{4}-\d{2}$", period):
        year, month = map(int, period.split("-"))
        start_date = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end_date = date(year, month, last_day)
        return start_date, end_date

    # Quarterly format: YYYY-Q1/Q2/Q3/Q4
    if re.match(r"^\d{4}-Q[1-4]$", period):
        year_str, quarter_str = period.split("-Q")
        year = int(year_str)
        quarter = int(quarter_str)

        quarter_months = {
            1: (1, 3),  # Q1: Jan-Mar
            2: (4, 6),  # Q2: Apr-Jun
            3: (7, 9),  # Q3: Jul-Sep
            4: (10, 12),  # Q4: Oct-Dec
        }

        start_month, end_month = quarter_months[quarter]
        start_date = date(year, start_month, 1)
        _, last_day = monthrange(year, end_month)
        end_date = date(year, end_month, last_day)
        return start_date, end_date

    # Yearly format: YYYY
    if re.match(r"^\d{4}$", period):
        year = int(period)
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)
        return start_date, end_date

    raise ValueError(
        f"Invalid period format: {period}. Supported formats: YYYY-MM, YYYY-Q1/Q2/Q3/Q4, YYYY"
    )


def _build_account_hierarchy(session, account: AccountDB) -> AccountHierarchyResponse:
    """
    Recursively build account hierarchy.

    Args:
        session: Database session
        account: Root account to build hierarchy from

    Returns:
        AccountHierarchyResponse with nested structure
    """
    # Convert account to Pydantic model
    account_model = Account(
        account_id=account.account_id,
        name=account.name,
        account_type=AccountType(account.account_type),
        parent_account_id=account.parent_account_id,
        source=SourceType(account.source),
        description=account.description,
        is_active=account.is_active,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )

    # Get child accounts
    children_db = (
        session.query(AccountDB)
        .filter(AccountDB.parent_account_id == account.account_id)
        .order_by(AccountDB.name)
        .all()
    )

    # Recursively build child hierarchies
    children = [_build_account_hierarchy(session, child) for child in children_db]

    # Get account values
    account_values = (
        session.query(AccountValueDB)
        .filter(AccountValueDB.account_id == account.account_id)
        .all()
    )

    values = [
        {
            "financial_record_id": av.financial_record_id,
            "value": float(av.value),
            "created_at": av.created_at.isoformat(),
        }
        for av in account_values
    ]

    return AccountHierarchyResponse(
        account=account_model, children=children, values=values
    )
