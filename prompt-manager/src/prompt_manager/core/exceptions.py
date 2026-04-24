"""
Domain exceptions for Prompt Manager.
"""

class PromptManagerError(Exception):
    """Base exception for all Prompt Manager errors."""
    pass

class PromptNotFoundError(PromptManagerError):
    """Raised when a requested prompt ID or version cannot be found."""
    pass

class PromptValidationError(PromptManagerError):
    """Raised when a prompt template or definition fails validation."""
    pass

class PromptRenderError(PromptManagerError):
    """Raised when variable injection or rendering fails."""
    pass

class PromptSecurityError(PromptManagerError):
    """Raised when a prompt fails security checks (e.g. Injection or PII)."""
    pass

class StorageBackendError(PromptManagerError):
    """Raised when the storage backend fails to read or write."""
    pass

class PromptVersionError(PromptManagerError):
    """Raised on invalid version transitions or missing versions."""
    pass
