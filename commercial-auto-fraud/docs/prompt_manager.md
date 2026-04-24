# Prompt Manager Architecture

The `prompt_manager` is the Cognitive Engine of the Commercial Auto Fraud application. Designed as a modular, loosely-coupled subsystem, it handles the generation, security, versioning, and validation of AI prompts before they are dispatched to the LLM backend.

## Directory Structure Overview

```text
src/prompt_manager/                 
├── __init__.py                 # Clean API exporter (exposes Facade)
├── core/                       # Foundational App Models & Exceptions
├── engine/                     # Orchestration (facade.py, builder.py, factory.py)
├── security/                   # Middleware (injection.py, pii_scrubber.py)
├── templates/                  # Rules (chain_of_thought.py, react.py, etc.)
└── storage/                    # Persistence (base.py, filesystem.py)
```

## Module Breakdown

### 1. External API (`__init__.py`)
The `prompt_manager` utilizes the **Facade Pattern**. External systems (like Application Agents) do not communicate with the individual internal components. The `__init__.py` file cleanly exports only the `PromptFacade` interface, shielding the consuming application from the internal complexity of constructing and managing prompts.

### 2. Core (`src/prompt_manager/core/`)
Contains domain models specific to prompt handling:
- **Models**: Defines classes like `PromptVersion`, `PromptTemplateContext`, and variable schema definitions. 
- **Exceptions**: Specific errors like `PromptNotFoundError`, `PIIValidationError`, or `TemplateRenderError`.

### 3. Engine (`src/prompt_manager/engine/`)
The core orchestrator responsible for prompt generation:
- **`builder.py` (Builder Pattern)**: Step-by-step construction of complex prompts (e.g., standardizing headers, injecting zero-shot directions, appending context variables).
- **`factory.py` (Factory Pattern)**: Instantiates the exact components needed based on the selected AI Agent role (e.g., standard investigator vs. orchestrator).
- **`facade.py`**: The main entry point used by external agents to request compiled prompts. It coordinates fetching, rendering, and security stripping seamlessly.

### 4. Security Middleware (`src/prompt_manager/security/`)
Acts as a strict proxy guaranteeing data safety before sending to the LLM:
- **`pii_scrubber.py`**: Detects and redacts Personally Identifiable Information (PII) such as SSNs, names, or addresses from the payload using regex heuristics or ML-based entity extraction.
- **`injection.py`**: Defenses against prompt injection. It sanitizes user inputs to ensure adversarial inputs don't hijack the instructions of the AI agents.

### 5. Templates (`src/prompt_manager/templates/`)
Stores the reasoning definitions and foundational constraints:
- **`chain_of_thought.py`**: Templates optimized for deep multi-step reasoning, forcing the AI to list its logic before coming to a fraud conclusion.
- **`react.py` (Reasoning and Acting)**: Templates specific to orchestrator or enrichment agents that must decide which tools to execute (`Action -> Observation -> Thought`).
- *Other Templates*: Could include generic classification templates or few-shot examples.

### 6. Storage (`src/prompt_manager/storage/`)
Handles physical persistence and retrieval of templates as assets instead of hard-coded strings.
- **`base.py` (`IStorageBackend`)**: Abstract class defining storage operations (fetching a prompt by name and version).
- **`filesystem.py`**: Uses flat JSON or YAML files on disk to manage prompt template states. Easily swappable for database storage (like PostgreSQL) in the future without modifying `engine` logic.

---

## Example Flow: Generating a Fraud Report Prompt
1. The **Report Agent** (Layer 2B) calls `PromptFacade.get_prompt("fraud_report", version="v1.2", context={"claim_id": "123"})`.
2. The **Facade** directs the **Storage** module to load the unstructured template from `filesystem`.
3. The **Builder** validates the `context` against expected variables and renders the markdown template.
4. The rendered text passes through **Security Middleware** (`pii_scrubber.py`) preventing any un-anonymized data leakage.
5. The safe, structured prompt string is returned to the Agent for LLM execution.
