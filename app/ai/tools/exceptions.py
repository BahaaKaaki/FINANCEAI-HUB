class FinancialAnalysisError(Exception):
    """Base exception for financial analysis operations."""
    pass


class ValidationError(FinancialAnalysisError):
    """Raised when input validation fails."""
    pass


class DataNotFoundError(FinancialAnalysisError):
    """Raised when required financial data is not found."""
    pass


class CalculationError(FinancialAnalysisError):
    """Raised when financial calculations fail."""
    pass


class ConfigurationError(FinancialAnalysisError):
    """Raised when tool configuration is invalid."""
    pass