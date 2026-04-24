# Google ADK (Agent Development Kit) — Deep Dive

This is a teaching document. It explains what ADK is, how it works internally, and how to build agents with it from scratch.

---

## 1. What is Google ADK?

**ADK = Agent Development Kit**. It's Google's framework for building AI agents that can:
- Use tools (call functions, APIs, databases)
- Reason step-by-step (Chain-of-Thought)
- Communicate with other agents (A2A protocol)
- Be observed and debugged (via OpenTelemetry traces)

Think of ADK as the **runtime engine** for an AI agent — similar to how Express.js is a runtime for a web server, ADK is a runtime for an AI agent.

### ADK vs Raw LLM API Calls

| Without ADK | With ADK |
|------------|---------|
| You call `gemini.generate("analyze this claim")` | You define an `Agent` with tools, instructions, and a model |
| You manually parse the response | ADK handles tool calling, response parsing, retries |
| You build your own tool-calling loop | ADK provides ReAct loop, tool registry, memory |
| You manage state yourself | ADK manages conversation state, tool results, context |
| You instrument traces manually | ADK auto-instruments LLM calls for observability |

### Core ADK Concepts

```
┌─────────────────────────────────────────┐
│              AGENT                       │
│  ┌─────────┐  ┌──────────┐              │
│  │  Model   │  │ Instruction│            │
│  │(Gemini)  │  │(System     │            │
│  │          │  │ Prompt)    │            │
│  └─────────┘  └──────────┘              │
│  ┌─────────────────────────┐            │
│  │       Tools[]            │            │
│  │  ┌──────┐ ┌──────┐     │            │
│  │  │Tool A│ │Tool B│ ... │            │
│  │  └──────┘ └──────┘     │            │
│  └─────────────────────────┘            │
│  ┌─────────────────────────┐            │
│  │    Memory / State        │            │
│  └─────────────────────────┘            │
└─────────────────────────────────────────┘
```

---

## 2. The Agent — The Core Unit

An Agent is defined by 4 things:

```python
agent = Agent(
    name="fraud_pattern_analyzer",       # Unique identifier
    model="gemini-2.5-pro",              # Which LLM to use
    instruction="You are a fraud...",    # System prompt (personality + rules)
    tools=[analyze_duplicate, ...],      # Functions the agent can call
)
```

### 2.1 Name
- Used for logging, tracing, and identification
- Must be unique within your system
- Appears in Arize traces as span labels
- In A2A, becomes the agent's identity in the agent card

### 2.2 Model
- Which Gemini model to use
- `gemini-2.5-pro` — Best reasoning, slower, more expensive (use for analysis)
- `gemini-2.5-flash` — Faster, cheaper (use for formatting, data retrieval)
- **Design principle**: Match model capability to task complexity

### 2.3 Instruction (System Prompt)
- Defines the agent's personality, constraints, and output format
- Set once at creation, applies to every `run()` call
- Think of it as the agent's "job description"

```python
instruction = """
You are a fraud pattern analyzer for commercial auto insurance.
You receive enriched claim data and evaluate specific fraud patterns.
Always return valid JSON with: pattern, score, severity, evidence, reasoning.
Never return scores above 100 or below 0.
"""
```

### 2.4 Tools
- Functions the agent can call during reasoning
- The LLM decides WHEN and IF to call each tool based on the prompt
- Each tool has a `name` and `description` (shown to the LLM so it knows what each tool does)

---

## 3. Agent.run() — What Happens Inside

When you call `agent.run(prompt)`, here's the internal flow:

```
User calls agent.run("Analyze this claim for fraud patterns")
│
▼
┌─────────────────────────────────────────────┐
│ Step 1: BUILD FULL PROMPT                    │
│                                              │
│ System: {instruction}                        │
│ Available Tools: {tool_name: description}    │
│ User: {prompt}                               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Step 2: SEND TO LLM (Gemini API)            │
│                                              │
│ POST https://generativelanguage.googleapis   │
│   .com/v1/models/gemini-2.5-pro:generate     │
│                                              │
│ Body: {system_instruction, contents, tools}  │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│ Step 3: LLM RESPONDS                         │
│                                              │
│ Option A: Text response (final answer)       │
│   → Return to caller                         │
│                                              │
│ Option B: Tool call request                  │
│   → Execute the tool                         │
│   → Feed result back to LLM                  │
│   → Go to Step 2 again (loop)               │
└─────────────────────────────────────────────┘
```

### The Tool-Calling Loop (ReAct Pattern)

When the LLM decides it needs a tool:

```
LLM: "I need to look up the claimant's history"
  → TOOL CALL: lookup_claimant_history(claimant_id="C-4821")
    → TOOL RESULT: {"total_prior_claims": 4, "prior_fraud_flags": 2, ...}
      → LLM receives result, reasons further
        → LLM: "The claimant has 2 prior fraud flags. Score: 85/100"
          → FINAL RESPONSE returned to caller
```

This loop can run multiple times — the LLM might call several tools in sequence before producing a final answer.

---

## 4. How We Implement ADK in This Project

Since the real `google.adk` package requires API credentials and network access, we built a **mock** that simulates the same interface:

