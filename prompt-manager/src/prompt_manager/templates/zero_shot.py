"""
Zero-Shot Template Implementation for ADK.

Pattern: Template Method (Concrete Class)
Architecture: Zero-Shot (No examples, raw instruction)
"""

from typing import Any, Dict
from .base import PromptTemplate
from ..core.exceptions import PromptRenderError

class ZeroShotTemplate(PromptTemplate):
    """
    Concrete implementation producing a Zero-Shot ADK instruction.
    """

    def build_task_instruction(self, variables: Dict[str, Any]) -> str:
        if not self.definition.user_message_template:
            return ""
            
        try:
            rendered_task = self.definition.user_message_template.format(**variables)
            return f"<task>\n{rendered_task}\n</task>"
        except KeyError as e:
            raise PromptRenderError(f"Failed to inject variable into Zero-Shot template: {e}")

    def build_examples(self) -> str:
        """Zero-shot has no examples."""
        return ""

    def build_constraints(self) -> str:
        """Basic execution constraints for zero-shot logic."""
        return "<constraints>\nAnswer the task directly based on your persona.\n</constraints>"