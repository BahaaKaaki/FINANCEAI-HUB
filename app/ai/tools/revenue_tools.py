from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import and_, func

from app.ai.exceptions import DataNotFoundError, FinancialAnalysisError, ValidationError
from app.ai.utils.validators import (
    validate_account_type,
    validate_date_range,
    validate_date_string,
    validate_source,
)
from app.core.logging import get_logger
from app.database.connection import get_db_session
from app.database.models import AccountDB, AccountValueDB, FinancialRecordDB

logger = get_logger(__name__)


def get_revenue_by_period(
    start_date: str,
    end_date: str,
    source: Optional[str] = None,
    account_type: Optional[str] = None,
    currency: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve revenue data for specified period with flexible filtering.

    This tool allows the AI agent to fetch revenue information for analysis,
    supporting various filtering options to narrow down the data.

    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Optional source filter ('quickbooks' or 'rootfi')
        account_type: Optional account type filter ('revenue', 'expense', etc.)
        currency: Optional currency filter (e.g., 'USD', 'EUR')

    Returns:
        Dictionary containing:
        - total_revenue: Total revenue for the period
        - record_count: Number of financial records found
        - currency: Currency of the results (if filtered)
        - period_start: Start date of the period
        - period_end: End date of the period
        - source_breakdown: Revenue breakdown by source
        - account_breakdown: Revenue breakdown by account (if account data available)

    Raises:
        ValidationError: If input parameters are invalid
        DataNotFoundError: If no data is found for the specified criteria
        FinancialAnalysisError: If database operation fails
    """
    logger.info("Getting revenue by period: %s to %s", start_date, end_date)

    try:

        start_dt = validate_date_string(start_date, "start_date")
        end_dt = validate_date_string(end_date, "end_date")
        validate_date_range(start_dt, end_dt)

        source_type = validate_source(source)
        account_type_enum = validate_account_type(account_type)

        if currency:
            currency = currency.upper()

        with get_db_session() as session:
            query = session.query(FinancialRecordDB).filter(
                and_(
                    FinancialRecordDB.period_start >= start_dt,
                    FinancialRecordDB.period_end <= end_dt,
                )
            )

            if source_type:
                query = query.filter(FinancialRecordDB.source == source_type.value)

            if currency:
                query = query.filter(FinancialRecordDB.currency == currency)

            records = query.all()

            if not records:
                raise DataNotFoundError(
                    f"No financial records found for period {start_date} to {end_date}"
                )

            # Calculate total revenue
            total_revenue = sum(record.revenue for record in records)

            source_breakdown = {}
            for record in records:
                if record.source not in source_breakdown:
                    source_breakdown[record.source] = Decimal("0")
                source_breakdown[record.source] += record.revenue

            # Get account breakdown if account_type is specified
            account_breakdown = {}
            if account_type_enum:
                # Query account values for revenue accounts
                account_query = (
                    session.query(
                        AccountDB.name,
                        func.sum(AccountValueDB.value).label("total_value"),
                    )
                    .join(
                        AccountValueDB,
                        AccountDB.account_id == AccountValueDB.account_id,
                    )
                    .join(
                        FinancialRecordDB,
                        AccountValueDB.financial_record_id == FinancialRecordDB.id,
                    )
                    .filter(
                        and_(
                            AccountDB.account_type == account_type_enum.value,
                            FinancialRecordDB.period_start >= start_dt,
                            FinancialRecordDB.period_end <= end_dt,
                        )
                    )
                )

                if source_type:
                    account_query = account_query.filter(
                        FinancialRecordDB.source == source_type.value
                    )

                if currency:
                    account_query = account_query.filter(
                        FinancialRecordDB.currency == currency
                    )

                account_results = account_query.group_by(AccountDB.name).all()

                for account_name, total_value in account_results:
                    account_breakdown[account_name] = (
                        float(total_value) if total_value else 0.0
                    )

            result = {
                "total_revenue": float(total_revenue),
                "record_count": len(records),
                "currency": currency or "mixed",
                "period_start": start_date,
                "period_end": end_date,
                "source_breakdown": {k: float(v) for k, v in source_breakdown.items()},
                "account_breakdown": account_breakdown,
            }

            logger.info(
                "Revenue analysis completed: total=%s, records=%d",
                total_revenue,
                len(records),
            )
            return result

    except (ValidationError, DataNotFoundError):
        raise
    except Exception as e:
        logger.error("Error in get_revenue_by_period: %s", str(e))
        raise FinancialAnalysisError(
            f"Failed to retrieve revenue data: {str(e)}"
        ) from e
