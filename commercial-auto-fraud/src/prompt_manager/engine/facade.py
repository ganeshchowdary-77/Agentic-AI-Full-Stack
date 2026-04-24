"""
PromptFacade — Versioned Prompt Manager
=========================================
Single access point for ALL agent prompts in the system.

Priority chain (first match wins):
  1. YAML file: storage/prompts/{name}/v{N}.yaml  (versioned, A/B testable)
  2. Python constant fallback (backward compatibility)

Usage:
  prompt = PromptFacade.get_prompt("duplicate_similar_cot", {
      "claim_id": "CLM-001",
      "enriched_data": "...",
  })

  # Pin a specific version (A/B testing):
  prompt = PromptFacade.get_prompt("duplicate_similar_cot", context, version="1")

Adding a new agent prompt:
  1. Create storage/prompts/{name}/v1.yaml  with a `content:` field
  2. Register the key in REGISTRY below
  3. Call PromptFacade.get_prompt("{name}", context) in your agent
  No other changes needed.
"""

import os
import re
from typing import Any, Dict, Optional

import yaml

# ── Python fallback constants (kept for backward compat) ───────────────────
import src.prompt_manager.templates.chain_of_thought as cot
import src.prompt_manager.templates.react as react
import src.prompt_manager.templates.report as report

PYTHON_FALLBACKS: Dict[str, str] = {
    "duplicate_similar_cot": cot.DUPLICATE_SIMILAR_COT_PROMPT,
    "suspicious_timing_cot": cot.SUSPICIOUS_TIMING_COT_PROMPT,
    "inflated_amounts_cot":  cot.INFLATED_AMOUNTS_COT_PROMPT,
    "provider_network_cot":  cot.PROVIDER_NETWORK_COT_PROMPT,
    "enrichment_react":      react.ENRICHMENT_REACT_PROMPT,
    "investigation_report":  report.INVESTIGATION_REPORT_PROMPT,
    "orchestrator_system":   report.ORCHESTRATOR_SYSTEM_PROMPT,
}

# ── YAML prompt registry — all registered prompt keys ─────────────────────
REGISTRY = {
    # Orchestrator
    "orchestrator_system",
    # Analyzer patterns (Few-Shot + CoT)
    "duplicate_similar_cot",    # Few-shot examples + CoT (spec 10.1.2 + 10.1.3)
    "suspicious_timing_cot",    # CoT (spec 10.1.3)
    "inflated_amounts_cot",     # CoT (spec 10.1.3)
    "provider_network_cot",     # CoT (spec 10.1.3)
    "composite_score_cot",      # CoT — weighted scoring + narrative coherence (spec 10.1.3 #15)
    "fraud_classification_fewshot",  # Few-shot — FLAGGED/CLEAN with priority tier (spec 11.4)
    # Enrichment
    "enrichment_react",         # Full THOUGHT/ACTION/OBSERVATION ReAct (spec 10.1.4)
    # Report generator
    "investigation_report",
    # SIU query chat personas
    "kevin_query",
    "diana_query",
}

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "storage", "prompts")
_yaml_cache:  Dict[str, str] = {}
_usage_log:   list = []   # [{template, version, timestamp}] — fed into Arize span attributes
_dir_cache:   Dict[str, str] = {}  # prompt_name → resolved directory path


def _resolve_prompt_dir(name: str) -> Optional[str]:
    """
    Resolves a prompt name to its directory path.
    Supports the agent-grouped structure:
      storage/prompts/{agent_folder}/{prompt_name}/v1.yaml
    Also supports flat structure for backward compatibility:
      storage/prompts/{prompt_name}/v1.yaml
    """
    if name in _dir_cache:
        return _dir_cache[name]

    # 1. Check flat path (backward compat)
    flat = os.path.join(_PROMPTS_DIR, name)
    if os.path.isdir(flat):
        _dir_cache[name] = flat
        return flat

    # 2. Search inside agent subdirectories
    if os.path.isdir(_PROMPTS_DIR):
        for agent_folder in os.listdir(_PROMPTS_DIR):
            agent_path = os.path.join(_PROMPTS_DIR, agent_folder)
            if os.path.isdir(agent_path):
                nested = os.path.join(agent_path, name)
                if os.path.isdir(nested):
                    _dir_cache[name] = nested
                    return nested

    return None


