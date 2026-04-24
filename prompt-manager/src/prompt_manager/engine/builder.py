"""
Fluent Builder for ADK definitions.
"""

from typing import List, Optional, Any
from ..core.models import (
    TemplateDefinition, PromptMetadata, PromptType, PromptStatus, 
    VariableType, PromptVariable, Example
)

class PromptBuilder:
    """
    Fluent builder for constructing TemplateDefinition schemas programmatically.
    """
    def __init__(self, prompt_id: str, author: str):
        self._prompt_id = prompt_id
        self._version = "v1.0.0"
        self._type = PromptType.ZERO_SHOT
        self._author = author
        self._description = ""
        self._tags: List[str] = []
        self._status = PromptStatus.DRAFT
        self._system_message = ""
        self._user_template = ""
        self._variables: List[PromptVariable] = []
        self._examples: List[Example] = []

    def with_version(self, version: str) -> "PromptBuilder":
        self._version = version
        return self

    def with_type(self, ptype: PromptType) -> "PromptBuilder":
        self._type = ptype
        return self

    def with_description(self, desc: str) -> "PromptBuilder":
        self._description = desc
        return self

    def add_tag(self, tag: str) -> "PromptBuilder":
        self._tags.append(tag)
        return self

    def with_status(self, status: PromptStatus) -> "PromptBuilder":
        self._status = status
        return self

    def with_system_message(self, msg: str) -> "PromptBuilder":
        self._system_message = msg
        return self

    def with_user_template(self, tmpl: str) -> "PromptBuilder":
        self._user_template = tmpl
        return self

    def add_variable(
        self, name: str, desc: str, vtype: VariableType = VariableType.STRING, 
        required: bool = True, default: Any = None
    ) -> "PromptBuilder":
        self._variables.append(PromptVariable(
            name=name, type=vtype, description=desc, required=required, default=default
        ))
        return self

    def add_example(self, input_val: str, output_val: str, explanation: Optional[str] = None) -> "PromptBuilder":
        self._examples.append(Example(
            input=input_val, output=output_val, explanation=explanation
        ))
        return self

    def build(self) -> TemplateDefinition:
        metadata = PromptMetadata(
            prompt_id=self._prompt_id,
            version=self._version,
            prompt_type=self._type,
            created_by=self._author,
            description=self._description,
            tags=self._tags,
            status=self._status
        )
        return TemplateDefinition(
            metadata=metadata,
            system_message=self._system_message,
            user_message_template=self._user_template,
            variables=self._variables,
            examples=self._examples
        )
