"""
Few-Shot Template Implementation for ADK.
"""

from typing import Any, Dict
from .base import PromptTemplate
from ..core.exceptions import PromptRenderError, PromptValidationError

class FewShotTemplate(PromptTemplate):
    """
    Concrete implementation producing a Few-Shot ADK instruction.
    Injects `<examples>` block.
    """

    def _validate_template(self) -> None:
        super()._validate_template()
        if not self.definition.examples:
            raise PromptValidationError("FewShotTemplate requires at least one Example object.")

    def build_task_instruction(self, variables: Dict[str, Any]) -> str:
        if not self.definition.user_message_template:
            return ""
            
        try:
            rendered_task = self.definition.user_message_template.format(**variables)
            return f"<task>\n{rendered_task}\n</task>"
        except KeyError as e:
            raise PromptRenderError(f"Failed to inject variable into Few-Shot template: {e}")

    def build_examples(self) -> str:
        """Actively loops through the examples and compiles them via XML tags."""
        compiled_examples = ["<examples>"]

        for i, example in enumerate(self.definition.examples, 1):
            block = f"  <example index=\"{i}\">\n    <input>{example.input}</input>\n    <output>{example.output}</output>"
            if example.explanation:
                block += f"\n    <reasoning>{example.explanation}</reasoning>"
            block += "\n  </example>"
            compiled_examples.append(block)

        compiled_examples.append("</examples>")
        return "\n".join(compiled_examples)

    def build_constraints(self) -> str:
        return "<constraints>\nFormat your response exactly matching the pattern provided in the examples.\n</constraints>"