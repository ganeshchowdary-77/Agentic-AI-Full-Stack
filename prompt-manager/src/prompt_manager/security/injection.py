"""
Injection Guard Middleware.
"""

from typing import Dict, Any
import re
from .base import SecurityMiddleware
from ..core.exceptions import PromptSecurityError

class InjectionGuard(SecurityMiddleware):
    """
    Detects catastrophic prompt injection patterns in user-supplied variables.
    """
    
    # Common injection keywords/patterns
    INJECTION_PATTERNS = [
        r"(?i)ignore\s+(all\s+)?(previous\s+)?instructions",
        r"(?i)system\s+prompt",
        r"(?i)forget\s+(all\s+)?rules",
        r"(?i)you\s+are\s+now"
    ]

    def __init__(self) -> None:
        self._compiled_patterns = [re.compile(p) for p in self.INJECTION_PATTERNS]

    def process_input(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan all string variables for injection attempts.
        Raises PromptSecurityError if found.
        """
        for key, value in variables.items():
            if isinstance(value, str):
                for pattern in self._compiled_patterns:
                    if pattern.search(value):
                        raise PromptSecurityError(
                            f"Potential prompt injection detected in variable '{key}'. "
                            f"Pattern matched: {pattern.pattern}"
                        )
        return variables
