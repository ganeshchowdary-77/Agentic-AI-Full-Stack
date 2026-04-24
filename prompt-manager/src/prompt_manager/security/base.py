"""
Security Middleware logic for Prompt Manager.
"""

from typing import Protocol, Dict, Any, List

class SecurityMiddleware(Protocol):
    """
    Protocol for security middlewares.
    Middlewares intercept variables BEFORE they are injected into templates.
    """
    def process_input(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the incoming variables.
        Can either sanitize them (mutating and returning the dict)
        or raise a PromptSecurityError if a violation is detected.
        """
        ...

class SecurityPipeline:
    """
    Chains multiple security middlewares together.
    """
    def __init__(self, middlewares: List[SecurityMiddleware]):
        self.middlewares = middlewares

    def sanitize_variables(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all variables through the security pipeline.
        Creates a copy of the variables to ensure immutability of the original dict.
        """
        sanitized = variables.copy()
        for mw in self.middlewares:
            sanitized = mw.process_input(sanitized)
        return sanitized
