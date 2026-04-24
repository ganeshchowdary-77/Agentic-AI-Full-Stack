"""
Base template class for generating ADK Agent Instructions.

Pattern: Template Method
Why?
- Defines algorithm skeleton
- Subclasses implement specific formatting algorithms
- Ensures consistent instruction generation that is optimized for LLMs
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import re

from ..core.models import RenderedInstruction, TemplateDefinition
from ..core.exceptions import PromptValidationError, PromptRenderError


class PromptTemplate(ABC):
    """
    Abstract base for all ADK instruction templates.

    Template Method Pattern:
    - render() is the template method that constructs the XML-demarcated string
    - Subclasses define the content of those tags.
    """

    def __init__(self, definition: TemplateDefinition):
        self.definition = definition
        self._validate_template()

    def _validate_template(self) -> None:
        """
        Validate template consistency by checking if user_message_template uses variables defined.
        """
        template_vars = set(re.findall(r'\{(\w+)\}', self.definition.user_message_template))
        required_vars = {v.name for v in self.definition.variables if v.required}

        missing = required_vars - template_vars
        if missing:
            raise PromptValidationError(f"Template missing required variables in the user template string: {missing}")

    def render(self, variables: Dict[str, Any]) -> RenderedInstruction:
        """
        Render the ADK instruction string (Template Method).
        
        This builds a heavily formatted Markdown/XML string optimized for
        the ADK Agent's memory constraints and focus.
        """
        self._validate_variables(variables)

        # Assemble the structured string blocks
        persona_block = self.build_persona()
        task_block = self.build_task_instruction(variables)
        examples_block = self.build_examples()
        constraints_block = self.build_constraints()

        # Compose them cleanly
        final_text = self.compose_instruction([
            persona_block, 
            task_block, 
            examples_block, 
            constraints_block
        ])

        return RenderedInstruction(
            metadata=self.definition.metadata,
            text=final_text,
            variables_used=variables
        )

    def _validate_variables(self, variables: Dict[str, Any]) -> None:
        """Ensure provided variables match schema definitions."""
        for var_def in self.definition.variables:
            if var_def.required and var_def.name not in variables:
                raise PromptRenderError(f"Required variable missing: {var_def.name}")

    # ===== ABSTRACT & VIRTUAL METHODS =====

    def build_persona(self) -> str:
        """Builds the <persona> metadata tag based on system message."""
        if not self.definition.system_message:
            return ""
        return f"<persona>\n{self.definition.system_message}\n</persona>"

    @abstractmethod
    def build_task_instruction(self, variables: Dict[str, Any]) -> str:
        """Injects dynamic runtime variables into the task description."""
        pass

    @abstractmethod
    def build_examples(self) -> str:
        """Builds the <examples> tag for few-shot/CoT instructions."""
        pass

    @abstractmethod
    def build_constraints(self) -> str:
        """Builds strict instructions, like CoT constraints or ReAct logic loops."""
        pass

    def compose_instruction(self, blocks: List[str]) -> str:
        """Combines all blocks, filtering empty ones, into the final string."""
        return "\n\n".join(filter(None, blocks)).strip()