"""
Storage Backend Protocol.
"""

from typing import Protocol, List
from ..core.models import TemplateDefinition, PromptMetadata

class StorageBackend(Protocol):
    """
    Protocol defining the interface for storing and retrieving ADK prompt templates.
    """

    def save(self, definition: TemplateDefinition) -> None:
        """Save a new template definition."""
        ...

    def load(self, prompt_id: str, version: str) -> TemplateDefinition:
        """Load a specific version of a template definition."""
        ...

    def list_prompts(self) -> List[PromptMetadata]:
        """List all available prompts."""
        ...

    def list_versions(self, prompt_id: str) -> List[PromptMetadata]:
        """List all versions of a specific prompt."""
        ...
