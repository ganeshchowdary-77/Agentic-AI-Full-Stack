class CommercialAutoFraudError(Exception):
    """Base exception for the Commercial Auto Fraud application."""
    pass

class ValidationFailedError(CommercialAutoFraudError):
    """Raised when a claim or batch fails validation."""
    pass

class EnrichmentError(CommercialAutoFraudError):
    """Raised when external mock APIs fail to fetch data."""
    pass

class AnalysisTimeoutError(CommercialAutoFraudError):
    """Raised when a parallel pattern analysis takes too long or fails."""
    pass