def _load_yaml_prompt(name: str, version: Optional[str] = None) -> Optional[str]:
    """
    Loads prompt content from storage/prompts/{agent}/{name}/v{N}.yaml.
    If version is None, loads the highest available version.
    Returns None if no YAML file exists.
    """
    cache_key = f"{name}:{version or 'latest'}"
    if cache_key in _yaml_cache:
        return _yaml_cache[cache_key]

    prompt_dir = _resolve_prompt_dir(name)
    if prompt_dir is None:
        return None

    if version:
        candidates = [f"v{version}.yaml"]
    else:
        # Find highest version number
        files = [f for f in os.listdir(prompt_dir) if re.match(r"v\d+\.yaml$", f)]
        if not files:
            return None
        candidates = sorted(files, key=lambda f: int(re.search(r"\d+", f).group()), reverse=True)

    for candidate in candidates:
        path = os.path.join(prompt_dir, candidate)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            content = data.get("content") or data.get("system_instruction", "")
            _yaml_cache[cache_key] = content
            return content

    return None


class PromptFacade:
    """
    Versioned prompt manager facade.
    All agents call PromptFacade.get_prompt() — never hardcode strings.
    """

    @classmethod
    def get_prompt(
        cls,
        template_name: str,
        context: Dict[str, Any] = None,
        version: Optional[str] = None,
    ) -> str:
        """
        Retrieves and formats a prompt template with context variables.

        Args:
            template_name: Registered prompt key (e.g., "duplicate_similar_cot")
            context:        Dict of variables to interpolate into the template
            version:        Pin a specific version string (e.g., "1"). Default: latest.

        Returns:
            Formatted prompt string.

        Raises:
            ValueError: If the prompt key is not found in YAML or fallbacks.
        """
        if context is None:
            context = {}

        # 1. Try YAML (versioned storage)
        content = _load_yaml_prompt(template_name, version)

        # 2. Fall back to Python constants
        if content is None:
            content = PYTHON_FALLBACKS.get(template_name)

        if content is None:
            available = sorted(REGISTRY)
            raise ValueError(
                f"Prompt '{template_name}' not found. "
                f"Registered keys: {available}"
            )

        # Log usage — consumed by Arize spans as prompt_template / prompt_version
        _usage_log.append({
            "template":  template_name,
            "version":   version or "latest",
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
        })

        # Interpolate context variables
        try:
            return content.format_map(context)
        except KeyError as e:
            raise ValueError(
                f"Prompt '{template_name}' requires variable {e} "
                f"but it was not provided in context."
            )

    @classmethod
    def get_last_usage(cls) -> Dict[str, str]:
        """
        Returns the most recent prompt usage record.
        Callers (agents) use this to set Arize span attributes:
          span.set_attribute("prompt_template", PromptFacade.get_last_usage()["template"])
          span.set_attribute("prompt_version",  PromptFacade.get_last_usage()["version"])
        """
        return _usage_log[-1] if _usage_log else {"template": "", "version": ""}

    @classmethod
    def get_usage_log(cls) -> list:
        """Full prompt usage audit trail. Mirrors spec's PromptManager.get_usage_log()."""
        return list(_usage_log)

    @classmethod
    def list_prompts(cls) -> list[str]:
        """Returns all registered prompt keys."""
        return sorted(REGISTRY)

    @classmethod
    def get_version_info(cls, template_name: str) -> Dict[str, Any]:
        """Returns metadata (version, description, agent) from the YAML file."""
        prompt_dir = _resolve_prompt_dir(template_name)
        if prompt_dir is None:
            return {"source": "python_fallback", "name": template_name}

        files = sorted(
            [f for f in os.listdir(prompt_dir) if re.match(r"v\d+\.yaml$", f)],
            key=lambda f: int(re.search(r"\d+", f).group()),
            reverse=True,
        )
        if not files:
            return {"source": "python_fallback", "name": template_name}

        path = os.path.join(prompt_dir, files[0])
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return {
            "source": "yaml",
            "name": template_name,
            "version": data.get("version"),
            "description": data.get("description"),
            "agent": data.get("agent"),
            "model": data.get("model"),
        }

