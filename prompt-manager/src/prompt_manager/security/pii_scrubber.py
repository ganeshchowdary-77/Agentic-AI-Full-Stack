"""
PII Scrubber Middleware.
"""

from typing import Dict, Any
import re
from .base import SecurityMiddleware

class PIIScrubber(SecurityMiddleware):
    """
    Sanitizes Personally Identifiable Information from variables
    before they are injected into LLM contexts.
    """
    
    # Very basic PII patterns for demonstration
    SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

    def process_input(self, variables: Dict[str, Any]) -> Dict[str, Any]:
        """
        Replaces matched PII patterns with [REDACTED].
        """
        for key, value in variables.items():
            if isinstance(value, str):
                # Scrub SSN
                value = self.SSN_PATTERN.sub("[REDACTED_SSN]", value)
                # Scrub Email
                value = self.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
                
                variables[key] = value
                
        return variables
