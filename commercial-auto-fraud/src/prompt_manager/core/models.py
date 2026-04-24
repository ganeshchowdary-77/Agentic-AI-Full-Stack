from pydantic import BaseModel
from typing import Dict, Any

class PromptVersion(BaseModel):
    version: str
    content: str
    description: str

class PromptTemplateContext(BaseModel):
    template_name: str
    version: str
    variables: Dict[str, Any]

