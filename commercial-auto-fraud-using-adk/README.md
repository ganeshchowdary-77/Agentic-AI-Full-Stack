# Commercial Auto Fraud Detection Pipeline

An enterprise-grade fraud detection system for commercial auto insurance claims, built with **Google ADK (Agent Development Kit)** and powered by **Gemini 2.5 models**.

## 🎯 Overview

This system processes batches of insurance claims through a multi-stage AI pipeline to detect fraud patterns, score risk, and generate investigation reports for Special Investigations Units (SIU).

### Key Features

- **Multi-Agent Architecture**: Specialized agents for enrichment, analysis, and reporting
- **4-Pattern Fraud Detection**: Duplicate claims, suspicious timing, inflated amounts, provider networks
- **Parallel Processing**: Concurrent claim analysis for high throughput
- **Interactive Dashboard**: Real-time batch processing and results visualization
- **SIU Chat Interface**: Conversational queries about batch results
- **Versioned Prompts**: YAML-based prompt management with semantic versioning

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Web API (Port 8001)                      │
│                  Dashboard + REST Endpoints                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Orchestrator Workflow                       │
│         Coordinates enrichment → analysis → report           │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Enrichment   │    │   Analyzer   │    │    Report    │
│   Agent      │    │    Agent     │    │    Agent     │
│ (Flash 2.5)  │    │  (Pro 2.5)   │    │ (Flash 2.5)  │
│              │    │              │    │              │
│ Port 8002    │    │  Port 8003   │    │  Port 8004   │
└──────────────┘    └──────────────┘    └──────────────┘
```

### Pipeline Stages

1. **Enrichment**: Augments raw claims with 4 data sources
   - Claimant history (prior claims, fraud flags)
   - Provider network (billing patterns, license status)
   - Vehicle valuation (market value, repair benchmarks)
   - Policy details (inception date, recent changes)

2. **Analysis**: Parallel fraud pattern detection (4 patterns)
   - Duplicate/Similar Claims (30% weight)
   - Suspicious Timing (20% weight)
   - Inflated Amounts (25% weight)
   - Provider Network Anomalies (25% weight)

3. **Reporting**: Investigation reports for flagged claims (score ≥ 40)
   - Executive summary
   - Pattern breakdown with evidence
   - Recommended actions
   - Risk factors

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Google Gemini API key
- `uv` package manager (recommended) or `pip`

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd commercial-auto-fraud-using-adk

# Install dependencies with uv
uv sync

# Or with pip
pip install -e .
```

### Configuration

1. Set your Gemini API key in `.env`:

```bash
GEMINI_API_KEY=your_actual_api_key_here
```

2. (Optional) Configure Redis for distributed session storage:

```bash
REDIS_URL=redis://localhost:6379/0
```

### Running the System

#### Option 1: All Services (Recommended)

```bash
python main.py
```

This starts all 4 services:
- Web API / Dashboard: http://localhost:8001/dashboard
- Enrichment A2A: http://localhost:8002
- Analyzer A2A: http://localhost:8003
- Report A2A: http://localhost:8004

#### Option 2: Individual Services

```bash
# Terminal 1: Web API
uvicorn commercial_auto_fraud.presentation.web_api:app --host 0.0.0.0 --port 8001

# Terminal 2: Enrichment Agent
uvicorn commercial_auto_fraud.presentation.a2a_server:enrichment_app --host 0.0.0.0 --port 8002

# Terminal 3: Analyzer Agent
uvicorn commercial_auto_fraud.presentation.a2a_server:analyzer_app --host 0.0.0.0 --port 8003

# Terminal 4: Report Agent
uvicorn commercial_auto_fraud.presentation.a2a_server:report_app --host 0.0.0.0 --port 8004
```

## 📊 Usage

### Web Dashboard

1. Open http://localhost:8001/dashboard
2. Upload `weekly_auto_claims.json` (or your own batch file)
3. Click "Analyze Batch"
4. View results with fraud scores, priority tiers, and evidence

### REST API

#### Submit Batch

```bash
curl -X POST http://localhost:8001/api/fraud-detection/batch \
  -H "Content-Type: application/json" \
  -d @weekly_auto_claims.json
```

Response:
```json
{
  "status": "complete",
  "batch_id": "batch_2026_w16",
  "summary": {
    "total_claims": 12,
    "processed_claims": 12,
    "failed_claims": 0,
    "tier_distribution": {
      "critical": 2,
      "high": 3,
      "medium": 4,
      "low": 3
    },
    "processing_time_ms": 45230.5
  }
}
```

#### Get Batch Results

```bash
curl http://localhost:8001/api/batch/batch_2026_w16/results
```

#### Get Claim Detail

```bash
curl http://localhost:8001/api/batch/batch_2026_w16/claims/CLM-2026-001
```

#### SIU Chat

```bash
curl -X POST http://localhost:8001/api/siu/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Show me all critical priority claims",
    "batch_id": "batch_2026_w16"
  }'
```

## 📁 Project Structure

