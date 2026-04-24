# Commercial Auto Fraud Detection & Investigation Agent

This is a production-grade, multi-agent AI pipeline designed to detect commercial auto insurance fraud using Google's Agent-to-Agent (A2A) protocol.

The system utilizes a decentralized microservices architecture where specialized agents process claims concurrently.

## Prerequisites

Ensure you have Python 3.9+ installed on your system.

### Install Dependencies

Add the required Python packages using `uv`:

```bash
uv add fastapi uvicorn httpx pydantic python-dotenv opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp
```

*(Note: The `google.adk` library is simulated locally within the project for the MVP so it does not need to be installed via pip.)*

## Environment Setup

The system utilizes environment variables for telemetry (Arize OpenTelemetry).
Create a `.env` file in the root directory (where `main.py` is located):

```env
ARIZE_SPACE_ID=your_mock_space_id
ARIZE_API_KEY=your_mock_api_key
```

## Running the Application

The project is designed with a full Agent-to-Agent (A2A) network. When you boot the application, it automatically spins up three independent microservices in the background before launching the main Orchestrator.

### Option 1: Run the Integration Test Pipeline (Recommended for testing)

To observe the pipeline processing a batch of claims automatically without user intervention, run the integration test script:

```bash
uv run python tests/test_integration.py
```

**What happens:**
1. Background servers boot on ports `8002` (Enrichment), `8003` (Analyzer), and `8004` (Report Generator).
2. The Orchestrator ingests `weekly_auto_claims.json`.
3. Claims fan out to the agents and are enriched, evaluated for 4 distinct fraud patterns concurrently, and compiled into reports.
4. Output summaries are printed to the console, and batch results are saved in the `fraud_data_store/` directory.

### Option 2: Run the Main Bootstrapper (For UI / Chat mode)

To launch the main application (which integrates with the local ADK chat/UI):

```bash
uv run python src/main.py
```

**What happens:**
1. Background A2A servers start on their respective ports.
2. The Orchestrator Agent is initialized.
3. The mock `google.adk.ui` starts, simulating the user interface for investigators.

## Architecture Overview

- **Port 8001:** Orchestrator (Client)
- **Port 8002:** Claim Data Enrichment A2A Server
- **Port 8003:** Fraud Pattern Analyzer A2A Server
- **Port 8004:** Investigation Report Generator A2A Server

Data outputs, such as batch summaries and Markdown investigation reports, will be written to the dynamically created `fraud_data_store/` directory in the project root.
