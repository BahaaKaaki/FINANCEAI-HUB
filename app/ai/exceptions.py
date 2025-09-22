class FinancialAnalysisError(Exception):
    """Base exception for financial analysis tool errors."""

    pass


class ValidationError(FinancialAnalysisError):
    """Exception raised for input validation errors."""

    pass


class DataNotFoundError(FinancialAnalysisError):
    """Exception raised when requested data is not found."""

    pass
