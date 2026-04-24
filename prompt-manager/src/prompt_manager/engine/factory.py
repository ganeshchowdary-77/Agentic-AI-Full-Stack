"""
Template Factory for mapping models to concrete ADK formatters.
"""

from ..core.models import PromptType, TemplateDefinition
from ..templates.base import PromptTemplate
from ..templates.zero_shot import ZeroShotTemplate
from ..templates.few_shot import FewShotTemplate
from ..templates.chain_of_thought import ChainOfThoughtTemplate
from ..templates.react import ReActTemplate

from typing import Type

class TemplateFactory:
    """
    Creates the appropriate ADK PromptTemplate subclass based on the definition's PromptType.
    """
    
    _MAPPING: dict[PromptType, Type[PromptTemplate]] = {
        PromptType.ZERO_SHOT: ZeroShotTemplate,
        PromptType.FEW_SHOT: FewShotTemplate,
        PromptType.CHAIN_OF_THOUGHT: ChainOfThoughtTemplate,
        PromptType.REACT: ReActTemplate
    }

    @classmethod
    def create(cls, definition: TemplateDefinition) -> PromptTemplate:
        template_class = cls._MAPPING.get(definition.metadata.prompt_type)
        if not template_class:
            raise ValueError(f"Unsupported prompt type: {definition.metadata.prompt_type}")
            
        return template_class(definition)
