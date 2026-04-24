"""
Chain-of-Thought (CoT) Template Implementation for ADK.
"""

from typing import Any, Dict
from .base import PromptTemplate
from ..core.exceptions import PromptRenderError

class ChainOfThoughtTemplate(PromptTemplate):
    """
    Concrete implementation for Chain-of-Thought (CoT) ADK instruction.
    Injects strict `<constraints>` for step-by-step reasoning.
    """

    def build_task_instruction(self, variables: Dict[str, Any]) -> str:
        if not self.definition.user_message_template:
            return ""
            
        try:
            rendered_task = self.definition.user_message_template.format(**variables)
            return f"<task>\n{rendered_task}\n</task>"
        except KeyError as e:
            raise PromptRenderError(f"Failed to inject variable into CoT template: {e}")

    def build_examples(self) -> str:
        if not self.definition.examples:
            return ""

        compiled_examples = ["<reasoning_examples>"]
        for i, example in enumerate(self.definition.examples, 1):
            reasoning = example.explanation or "Let's think step by step to arrive at the output."
            block = (f"  <example index=\"{i}\">\n"
                     f"    <input>{example.input}</input>\n"
                     f"    <reasoning>{reasoning}</reasoning>\n"
                     f"    <output>{example.output}</output>\n"
                     f"  </example>")
            compiled_examples.append(block)

        compiled_examples.append("</reasoning_examples>")
        return "\n".join(compiled_examples)

    def build_constraints(self) -> str:
        return ("<constraints>\n"
                "You must think step-by-step. Write out your reasoning process explicitly "
                "before providing the final answer.\n"
                "</constraints>")