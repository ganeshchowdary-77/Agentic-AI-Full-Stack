"""
Core domain models for the ADK Prompt Manager.

These models define the structure of prompt instructions, variables, and metadata
that are injected into Google ADK Agents.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class PromptType(str, Enum):
    """
    Cognitive architecture types for ADK instructions.
    
    Zero-shot: Direct instruction without examples
    Few-shot: Inclusion of explicit input/output examples
    Chain-of-thought: Forces step-by-step reasoning formulation
    ReAct: Specifically frames the prompt for tool-calling reasoning loops
    """
    ZERO_SHOT = "zero_shot"
    FEW_SHOT = "few_shot"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    REACT = "react"


class VariableType(str, Enum):
    """Supported types for prompt variable injection mapping."""
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    LIST = "list"
    DICT = "dict"
    BOOL = "bool"


class PromptStatus(str, Enum):
    """Lifecycle status of a prompt template."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class Example(BaseModel):
    """Single example for few-shot or CoT prompting."""
    input: str = Field(..., description="Input text")
    output: str = Field(..., description="Expected output")
    explanation: Optional[str] = Field(None, description="Reasoning or intermediate thought process")

    model_config = {"frozen": True}


class PromptVariable(BaseModel):
    """Variable definition for dynamic instruction injection."""
    name: str = Field(..., description="Variable name")
    type: VariableType = Field(default=VariableType.STRING, description="Expected type")
    description: str = Field(..., description="What this variable is for")
    required: bool = Field(True, description="Is this required?")
    default: Optional[Any] = Field(None, description="Default value")

    model_config = {"frozen": True}


class PromptMetadata(BaseModel):
    """Metadata for tracking ADK instructions."""
    prompt_id: str = Field(..., description="Logical identifier")
    version: str = Field(..., description="Semantic Version string, e.g. v1.0.0")
    prompt_type: PromptType = Field(..., description="Cognitive architecture")
    
    # Audit fields
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(..., description="Creator")

    # Discovery fields
    description: str = Field(..., description="What this instruction directs the agent to do")
    tags: List[str] = Field(default_factory=list, description="Search tags")

    # Lifecycle
    status: PromptStatus = Field(
        default=PromptStatus.DRAFT,
        description="Lifecycle status"
    )

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure version strings follow vX.Y.Z semantics."""
        if not v.startswith("v"):
            raise ValueError("Version must start with 'v' (e.g., 'v1.0.0')")
        return v


class TemplateDefinition(BaseModel):
    """
    Complete serializable definition of a prompt before it is rendered with dynamic variables.
    This acts as the schema saved to disk (YAML/JSON).
    """
    metadata: PromptMetadata
    system_message: str = Field(..., description="Core ADK instruction persona and mandate")
    user_message_template: str = Field(default="", description="The specific task instruction with {variables}")
    variables: List[PromptVariable] = Field(default_factory=list, description="Variables to inject")
    examples: List[Example] = Field(default_factory=list, description="Examples for few-shot prompting")

    model_config = {"frozen": True}


class RenderedInstruction(BaseModel):
    """
    The final instruction object containing the fully rendered string ready for ADK Agent injection.
    """
    metadata: PromptMetadata
    text: str = Field(..., description="The fully rendered instruction text to feed to ADK Agent")
    variables_used: Dict[str, Any] = Field(default_factory=dict, description="Variables that were injected")

    model_config = {"frozen": True}