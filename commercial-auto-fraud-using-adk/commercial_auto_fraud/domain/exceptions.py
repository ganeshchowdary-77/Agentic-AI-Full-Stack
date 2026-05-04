"""
Domain Exceptions — Commercial Auto Fraud Detection Pipeline

Structured exception hierarchy for each pipeline stage.
"""


class FraudPipelineError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(self, message: str, claim_id: str = "", details: dict = None):
        self.claim_id = claim_id
        self.details = details or {}
        super().__init__(message)


class BatchValidationError(FraudPipelineError):
    """Raised when batch JSON fails schema validation."""
    pass


class EnrichmentError(FraudPipelineError):
    """Raised when an enrichment data source fails or returns invalid data."""
    pass


class AnalysisError(FraudPipelineError):
    """Raised when a fraud pattern analysis fails."""
    pass


class ReportGenerationError(FraudPipelineError):
    """Raised when investigation report generation fails."""
    pass


class DataProviderError(FraudPipelineError):
    """Raised when an external/mock data provider is unreachable."""
    pass


class TelemetryConfigurationError(FraudPipelineError):
    """Raised when telemetry/observability is misconfigured."""
    pass