### Real ADK (production)
```python
from google.adk import Agent  # Real package from Google

agent = Agent(name="analyzer", model="gemini-2.5-pro", instruction="...")
result = await agent.run("Analyze this claim")
# → Makes actual API call to Gemini
# → Returns LLM-generated text
```

### Mock ADK (our development setup)
```python
from google.adk import Agent  # Our mock in google/adk/__init__.py

agent = Agent(name="analyzer", model="gemini-2.5-pro", instruction="...")
result = await agent.run("Analyze this claim")
# → No API call
# → Parses enriched data from prompt
# → Applies deterministic scoring rules
# → Returns JSON matching the expected schema
```

### The Swap is Transparent
The `LLMProvider` in `src/infrastructure/llm/provider.py` is the ONLY place that imports `Agent`:

```python
from google.adk import Agent  # Change this ONE import to switch mock ↔ real
```

Every agent module calls `llm_provider.get_agent()` — they never import `Agent` directly. This is the **Dependency Inversion Principle** in action.

---

## 5. Multi-Agent Systems — How Agents Work Together

In ADK, complex problems are solved by **multiple specialized agents** rather than one monolithic agent:

### Why Multiple Agents?

| Single Agent | Multiple Agents |
|-------------|----------------|
| One massive instruction prompt | Each agent has a focused instruction |
| All tools registered in one place | Each agent has its own relevant tools |
| Hard to test, debug, and improve | Each agent testable independently |
| Single model for everything | Match model to task (Pro for analysis, Flash for formatting) |
| One failure breaks everything | Graceful degradation per agent |

### Our Multi-Agent Architecture

```
Orchestrator (Pro) — "The Manager"
├── Enrichment Agent (Flash) — "The Researcher"
│   ├── Tool: lookup_claimant_history
│   ├── Tool: lookup_provider_network
│   ├── Tool: lookup_vehicle_valuation
│   └── Tool: lookup_policy_details
├── Analyzer Agent (Pro) — "The Detective"
│   ├── Tool: duplicate_similar_analyzer
│   ├── Tool: suspicious_timing_analyzer
│   ├── Tool: inflated_amounts_analyzer
│   └── Tool: provider_network_analyzer
└── Report Generator (Flash) — "The Writer"
    ├── Tool: calculate_priority_score
    ├── Tool: format_evidence_summary
    └── Tool: format_investigation_report
```

### Agent Communication Patterns

**Pattern 1: Direct Function Call** (same process)
```python
# Agent A calls Agent B's run() method directly
result = await agent_b.run(data)
```

**Pattern 2: A2A Protocol** (separate processes, our approach)
```python
# Agent A sends HTTP request to Agent B's server
response = await httpx.post("http://localhost:8002/v1/tasks", json=task)
```

We use Pattern 2 because:
- Agents can be deployed on different machines
- Each agent can scale independently
- Follows Google's A2A specification
- Enables distributed tracing across agent boundaries

---

## 6. Building Your Own ADK Agent — Step by Step

Here's how to add a new agent to this system from scratch.

### Step 1: Define the Agent Module
```
src/application/agents/my_new_agent/
├── agent.py        # Agent class
├── schemas.py      # Pydantic schemas
└── tools/
    └── my_tool.py  # Your tool(s)
```

### Step 2: Create Your Tool
```python
# src/application/agents/my_new_agent/tools/my_tool.py
from src.infrastructure.tools.base_tool import BaseTool

class MyAnalysisTool(BaseTool):
    name = "my_analysis"
    description = "Analyzes claims for pattern X based on enriched data"

    def __init__(self, llm_agent):
        self._agent = llm_agent

    async def execute(self, enriched_claim: dict) -> dict:
        prompt = f"Analyze this: {json.dumps(enriched_claim)}"
        result = await self._agent.run(prompt)
        return json.loads(result)
```

### Step 3: Create Your Agent
```python
# src/application/agents/my_new_agent/agent.py
from src.infrastructure.tools.registry import ToolRegistry
from src.infrastructure.llm.provider import llm_provider
from .tools.my_tool import MyAnalysisTool

class MyNewAgent:
    agent_name = "my_new_agent"
    model = "gemini-2.5-pro"

    def __init__(self):
        self._llm = llm_provider.get_agent(
            name=self.agent_name,
            model=self.model,
            instruction="You are an expert at detecting pattern X...",
        )
        self._registry = ToolRegistry()
        self._registry.register(MyAnalysisTool(self._llm))

    async def run(self, data: dict) -> dict:
        return await self._registry.get("my_analysis").run(enriched_claim=data)
```

### Step 4: Create an A2A Server (if running as separate service)
```python
# src/presentation/a2a/server_my_agent.py
from fastapi import FastAPI
from .agent import MyNewAgent

app = FastAPI()
_agent = MyNewAgent()

@app.post("/v1/tasks")
async def handle_task(task: dict):
    data = json.loads(task["message"]["parts"][0]["text"])
    result = await _agent.run(data)
    return {"artifacts": [{"parts": [{"text": json.dumps(result)}]}]}
```

### Step 5: Register in Container
```python
# src/config/container.py — add one line
self.my_agent_client = A2AMyAgentClient()
```

That's it. The architecture enforces this pattern so every new agent is consistent.
