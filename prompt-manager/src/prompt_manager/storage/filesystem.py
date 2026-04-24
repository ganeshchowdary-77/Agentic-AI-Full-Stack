"""
FileSystem Storage Backend.
"""

import json
from pathlib import Path
from typing import List

from .base import StorageBackend
from ..core.models import TemplateDefinition, PromptMetadata
from ..core.exceptions import StorageBackendError, PromptNotFoundError

class FileSystemStorage(StorageBackend):
    """
    Stores prompt templates as JSON files.
    Directory structure:
    base_dir/
      prompt_id/
        v1.0.0.json
        v1.1.0.json
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_prompt_dir(self, prompt_id: str) -> Path:
        return self.base_dir / prompt_id

    def _get_file_path(self, prompt_id: str, version: str) -> Path:
        return self._get_prompt_dir(prompt_id) / f"{version}.json"

    def save(self, definition: TemplateDefinition) -> None:
        try:
            prompt_dir = self._get_prompt_dir(definition.metadata.prompt_id)
            prompt_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = self._get_file_path(definition.metadata.prompt_id, definition.metadata.version)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # model_dump_json takes care of datetime objects etc
                f.write(definition.model_dump_json(indent=2))
                
        except Exception as e:
            raise StorageBackendError(f"Failed to save prompt {definition.metadata.prompt_id}: {e}")

    def load(self, prompt_id: str, version: str) -> TemplateDefinition:
        file_path = self._get_file_path(prompt_id, version)
        if not file_path.exists():
            raise PromptNotFoundError(f"Prompt {prompt_id} version {version} not found.")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return TemplateDefinition.model_validate(data)
        except Exception as e:
            raise StorageBackendError(f"Failed to load prompt {prompt_id}: {e}")

    def list_prompts(self) -> List[PromptMetadata]:
        """Lists the latest version of each prompt."""
        prompts = []
        try:
            for prompt_dir in self.base_dir.iterdir():
                if prompt_dir.is_dir():
                    # Just grab metadata of the first version we find for listing purposes
                    # In a real system, you'd sort by version and get the active/latest
                    versions = list(prompt_dir.glob("*.json"))
                    if versions:
                        latest = sorted(versions)[-1] # primitive version sort
                        with open(latest, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            prompts.append(TemplateDefinition.model_validate(data).metadata)
        except Exception as e:
            raise StorageBackendError(f"Failed to list prompts: {e}")
        return prompts

    def list_versions(self, prompt_id: str) -> List[PromptMetadata]:
        prompt_dir = self._get_prompt_dir(prompt_id)
        if not prompt_dir.exists():
            raise PromptNotFoundError(f"Prompt {prompt_id} not found.")
            
        versions = []
        try:
            for file_path in prompt_dir.glob("*.json"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    versions.append(TemplateDefinition.model_validate(data).metadata)
        except Exception as e:
            raise StorageBackendError(f"Failed to list versions for {prompt_id}: {e}")
            
        return versions
