"""
ADK Prompt Manager Facade.

The single entry point for enterprise ADK Agent prompt management.
"""

from typing import Dict, Any, List, Optional
from ..core.models import TemplateDefinition, PromptMetadata, RenderedInstruction
from ..core.exceptions import PromptNotFoundError
from ..storage.base import StorageBackend
from ..security.base import SecurityPipeline, SecurityMiddleware
from ..security.injection import InjectionGuard
from ..security.pii_scrubber import PIIScrubber
from .factory import TemplateFactory

class PromptManager:
    """
    Enterprise-grade Prompt Manager specifically tuned for Google ADK Agents.
    """
    
    def __init__(
        self, 
        storage_backend: StorageBackend, 
        security_middlewares: Optional[List[SecurityMiddleware]] = None
    ):
        """
        Initialize the ADK Prompt Manager.
        
        Args:
            storage_backend: Implementation of StorageBackend (e.g. FileSystemStorage)
            security_middlewares: Optional list of SecurityMiddleware to run variables through.
                                  If None, InjectionGuard and PIIScrubber are used by default.
        """
        self.storage = storage_backend
        
        if security_middlewares is None:
            security_middlewares = [InjectionGuard(), PIIScrubber()]
        self.security = SecurityPipeline(security_middlewares)

    def register(self, definition: TemplateDefinition) -> None:
        """
        Save a new TemplateDefinition schema.
        """
        self.storage.save(definition)

    def render(self, prompt_id: str, variables: Dict[str, Any], version: Optional[str] = None) -> RenderedInstruction:
        """
        Renders a fully-formed ADK instruction string.
        
        Args:
            prompt_id: The ID of the prompt template
            variables: Runtime variables to inject
            version: Target version. If None, we load the highest version (if storage supports it)
                     Note: The current FileSystemStorage implementation expects explicit versioning,
                     so you should supply it, but we fallback trying to find the highest automatically.
        """
        if version is None:
            # Try to grab the latest active version
            versions = self.storage.list_versions(prompt_id)
            if not versions:
                raise PromptNotFoundError(f"No versions found for prompt {prompt_id}")
            # Naive string sort for versioning (e.g. v1.0.0 < v1.1.0)
            latest_version_meta = sorted(versions, key=lambda v: v.version)[-1]
            version = latest_version_meta.version

        # 1. Load Definition
        definition = self.storage.load(prompt_id, version)

        # 2. Security Interception
        sanitized_vars = self.security.sanitize_variables(variables)

        # 3. Render Template
        template_formatter = TemplateFactory.create(definition)
        rendered_instruction = template_formatter.render(sanitized_vars)

        return rendered_instruction

    def get_adk_instruction_string(self, prompt_id: str, variables: Dict[str, Any], version: Optional[str] = None) -> str:
        """
        Convenience wrapper that directly returns the raw XML-demarcated string 
        so you can pass it directly into ADK Agent(instruction=...).
        """
        rendered = self.render(prompt_id, variables, version)
        return rendered.text

    def list_available_prompts(self) -> List[PromptMetadata]:
        """List all managed prompts available."""
        return self.storage.list_prompts()