```
commercial-auto-fraud-using-adk/
├── commercial_auto_fraud/
│   ├── agents/                    # AI agents
│   │   ├── enrichment_agent.py    # Data enrichment (Flash)
│   │   ├── analyzer_agent.py      # Fraud analysis (Pro)
│   │   ├── report_agent.py        # Report generation (Flash)
│   │   ├── siu_chat_agent.py      # Interactive chat (Pro)
│   │   └── orchestrator_workflow.py # Pipeline coordinator
│   ├── domain/                    # Business logic
│   │   ├── schemas.py             # Pydantic models
│   │   └── exceptions.py          # Custom exceptions
│   ├── infrastructure/            # External integrations
│   │   ├── mock_providers.py      # Mock data sources
│   │   ├── session_store.py       # Session management
│   │   └── telemetry.py           # Observability
│   ├── presentation/              # API layer
│   │   ├── web_api.py             # Main REST API
│   │   ├── a2a_server.py          # A2A agent servers
│   │   └── dashboard.html         # Web UI
│   ├── prompts/                   # Prompt management
│   │   ├── manager.py             # Versioned prompt loader
│   │   └── storage/               # YAML prompt files
│   └── tools/                     # Agent tools
│       ├── enrichment_tools.py    # Data lookup tools
│       ├── analysis_tools.py      # Fraud detection tools
│       ├── report_tools.py        # Report generation tools
│       └── query_tools.py         # Result query tools
├── main.py                        # Multi-process entry point
├── weekly_auto_claims.json        # Sample batch data
├── pyproject.toml                 # Dependencies
└── README.md                      # This file
```

## 🔍 Fraud Detection Patterns

### 1. Duplicate/Similar Claims (30% weight)
- Same claimant filing multiple claims
- Same VIN across claims
- Prior fraud flags
- High claim frequency

### 2. Suspicious Timing (20% weight)
- Claims within 7-30 days of policy inception
- Coverage upgrades before loss
- Policy changes near loss date
- Weekend losses reported Monday

### 3. Inflated Amounts (25% weight)
- Claimed amount exceeds vehicle market value
- Repair costs above regional benchmarks
- Prior total loss on vehicle
- Salvage/rebuilt title

### 4. Provider Network (25% weight)
- Billing >2x regional average
- High flagged claims count
- Referral ring patterns
- License issues

## 📈 Scoring System

- **Composite Score**: 0-100 (weighted average of 4 patterns)
- **Priority Tiers**:
  - Critical: ≥80 (immediate investigation)
  - High: 60-79 (priority review)
  - Medium: 40-59 (standard review)
  - Low: <40 (routine processing)
- **Confidence Levels**:
  - High: 3+ patterns flagged (score >40)
  - Medium: 2 patterns flagged
  - Low: 1 or fewer patterns flagged

## 🛠️ Development

### Adding New Fraud Patterns

1. Create tool in `tools/analysis_tools.py`:
```python
async def analyze_new_pattern(claim_data_json: str, tool_context: ToolContext) -> Dict[str, Any]:
    # Pattern detection logic
    return {"pattern": "new_pattern", "score": score, "evidence": evidence}
```

2. Add to analyzer agent in `agents/analyzer_agent.py`
3. Update composite score weights in `domain/schemas.py`

### Adding New Prompts

Create YAML file in `prompts/storage/`:

```yaml
metadata:
  prompt_id: my_new_prompt
  version: v1.0.0
  description: My new prompt
  prompt_type: chain_of_thought
  created_by: developer
system_message: |
  Your prompt instructions here...
user_message_template: |
  Optional user message template with {variables}
```

Load in code:
```python
from commercial_auto_fraud.prompts.manager import prompt_manager
prompt = prompt_manager.get("my_new_prompt", variables={"key": "value"})
```

## 🧪 Testing

```bash
# Run with sample data
python main.py

# In another terminal, submit test batch
curl -X POST http://localhost:8001/api/fraud-detection/batch \
  -H "Content-Type: application/json" \
  -d @weekly_auto_claims.json
```

Expected results for `weekly_auto_claims.json`:
- **Critical**: CLM-2026-001, CLM-2026-002 (duplicate claims, same claimant)
- **High**: CLM-2026-003, CLM-2026-005, CLM-2026-007
- **Medium**: CLM-2026-009, CLM-2026-012
- **Low**: CLM-2026-004, CLM-2026-006, CLM-2026-008, CLM-2026-010, CLM-2026-011

## 📝 Sample Batch Format

```json
{
  "batch_id": "batch_2026_w16",
  "batch_name": "Weekly Auto Claims — Week 16, April 2026",
  "claims": [
    {
      "claim_id": "CLM-2026-001",
      "claimant": {"id": "C-4821", "name": "Marcus Rivera"},
      "provider": {"id": "PRV-0093", "type": "repair_shop"},
      "vehicle": {"vin": "1HGCM82633A004352", "year": 2022, "make": "Honda", "model": "Accord"},
      "policy_number": "POL-99-1234",
      "claimed_amount": 42000.00,
      "loss_date": "2026-04-11",
      "loss_type": "major_collision",
      "description": "Rear-end collision on I-94 northbound..."
    }
  ]
}
```

## 🔐 Security Considerations

- API keys stored in `.env` (never commit)
- Input validation on all endpoints
- Rate limiting recommended for production
- Audit logging for all fraud determinations
- Role-based access control for SIU dashboard

## 🚀 Production Deployment

### Recommended Setup

1. **Container Orchestration**: Deploy with Kubernetes/Docker
2. **Load Balancing**: Distribute across multiple agent instances
3. **Message Queue**: Replace in-memory with Redis/RabbitMQ
4. **Database**: Store results in PostgreSQL/MongoDB
5. **Monitoring**: Integrate with Datadog/New Relic
6. **Secrets Management**: Use AWS Secrets Manager/Vault

### Environment Variables

```bash
GEMINI_API_KEY=<your-key>
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://user:pass@host:5432/fraud_db
LOG_LEVEL=INFO
ENVIRONMENT=production
```

## 📚 Resources

- [Google ADK Documentation](https://cloud.google.com/vertex-ai/docs/agent-builder)
- [Gemini API Reference](https://ai.google.dev/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License.

## 🙏 Acknowledgments

- Built with Google ADK and Gemini 2.5 models
- Inspired by real-world insurance fraud detection systems
- Mock data designed to demonstrate fraud patterns

---

**Note**: This is a demonstration system using mock data. For production use, integrate with real data sources and implement proper security, compliance, and audit controls.
